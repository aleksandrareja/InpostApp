import React, { useState, useEffect } from 'react';
import MapComponent from './MapComponent';
import RiskTable from './RiskTable';
import { analyze } from './engine';
import { MOCK_DATA } from './mockData';

export default function App() {
  const [machines, setMachines] = useState([]);
  const [selected, setSelected] = useState(null);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [loadingMsg, setLoadingMsg] = useState('Inicjalizacja...');
  const [source, setSource] = useState('');

  useEffect(() => {
    setLoadingMsg('Pobieranie danych z InPost API...');
    fetch('http://localhost:8000/api/analyze?country=PL&max_pages=50')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(d => {
        // Mapuj pola backendu na format frontendu
        const mapped = d.machines.map(m => ({
          ...m,
          score: m.risk_score,
          reason: m.primary_reason,
          isLoop: m.is_loop,
          isCrowd: m.is_crowd,
          crowdNeighbors: m.crowd_neighbors || [],
          avgDist: m.avg_distance_km,
          inDeg: m.in_degree,
          distPenalty: m.distance_penalty,
          netPressure: m.network_pressure,
          isolation: m.isolation_penalty,
        }));
        setMachines(mapped);
        setSource(d.source);
        setLoading(false);
      })
      .catch(err => {
        console.warn('Backend niedostępny, używam mock data:', err);
        setMachines(analyze(MOCK_DATA));
        setSource('Mock data (backend offline)');
        setLoading(false);
      });
  }, []);

  const stats = {
    total: machines.length,
    critical: machines.filter(m => m.score >= 75).length,
    medium: machines.filter(m => m.score >= 25 && m.score < 75).length,
    low: machines.filter(m => m.score < 25).length,
    loops: machines.filter(m => m.reason === "MARTWA PĘTLA (Brak wyjścia)").length,
  };

  if (loading) return (
    <div style={{ display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', height:'100vh', background:'#0a0b0e' }}>
      <p style={{ fontFamily:'monospace', fontSize:11, letterSpacing:3, color:'#5c6478', textTransform:'uppercase', marginBottom:16 }}>
        InPost · Resilience Auditor
      </p>
      <div style={{ width:200, height:2, background:'#1e222b', borderRadius:1, overflow:'hidden' }}>
        <div style={{ height:'100%', width:'60%', background:'#FFD000', borderRadius:1 }} />
      </div>
    </div>
  );

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100vh', background:'#0a0b0e', color:'#f0f2f8', fontFamily:"'Segoe UI', system-ui, sans-serif", overflow:'hidden' }}>
      <header style={{ display:'flex', alignItems:'center', justifyContent:'space-between', padding:'0 20px', height:54, background:'#111318', borderBottom:'1px solid rgba(255,255,255,0.07)', flexShrink:0 }}>
        <div style={{ display:'flex', alignItems:'center', gap:10 }}>
          <span style={{ background:'#FFD000', color:'#111', fontFamily:'monospace', fontSize:11, fontWeight:700, padding:'4px 8px', borderRadius:3, letterSpacing:1 }}>IRA</span>
          <div>
            <div style={{ fontSize:14, fontWeight:600 }}>InPost Resilience Auditor</div>
            <div style={{ fontSize:11, color:'#5c6478', marginTop:1 }}>Analiza podatności sieci Paczkomatów · v3.0</div>
          </div>
        </div>
        <div style={{ display:'flex', gap:28, alignItems:'center' }}>
          <Stat label="Łącznie" value={stats.total} />
          <Stat label="Krytyczne" value={stats.critical} color="#dc2626" />
          <Stat label="Średnie" value={stats.medium} color="#FFD000" />
          <Stat label="Niskie" value={stats.low} color="#22c55e" />
          <Stat label="Pętle" value={stats.loops} color="#a78bfa" />
        </div>
      </header>
      <div style={{ display:'flex', flex:1, overflow:'hidden' }}>
        <RiskTable machines={machines} selected={selected} onSelect={setSelected} filter={filter} onFilter={setFilter} />
        <MapComponent machines={machines} selected={selected} onSelect={setSelected} />
      </div>
    </div>
  );
}

function Stat({ label, value, color = '#f0f2f8' }) {
  return (
    <div style={{ textAlign:'center' }}>
      <div style={{ fontFamily:'monospace', fontSize:19, fontWeight:700, lineHeight:1, color }}>{value}</div>
      <div style={{ fontSize:9, color:'#5c6478', letterSpacing:'1.2px', textTransform:'uppercase', marginTop:2 }}>{label}</div>
    </div>
  );
}