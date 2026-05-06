from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import networkx as nx
from geopy.distance import geodesic
import httpx
import math
import time
import numpy as np
from scipy.spatial import cKDTree

app = FastAPI(title="InPost Resilience Auditor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

INPOST_API_BASE = "https://api-global-points.easypack24.net/v1/points"
CROWD_THRESHOLD_M = 50.0
CACHE_TTL = 600
_cache: dict = {}

# Dostępne kraje w API (endpoint /v1/points/{country})
AVAILABLE_COUNTRIES = ["PL", "GB", "IT", "FR", "DE", "ES", "NL", "BE", "PT", "AT", "LU"]

# ─── Models ───────────────────────────────────────────────────────────────────

class Location(BaseModel):
    longitude: float
    latitude: float

class CrowdPair(BaseModel):
    a: str
    b: str
    dist_m: float

class RiskDetail(BaseModel):
    name: str
    country: Optional[str]
    location: Location
    status: str
    address: Optional[str]
    city: Optional[str]
    functions: List[str]
    recommended: List[str]
    risk_score: float
    isolation_penalty: float
    distance_penalty: float
    network_pressure: float
    is_loop: bool
    is_crowd: bool
    crowd_neighbors: List[CrowdPair]
    primary_reason: str
    avg_distance_km: Optional[float]
    in_degree: int

class AnalysisResponse(BaseModel):
    machines: List[RiskDetail]
    total: int
    high_risk_count: int
    crowd_count: int
    loop_count: int
    source: str

# ─── Fetcher ──────────────────────────────────────────────────────────────────

async def fetch_inpost_points(
    country: Optional[str] = None,
    max_pages: int = 5,
    per_page: int = 500,
) -> List[dict]:
    #Pobiera punkty z InPost Global API.
    base_url = f"{INPOST_API_BASE}?country={country.upper()}" if country else INPOST_API_BASE
    all_items = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for page in range(1, max_pages + 1):
            resp = await client.get(base_url, params={"per_page": per_page, "page": page})
            resp.raise_for_status()
            data = resp.json()
            items = [i for i in data.get("items", []) if i.get("name") and i.get("location")]
            all_items.extend(items)
            total_pages = data.get("total_pages", 1)
            label = country.upper() if country else "ALL"
            print(f"  [{label}] strona {page}/{min(max_pages, total_pages)}, +{len(items)} pkt (łącznie: {len(all_items)})")
            if page >= total_pages:
                break
    return all_items

# ─── Normalizer ───────────────────────────────────────────────────────────────

def normalize(raw: dict) -> dict:
    addr = raw.get("address_details") or {}
    address = raw.get("address") or {}
    return {
        "name": raw["name"],
        "country": raw.get("country"),
        "location": {
            "longitude": float(raw["location"]["longitude"]),
            "latitude": float(raw["location"]["latitude"]),
        },
        "status": raw.get("status", "Operating"),
        "functions": raw.get("functions") or [],
        "recommended_low_interest_box_machines_list": raw.get("recommended_low_interest_box_machines_list") or [],
        "address": address.get("line1"),
        "city": addr.get("city"),
    }

# ─── Scoring Engine ───────────────────────────────────────────────────────────

def analyze(points: List[dict]) -> List[RiskDetail]:
    N = len(points)
    if N == 0: return []

    t_start = time.time()
    names_arr = [p["name"] for p in points]
    name_to_idx = {n: i for i, n in enumerate(names_arr)}
    lats = np.array([p["location"]["latitude"] for p in points])
    lons = np.array([p["location"]["longitude"] for p in points])
    recs_raw = [p["recommended_low_interest_box_machines_list"] or [] for p in points]

    # 1. Graf i Analiza Presji (In-degree)
    G = nx.DiGraph()
    G.add_nodes_from(names_arr)
    for i, name in enumerate(names_arr):
        for r in recs_raw[i]:
            if r in name_to_idx:
                G.add_edge(name, r)
    
    in_deg_map = dict(G.in_degree())
    in_deg_arr = np.array([in_deg_map.get(n, 0) for n in names_arr], dtype=float)

    # 2. Martwe Pętle i Kanibalizm
    deadly_loops = set()
    is_loop_set = set()
    for i, name in enumerate(names_arr):
        recs = recs_raw[i]
        for r in recs:
            if r in name_to_idx:
                j = name_to_idx[r]
                if name in recs_raw[j]:
                    is_loop_set.add(name)
                    if len(recs) == 1 and len(recs_raw[j]) == 1:
                        deadly_loops.add(name)

    lat_r, lon_r = np.radians(lats), np.radians(lons)
    coords_3d = np.column_stack([np.cos(lat_r)*np.cos(lon_r), np.cos(lat_r)*np.sin(lon_r), np.sin(lat_r)])
    tree = cKDTree(coords_3d)
    crowd_pairs_idx = tree.query_pairs(CROWD_THRESHOLD_M / 6371000.0, output_type="ndarray")
    crowd_set = set(names_arr[i] for i in crowd_pairs_idx.flatten())

    # 3. Obliczanie dystansów
    avg_dist_arr = np.full(N, np.nan)
    has_valid_backup = np.zeros(N, dtype=bool)
    for i, recs in enumerate(recs_raw):
        valid = [name_to_idx[r] for r in recs if r in name_to_idx]
        if valid:
            has_valid_backup[i] = True
            vidx = np.array(valid)
            dlat, dlon = np.radians(lats[vidx] - lats[i]), np.radians(lons[vidx] - lons[i])
            a = np.sin(dlat/2)**2 + np.cos(np.radians(lats[i])) * np.cos(np.radians(lats[vidx])) * np.sin(dlon/2)**2
            avg_dist_arr[i] = (6371.0 * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))).mean()

    # 4. SMART SCORING LOGIC
    results = []
    for i in range(N):
        name = names_arr[i]
        in_deg = in_deg_arr[i]
        score = 0.0
        reason = "Status Stabilny"

        # --- LOGIKA IZOLACJI ---
        if not has_valid_backup[i]:
            if in_deg > 5:
                score = 85.0
                reason = "KRYTYCZNA IZOLACJA (High Pressure)"
            elif in_deg > 0:
                score = 50.0
                reason = "IZOLACJA STANDARDOWA"
            else:
                score = 15.0 # Samotnik - niskie znaczenie
                reason = "Samotny punkt (Niska presja)"
        
        # --- LOGIKA PĘTLI ---
        elif name in deadly_loops:
            score = 75.0
            reason = "MARTWA PĘTLA (Brak wyjścia)"
        
        # --- LOGIKA DYSTANSU ---
        elif avg_dist_arr[i] > 2.0:
            score = 60.0
            reason = "KRYTYCZNY DYSTANS (>2km)"
        
        # --- LOGIKA BOTTLENECK ---
        elif in_deg > 10:
            score = 45.0
            reason = "WĄSKIE GARDŁO (Przeciążenie)"

        # Dodatkowe kary za gęstość
        if name in crowd_set and in_deg > 5:
            score += 10

        # Ostateczne wyliczenie kar szczegółowych dla modelu RiskDetail
        iso_p = 80.0 if not has_valid_backup[i] and in_deg > 0 else (20.0 if not has_valid_backup[i] else 0.0)
        dist_p = np.clip((np.nan_to_num(avg_dist_arr[i]) - 1.0) * 15.0, 0, 40) if has_valid_backup[i] else 0.0
        net_p = np.clip((in_deg / 10.0) * 30.0, 0, 30)

        results.append(RiskDetail(
            name=name,
            country=points[i].get("country"),
            location=Location(**points[i]["location"]),
            status=points[i]["status"],
            address=points[i].get("address"),
            city=points[i].get("city"),
            functions=points[i]["functions"],
            recommended=recs_raw[i],
            risk_score=round(float(score), 1),
            isolation_penalty=round(float(iso_p), 1),
            distance_penalty=round(float(dist_p), 1),
            network_pressure=round(float(net_p), 1),
            is_loop=name in is_loop_set,
            is_crowd=name in crowd_set,
            crowd_neighbors=[],
            primary_reason=reason,
            avg_distance_km=round(float(avg_dist_arr[i]), 3) if has_valid_backup[i] else None,
            in_degree=int(in_deg)
        ))

    results.sort(key=lambda x: x.risk_score, reverse=True)
    
    # Logi dla szefa
    from collections import Counter
    stats = Counter(r.primary_reason for r in results)
    print(f"\n{'='*40}\nRAPORT STRATEGICZNY IRA\n{'-'*40}")
    for r in ["KRYTYCZNA IZOLACJA (High Pressure)", "MARTWA PĘTLA (Brak wyjścia)", "KRYTYCZNY DYSTANS (>2km)", "Status Stabilny"]:
        print(f"  {r.ljust(30)} : {stats.get(r, 0)}")
    print('='*40)
    
    return results

