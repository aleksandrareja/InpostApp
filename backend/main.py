from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import networkx as nx
from geopy.distance import geodesic
import pandas as pd
import math

app = FastAPI(title="InPost Resilience Auditor API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Models ───────────────────────────────────────────────────────────────────

class Location(BaseModel):
    longitude: float
    latitude: float

class PaczkomatInput(BaseModel):
    name: str
    location: Location
    recommended_low_interest_box_machines_list: List[str] = []
    status: str = "Operating"
    functions: List[str] = []

class RiskDetail(BaseModel):
    name: str
    location: Location
    status: str
    functions: List[str]
    recommended: List[str]
    risk_score: float
    isolation_penalty: float
    distance_penalty: float
    network_pressure: float
    is_loop: bool
    primary_reason: str
    avg_distance_km: Optional[float]
    in_degree: int

class AnalysisResponse(BaseModel):
    machines: List[RiskDetail]
    total: int
    high_risk_count: int

# ─── Mock Data ────────────────────────────────────────────────────────────────

MOCK_DATA = [
    {"name": "WAW01M", "location": {"longitude": 21.0122, "latitude": 52.2297}, "recommended_low_interest_box_machines_list": ["WAW02M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "WAW02M", "location": {"longitude": 21.0180, "latitude": 52.2320}, "recommended_low_interest_box_machines_list": ["WAW01M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "WAW03M", "location": {"longitude": 21.0350, "latitude": 52.2150}, "recommended_low_interest_box_machines_list": [], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "WAW04M", "location": {"longitude": 20.9800, "latitude": 52.2500}, "recommended_low_interest_box_machines_list": ["WAW05M", "WAW06M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "WAW05M", "location": {"longitude": 20.9900, "latitude": 52.2600}, "recommended_low_interest_box_machines_list": ["WAW04M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "WAW06M", "location": {"longitude": 21.0500, "latitude": 52.2700}, "recommended_low_interest_box_machines_list": ["WAW04M"], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "KRK01M", "location": {"longitude": 19.9450, "latitude": 50.0647}, "recommended_low_interest_box_machines_list": [], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "KRK02M", "location": {"longitude": 19.9600, "latitude": 50.0700}, "recommended_low_interest_box_machines_list": ["KRK01M"], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "KRK03M", "location": {"longitude": 19.9750, "latitude": 50.0500}, "recommended_low_interest_box_machines_list": ["KRK04M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "KRK04M", "location": {"longitude": 19.9900, "latitude": 50.0550}, "recommended_low_interest_box_machines_list": ["KRK03M"], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "GDA01M", "location": {"longitude": 18.6466, "latitude": 54.3520}, "recommended_low_interest_box_machines_list": ["GDA02M", "GDA03M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "GDA02M", "location": {"longitude": 18.6600, "latitude": 54.3600}, "recommended_low_interest_box_machines_list": ["GDA01M"], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "GDA03M", "location": {"longitude": 18.6800, "latitude": 54.3800}, "recommended_low_interest_box_machines_list": [], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "WRO01M", "location": {"longitude": 17.0385, "latitude": 51.1079}, "recommended_low_interest_box_machines_list": [], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "WRO02M", "location": {"longitude": 17.0500, "latitude": 51.1200}, "recommended_low_interest_box_machines_list": ["WRO01M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "WRO03M", "location": {"longitude": 17.0700, "latitude": 51.1000}, "recommended_low_interest_box_machines_list": ["WRO04M"], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "WRO04M", "location": {"longitude": 17.0900, "latitude": 51.0900}, "recommended_low_interest_box_machines_list": ["WRO03M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "POZ01M", "location": {"longitude": 16.9252, "latitude": 52.4064}, "recommended_low_interest_box_machines_list": ["POZ02M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "POZ02M", "location": {"longitude": 16.9800, "latitude": 52.4200}, "recommended_low_interest_box_machines_list": [], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "POZ03M", "location": {"longitude": 16.9000, "latitude": 52.3900}, "recommended_low_interest_box_machines_list": ["POZ01M", "POZ02M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "LDZ01M", "location": {"longitude": 19.4560, "latitude": 51.7592}, "recommended_low_interest_box_machines_list": [], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "LDZ02M", "location": {"longitude": 19.4700, "latitude": 51.7700}, "recommended_low_interest_box_machines_list": ["LDZ01M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "LDZ03M", "location": {"longitude": 19.5000, "latitude": 51.7500}, "recommended_low_interest_box_machines_list": ["LDZ04M"], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "LDZ04M", "location": {"longitude": 19.5200, "latitude": 51.7400}, "recommended_low_interest_box_machines_list": ["LDZ03M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "ADA01M", "location": {"longitude": 22.26405, "latitude": 51.73834}, "recommended_low_interest_box_machines_list": ["ADA01N"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "ADA01N", "location": {"longitude": 22.27500, "latitude": 51.74200}, "recommended_low_interest_box_machines_list": ["ADA01M"], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "BIA01M", "location": {"longitude": 23.1688, "latitude": 53.1325}, "recommended_low_interest_box_machines_list": [], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "BIA02M", "location": {"longitude": 23.1900, "latitude": 53.1500}, "recommended_low_interest_box_machines_list": ["BIA01M"], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "RZE01M", "location": {"longitude": 22.0047, "latitude": 50.0412}, "recommended_low_interest_box_machines_list": [], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "KAT01M", "location": {"longitude": 19.0238, "latitude": 50.2649}, "recommended_low_interest_box_machines_list": ["KAT02M", "KAT03M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
    {"name": "KAT02M", "location": {"longitude": 19.0400, "latitude": 50.2750}, "recommended_low_interest_box_machines_list": ["KAT01M"], "status": "Operating", "functions": ["parcel_collect"]},
    {"name": "KAT03M", "location": {"longitude": 19.0600, "latitude": 50.2600}, "recommended_low_interest_box_machines_list": ["KAT01M"], "status": "Operating", "functions": ["parcel_collect", "parcel_send"]},
]

# ─── Analysis Engine ──────────────────────────────────────────────────────────

def analyze(machines: List[PaczkomatInput]) -> List[RiskDetail]:
    name_to_machine = {m.name: m for m in machines}

    # Build directed graph
    G = nx.DiGraph()
    for m in machines:
        G.add_node(m.name)
        for rec in m.recommended_low_interest_box_machines_list:
            G.add_edge(m.name, rec)

    # In-degree centrality
    in_degree = dict(G.in_degree())
    max_in_degree = max(in_degree.values()) if in_degree else 1

    # Detect loops (mutual recommendations)
    loops = set()
    for m in machines:
        for rec in m.recommended_low_interest_box_machines_list:
            if rec in name_to_machine:
                rec_machine = name_to_machine[rec]
                if m.name in rec_machine.recommended_low_interest_box_machines_list:
                    loops.add(m.name)
                    loops.add(rec)

    results = []
    for m in machines:
        # 1. Isolation Penalty (50% weight)
        if not m.recommended_low_interest_box_machines_list:
            isolation_penalty = 50.0
        else:
            isolation_penalty = 0.0

        # 2. Distance Penalty (30% weight)
        distances = []
        for rec_name in m.recommended_low_interest_box_machines_list:
            if rec_name in name_to_machine:
                rec = name_to_machine[rec_name]
                d = geodesic(
                    (m.location.latitude, m.location.longitude),
                    (rec.location.latitude, rec.location.longitude)
                ).km
                distances.append(d)

        avg_dist = sum(distances) / len(distances) if distances else None
        if avg_dist is not None:
            if avg_dist > 1.5:
                # Proportional: 1.5km = 0, 5km = 30
                distance_penalty = min(30.0, (avg_dist - 1.5) / (5.0 - 1.5) * 30.0)
            else:
                distance_penalty = 0.0
        else:
            distance_penalty = 0.0

        # 3. Network Pressure (20% weight)
        node_in_degree = in_degree.get(m.name, 0)
        network_pressure = (node_in_degree / max(max_in_degree, 1)) * 20.0

        # Total score
        raw = isolation_penalty + distance_penalty + network_pressure
        risk_score = min(100.0, round(raw, 1))

        # Primary reason
        if isolation_penalty >= 50:
            reason = "Brak alternatyw"
        elif distance_penalty >= 15:
            reason = "Duży dystans"
        elif network_pressure >= 10:
            reason = "Krytyczny węzeł sieci"
        elif m.name in loops:
            reason = "Pętla rekomendacji"
        else:
            reason = "Niskie ryzyko"

        results.append(RiskDetail(
            name=m.name,
            location=m.location,
            status=m.status,
            functions=m.functions,
            recommended=m.recommended_low_interest_box_machines_list,
            risk_score=risk_score,
            isolation_penalty=round(isolation_penalty, 1),
            distance_penalty=round(distance_penalty, 1),
            network_pressure=round(network_pressure, 1),
            is_loop=m.name in loops,
            primary_reason=reason,
            avg_distance_km=round(avg_dist, 3) if avg_dist is not None else None,
            in_degree=node_in_degree,
        ))

    results.sort(key=lambda x: x.risk_score, reverse=True)
    return results

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/analyze", response_model=AnalysisResponse)
def analyze_mock():
    machines = [PaczkomatInput(**d) for d in MOCK_DATA]
    results = analyze(machines)
    high_risk = sum(1 for r in results if r.risk_score >= 50)
    return AnalysisResponse(machines=results, total=len(results), high_risk_count=high_risk)

@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze_custom(machines: List[PaczkomatInput]):
    results = analyze(machines)
    high_risk = sum(1 for r in results if r.risk_score >= 50)
    return AnalysisResponse(machines=results, total=len(results), high_risk_count=high_risk)

@app.get("/health")
def health():
    return {"status": "ok"}