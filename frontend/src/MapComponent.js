import React, { useState, useEffect, useMemo } from 'react';
import { MapContainer, TileLayer, Marker, Tooltip, useMap, useMapEvents } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// ... (funkcje scoreColor i pinIcon zostają bez zmian z poprzedniego etapu) ...
function scoreColor(score, isLoop, reason) {
  if (reason === "MARTWA PĘTLA (Brak wyjścia)" || isLoop) return '#a78bfa';
  if (score >= 75) return '#991b1b';
  if (score >= 50) return '#dc2626';
  if (score >= 25) return '#f97316';
  return '#fbbf24';
}

function pinIcon(color) {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="28" viewBox="0 0 22 30">
    <circle cx="11" cy="11" r="10" fill="${color}" stroke="#111" stroke-width="1.5"/>
    <polygon points="11,28 5,18 17,18" fill="${color}" stroke="#111" stroke-width="1"/>
  </svg>`;
  return L.divIcon({ html: svg, className: '', iconSize: [20, 28], iconAnchor: [10, 28] });
}

// Komponent do obsługi zdarzeń mapy (Viewport Filtering)
function MapEvents({ onBoundsChange }) {
  const map = useMapEvents({
    moveend: () => onBoundsChange(map.getBounds(), map.getZoom()),
    zoomend: () => onBoundsChange(map.getBounds(), map.getZoom()),
  });
  return null;
}

function FlyTo({ selected }) {
  const map = useMap();
  useEffect(() => {
    if (selected) {
      map.flyTo([selected.location.latitude, selected.location.longitude], 16, { duration: 1.5 });
    }
  }, [selected, map]);
  return null;
}

export default function MapComponent({ machines, selected, onSelect }) {
  const [bounds, setBounds] = useState(null);
  const [zoom, setZoom] = useState(6);

  // 1. Wstępna filtracja - odrzucamy 14 tysięcy stabilnych punktów RAZ
  const riskyMachines = useMemo(() => 
    machines.filter(m => m.reason !== "Status Stabilny"), 
    [machines]
  );

  // 2. Dynamiczna filtracja - tylko to, co widać w oknie i zależy od zoomu
  const visibleMarkers = useMemo(() => {
    if (!bounds || zoom < 7) return []; // Nie rysuj nic na bardzo dużym oddaleniu
    
    return riskyMachines.filter(m => {
      const { latitude, longitude } = m.location;
      // Sprawdzamy czy punkt jest w aktualnym widoku mapy
      const isInView = bounds.contains([latitude, longitude]);
      
      // Optymalizacja: na średnim zoomie (7-10) pokazuj tylko te najgorsze (score > 50)
      if (zoom < 11) return isInView && m.score >= 50;
      
      // Na dużym zbliżeniu pokazuj wszystkie błędy w widoku
      return isInView;
    });
  }, [riskyMachines, bounds, zoom]);

  return (
    <div style={{ flex: 1, position: 'relative' }}>
      <MapContainer
        center={[52.0, 19.5]}
        zoom={6}
        minZoom={5}
        style={{ width: '100%', height: '100%', background: '#0d0f14' }}
        zoomControl={false}
        attributionControl={false}
        // Uruchomienie Bounds na starcie
        whenReady={(e) => setBounds(e.target.getBounds())}
      >
        <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" className="map-dark" />
        
        <MapEvents onBoundsChange={(b, z) => { setBounds(b); setZoom(z); }} />
        <FlyTo selected={selected} />

        {/* Dynamiczne markery */}
        {visibleMarkers.map(m => (
          <Marker 
            key={m.name}
            position={[m.location.latitude, m.location.longitude]}
            icon={pinIcon(scoreColor(m.score, m.isLoop, m.reason))}
            eventHandlers={{ click: () => onSelect(m) }}
          >
            <Tooltip sticky>
              <div style={{ fontWeight: 700 }}>{m.name}</div>
              <div style={{ fontSize: 10 }}>Score: {m.score} | {m.reason}</div>
            </Tooltip>
          </Marker>
        ))}
      </MapContainer>

      {/* Info o wydajności w Legendzie */}
      <div style={{ position: 'absolute', top: 16, right: 16, background: '#111318', border: '1px solid rgba(255,255,255,0.07)', borderRadius: 4, padding: '10px 12px', zIndex: 1000 }}>
        <div style={{ fontSize: 9, color: '#5c6478', letterSpacing: '1.5px', textTransform: 'uppercase', marginBottom: 6 }}>Status Mapy</div>
        <div style={{ color: '#f0f2f8', fontSize: 10, marginBottom: 4 }}>
          Widoczne błędy: <span style={{ color: '#FFD000', fontWeight: 'bold' }}>{visibleMarkers.length}</span>
        </div>
        {zoom < 10 && (
          <div style={{ color: '#f97316', fontSize: 9, fontStyle: 'italic' }}>
            Przybliż, aby zobaczyć wszystkie punkty
          </div>
        )}
        <div style={{ marginTop: 8, borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 4 }}>
          {/* Legenda kolorów z poprzedniego kroku... */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#9ca3b0', fontSize: 10 }}>
             <span style={{ fontSize: 14, color: '#991b1b' }}>▼</span> Krytyczne / Izolacja
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#9ca3b0', fontSize: 10 }}>
             <span style={{ fontSize: 14, color: '#a78bfa' }}>▼</span> Martwe Pętle
          </div>
        </div>
      </div>

      <style>{`
        .map-dark { filter: brightness(0.3) saturate(0.5) contrast(1.2) invert(100%) hue-rotate(180deg); }
      `}</style>
    </div>
  );
}