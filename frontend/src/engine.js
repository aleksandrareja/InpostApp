// Client-side resilience scoring engine v3.0
// Mirrors the Python/FastAPI backend logic in main.py

function geodesicKm(lat1, lon1, lat2, lon2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLon = (lon2 - lon1) * Math.PI / 180;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

export function analyze(machines) {
  const byName = {};
  machines.forEach(m => (byName[m.name] = m));

  // In-degree count (NetworkX equivalent)
  const inDegree = {};
  machines.forEach(m => (inDegree[m.name] = 0));
  machines.forEach(m => {
    m.recommended_low_interest_box_machines_list.forEach(r => {
      if (inDegree[r] !== undefined) inDegree[r]++;
    });
  });
  const maxIn = Math.max(1, ...Object.values(inDegree));

  // Loop detection: A→B and B→A
  const loops = new Set();
  machines.forEach(m => {
    m.recommended_low_interest_box_machines_list.forEach(r => {
      if (
        byName[r] &&
        byName[r].recommended_low_interest_box_machines_list.includes(m.name)
      ) {
        loops.add(m.name);
        loops.add(r);
      }
    });
  });

  // Cannibalism detection: machines within 50m of each other
  const CROWD_DIST_M = 50;
  const crowdPairs = [];
  const crowdSet = new Set();
  for (let i = 0; i < machines.length; i++) {
    for (let j = i + 1; j < machines.length; j++) {
      const a = machines[i], b = machines[j];
      const d = geodesicKm(
        a.location.latitude, a.location.longitude,
        b.location.latitude, b.location.longitude
      ) * 1000;
      if (d <= CROWD_DIST_M) {
        crowdPairs.push({ a: a.name, b: b.name, dist: Math.round(d) });
        crowdSet.add(a.name);
        crowdSet.add(b.name);
      }
    }
  }

  return machines
    .map(m => {
      // 1. Isolation Penalty (weight 50%)
      const isolation =
        m.recommended_low_interest_box_machines_list.length === 0 ? 50 : 0;

      // 2. Distance Penalty (weight 30%)
      const dists = m.recommended_low_interest_box_machines_list
        .filter(r => byName[r])
        .map(r =>
          geodesicKm(
            m.location.latitude,
            m.location.longitude,
            byName[r].location.latitude,
            byName[r].location.longitude
          )
        );
      const avgDist =
        dists.length ? dists.reduce((a, b) => a + b, 0) / dists.length : null;
      const distPenalty =
        avgDist !== null && avgDist > 1.5
          ? Math.min(30, ((avgDist - 1.5) / 3.5) * 30)
          : 0;

      // 3. Network Pressure (weight 20%) — in-degree centrality
      const netPressure = (inDegree[m.name] / maxIn) * 20;

      const score = Math.min(
        100,
        Math.round(isolation + distPenalty + netPressure)
      );

      // Primary reason label
      let reason;
      if (isolation >= 50) reason = 'Brak alternatyw';
      else if (distPenalty >= 15) reason = 'Duży dystans';
      else if (netPressure >= 10) reason = 'Krytyczny węzeł';
      else if (loops.has(m.name)) reason = 'Pętla rekomendacji';
      else if (crowdSet.has(m.name)) reason = 'Kanibalizm lokalizacji';
      else reason = 'Niskie ryzyko';

      const myPairs = crowdPairs.filter(p => p.a === m.name || p.b === m.name);

      return {
        ...m,
        score,
        isolation: Math.round(isolation),
        distPenalty: Math.round(distPenalty * 10) / 10,
        netPressure: Math.round(netPressure * 10) / 10,
        reason,
        isLoop: loops.has(m.name),
        isCrowd: crowdSet.has(m.name),
        crowdNeighbors: myPairs,
        avgDist,
        inDeg: inDegree[m.name],
      };
    })
    .sort((a, b) => b.score - a.score);
}