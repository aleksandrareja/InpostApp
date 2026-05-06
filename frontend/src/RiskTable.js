import React from 'react';

// Synchronizacja kolorów z MapComponent
function scoreColor(s, isLoop) {
  if (isLoop) return '#a78bfa'; // Fioletowy dla pętli
  if (s >= 75) return '#ef4444'; // Jasny czerwony dla tekstu na ciemnym tle
  if (s >= 50) return '#f87171'; 
  if (s >= 25) return '#fb923c'; 
  return '#fbbf24';
}

function scoreBg(s) {
  if (s >= 75) return 'rgba(153,27,27,0.35)';
  if (s >= 50) return 'rgba(220,38,38,0.25)';
  if (s >= 25) return 'rgba(249,115,22,0.25)';
  return 'rgba(251,191,36,0.15)';
}

const FILTERS = [
  { key: 'all', label: 'ZAGROŻONE' }, // Zmienione z WSZYSTKIE, bo ukrywamy stabilne
  { key: 'critical', label: 'KRYTYCZNE' },
  { key: 'loop', label: 'PĘTLE' },
];

export default function RiskTable({ machines, selected, onSelect, filter, onFilter }) {
  
  // 1. Filtrowanie zgodne z logiką "War Room"
  const filtered = machines
    .filter(m => {
      // Ukrywamy status stabilny w tabeli tak samo jak na mapie
      if (m.reason === "Status Stabilny") return false;
      
      if (filter === 'critical') return m.score >= 75; // Tylko Izolacja i Martwe Pętle
      if (filter === 'loop') return m.isLoop;
      return true;
    })
    // 2. Sortowanie - najwyższy score zawsze na górze
    .sort((a, b) => b.score - a.score)
    .slice(0, 50); // Zwiększyłem do 50, przy 8k krytycznych 20 to za mało

  return (
    <div style={{ width:360, flexShrink:0, background:'#111318', borderRight:'1px solid rgba(255,255,255,0.07)', display:'flex', flexDirection:'column', overflow:'hidden' }}>
      
      {/* Header */}
      <div style={{ padding:'14px 16px 10px', borderBottom:'1px solid rgba(255,255,255,0.07)', flexShrink:0 }}>
        <div style={{ fontSize:10, color:'#5c6478', letterSpacing:'2px', textTransform:'uppercase', marginBottom:8, display:'flex', justifyContent:'space-between' }}>
          <span>Ranking Zagrożeń</span>
          <span style={{ color: '#4ade80' }}>N={filtered.length}</span>
        </div>
        
        <div style={{ display:'flex', gap:6, flexWrap:'wrap' }}>
          {FILTERS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => onFilter(key)}
              style={{
                background: filter === key ? '#FFD000' : '#1e222b',
                border: `1px solid ${filter === key ? '#FFD000' : 'rgba(255,255,255,0.07)'}`,
                color: filter === key ? '#111' : '#9ca3b0',
                fontFamily: 'monospace',
                fontSize: 9,
                fontWeight: 700,
                padding: '4px 8px',
                borderRadius: 3,
                cursor: 'pointer',
                letterSpacing: '0.5px',
                transition: 'all 0.1s',
              }}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Rows */}
      <div style={{ overflowY:'auto', flex:1, background: '#0d0f14' }}>
        {filtered.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', color: '#5c6478', fontSize: 11 }}>
            Brak punktów spełniających kryteria
          </div>
        ) : filtered.map((m, i) => (
          <div
            key={m.name}
            onClick={() => onSelect(selected?.name === m.name ? null : m)}
            style={{
              display: 'grid',
              gridTemplateColumns: '26px 100px 45px 1fr',
              alignItems: 'center',
              gap: 8,
              padding: '10px 16px',
              borderBottom: '1px solid rgba(255,255,255,0.04)',
              borderLeft: selected?.name === m.name ? '3px solid #FFD000' : '3px solid transparent',
              background: selected?.name === m.name ? '#1e222b' : 'transparent',
              cursor: 'pointer',
              transition: 'all 0.1s',
            }}
          >
            <span style={{ fontFamily:'monospace', fontSize:9, color:'#3a4152', textAlign:'right' }}>{i + 1}</span>
            
            <div style={{ display:'flex', flexDirection:'column' }}>
              <span style={{ fontFamily:'monospace', fontSize:12, fontWeight:700, color: selected?.name === m.name ? '#FFD000' : '#f0f2f8' }}>
                {m.name}
              </span>
              <div style={{ display:'flex', gap:4, marginTop:2 }}>
                {m.isLoop && <span title="Pętla" style={{ color:'#a78bfa', fontSize:10 }}>⟲</span>}
                {m.isCrowd && <span title="Kanibalizm" style={{ color:'#FFD000', fontSize:10 }}>⚠</span>}
              </div>
            </div>

            <div style={{ 
              fontFamily:'monospace', 
              fontSize:11, 
              fontWeight:800, 
              padding:'3px 0', 
              borderRadius:3, 
              textAlign:'center', 
              background: scoreBg(m.score), 
              color: scoreColor(m.score, m.isLoop) 
            }}>
              {Math.round(m.score)}
            </div>

            <div style={{ 
              fontSize:10, 
              color: m.score >= 75 ? '#f87171' : '#9ca3b0', 
              fontWeight: m.score >= 75 ? 600 : 400,
              whiteSpace:'nowrap', 
              overflow:'hidden', 
              textOverflow:'ellipsis' 
            }}>
              {m.reason}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}