# ─── Updated Endpoint ─────────────────────────────────────────────────────────

@app.get("/api/analyze", response_model=AnalysisResponse)
async def analyze_endpoint(country: Optional[str] = None, max_pages: int = 50, refresh: bool = False):
    cache_key = f"v32_{country}_{max_pages}"
    if not refresh and cache_key in _cache:
        return _cache[cache_key][1]

    raw = await fetch_inpost_points(country=country, max_pages=max_pages)
    points = [normalize(r) for r in raw]
    results = analyze(points)
    
    response = AnalysisResponse(
        machines=results,
        total=len(results),
        # Teraz High Risk to tylko realne pożary (score >= 75)
        high_risk_count=sum(1 for r in results if r.risk_score >= 75),
        crowd_count=sum(1 for r in results if r.is_crowd),
        loop_count=sum(1 for r in results if r.primary_reason == "MARTWA PĘTLA (Brak wyjścia)"),
        source=f"IRA Smart Audit v3.2 ({len(results)} pkt)"
    )
    _cache[cache_key] = (time.time(), response)
    return response

@app.get("/api/countries")
def list_countries():
    """Lista krajów dostępnych do filtrowania."""
    return {"countries": AVAILABLE_COUNTRIES}

@app.get("/health")
def health():
    return {"status": "ok", "api": INPOST_API, "cached_keys": list(_cache.keys())}