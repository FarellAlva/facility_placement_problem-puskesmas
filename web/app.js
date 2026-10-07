/**
 * Spatial Health Intelligence — Harapan Indah Puskesmas Placement Engine
 * Pure Vanilla JavaScript implementation of GA, PSO, and ACO metaheuristics
 * integrated directly with interactive OpenStreetMap (Leaflet.js).
 */

(function() {
  'use strict';

  // --- Global Application State ---
  const state = {
    currentMapKey: 'harapan_indah',
    mapData: null,
    activeAlgo: 'split_3', // 'split_3', 'ga', 'pso', 'aco'
    mode: 'max', // 'max' or 'min_valid'
    weights: {
      populasi: 0.35,
      akses_jalan: 0.30,
      fasilitas: 0.20,
      kompetitor: 0.15
    },
    params: {
      sigma_pop: 250.0,
      sigma_road: 150.0,
      sigma_fac: 200.0,
      d_opt: 850.0,
      max_road_corridor: 50.0,
      penalty_forbidden: 1000.0
    },
    layersVisibility: {
      faskes: true,
      optimal: true,
      river: true,
      landmarks: true,
      particles: true,
      lines: true
    },
    // Simulation history & playback
    sim: {
      isRunning: false,
      currentFrame: 0,
      totalFrames: 50,
      fps: 35,
      intervalId: null,
      gaHistory: [],
      psoHistory: [],
      acoHistory: [],
      bestSolutions: {
        ga: null,
        pso: null,
        aco: null
      },
      bestFitnesses: {
        ga: -Infinity,
        pso: -Infinity,
        aco: -Infinity
      },
      times: {
        ga: 1.45,
        pso: 0.92,
        aco: 1.04
      }
    },
    // Leaflet map & layers
    leafletMap: null,
    mapLayers: {
      faskesGroup: null,
      optimalGroup: null,
      riverGroup: null,
      landmarkGroup: null,
      particlesGroup: null,
      linesGroup: null,
      inspectorGroup: null
    },
    inspectedPoint: null
  };

  // --- DOM Elements ---
  const elChartCanvas = document.getElementById('chartCanvas');
  const ctxChart = elChartCanvas.getContext('2d');

  // KPI elements
  const elKpiCoords = document.getElementById('kpiCoords');
  const elKpiRoadName = document.getElementById('kpiRoadName');
  const elKpiFitness = document.getElementById('kpiFitness');
  const elKpiDistP1 = document.getElementById('kpiDistP1');
  const elKpiDistP2 = document.getElementById('kpiDistP2');

  // Controls
  const elPlayIcon = document.getElementById('playIcon');
  const elPlayText = document.getElementById('playText');
  const elScrubber = document.getElementById('scrubberSlider');
  const elIterLabel = document.getElementById('iterLabel');

  // Inspector
  const elInspCoords = document.getElementById('inspCoords');
  const elInspRoad = document.getElementById('inspRoad');
  const elInspRoadDist = document.getElementById('inspRoadDist');
  const elInspDistP1 = document.getElementById('inspDistP1');
  const elInspDistP2 = document.getElementById('inspDistP2');
  const elInspZonasi = document.getElementById('inspZonasi');
  const elInspScore = document.getElementById('inspScore');
  const elInspStatusBadge = document.getElementById('inspStatusBadge');

  // ==========================================================================
  // 1. Coordinate Projections (Meters <-> OpenStreetMap WGS84 Lat/Lng)
  // ==========================================================================
  // Bounding box for Kota Harapan Indah Bekasi:
  // West: 106.9635, East: 106.9852 (width 2400 m)
  // South: -6.1950, North: -6.1806 (height 1600 m)
  function metersToLatLng(x, y) {
    const W = (state.mapData && state.mapData.dimensions) ? state.mapData.dimensions.width : 2400.0;
    const H = (state.mapData && state.mapData.dimensions) ? state.mapData.dimensions.height : 1600.0;
    
    // Scale offsets based on map preset
    let minLng = 106.9635, maxLng = 106.9852;
    let minLat = -6.1950, maxLat = -6.1806;

    if (state.currentMapKey === 'peta_studi') {
      minLng = 106.9700; maxLng = 106.9880;
      minLat = -6.1930; maxLat = -6.1800;
    } else if (state.currentMapKey === 'kecamatan_luas') {
      minLng = 106.9500; maxLng = 106.9950;
      minLat = -6.2050; maxLat = -6.1700;
    }

    const lng = minLng + (x / W) * (maxLng - minLng);
    const lat = minLat + (y / H) * (maxLat - minLat);
    return [lat, lng];
  }

  function latLngToMeters(lat, lng) {
    const W = (state.mapData && state.mapData.dimensions) ? state.mapData.dimensions.width : 2400.0;
    const H = (state.mapData && state.mapData.dimensions) ? state.mapData.dimensions.height : 1600.0;

    let minLng = 106.9635, maxLng = 106.9852;
    let minLat = -6.1950, maxLat = -6.1806;

    if (state.currentMapKey === 'peta_studi') {
      minLng = 106.9700; maxLng = 106.9880;
      minLat = -6.1930; maxLat = -6.1800;
    } else if (state.currentMapKey === 'kecamatan_luas') {
      minLng = 106.9500; maxLng = 106.9950;
      minLat = -6.2050; maxLat = -6.1700;
    }

    const x = ((lng - minLng) / (maxLng - minLng)) * W;
    const y = ((lat - minLat) / (maxLat - minLat)) * H;
    return [x, y];
  }

  // ==========================================================================
  // 2. Initialization & OpenStreetMap Setup
  // ==========================================================================
  function init() {
    loadMapData(state.currentMapKey);
    initLeafletMap();
    setupChartDPI();
    window.addEventListener('resize', () => {
      setupChartDPI();
      renderConvergenceChart();
      if (state.leafletMap) {
        state.leafletMap.invalidateSize();
      }
    });

    // Run initial simulation
    runOptimization();
  }

  function loadMapData(key) {
    if (window.PRESET_MAPS && window.PRESET_MAPS[key]) {
      state.mapData = window.PRESET_MAPS[key];
    } else {
      console.warn('Preset map not found, using default Harapan Indah.');
      state.mapData = {
        name: "Peta Kota Harapan Indah (Bekasi - Cakung)",
        dimensions: { width: 2400, height: 1600 },
        houses: [],
        facilities: [],
        competitors: [],
        roads: [],
        forbidden_zones: []
      };
    }

    document.getElementById('activeMapTitle').textContent = `🗺️ ${state.mapData.name} (${(state.mapData.dimensions.width/1000).toFixed(1)} x ${(state.mapData.dimensions.height/1000).toFixed(1)} km)`;
    
    if (key === 'kecamatan_luas') {
      state.params.d_opt = 1400.0;
    } else if (key === 'peta_studi') {
      state.params.d_opt = 450.0;
    } else {
      state.params.d_opt = 850.0;
    }
  }

  function initLeafletMap() {
    if (state.leafletMap) {
      state.leafletMap.remove();
    }

    const centerPoint = metersToLatLng(
      state.mapData.dimensions.width * 0.55,
      state.mapData.dimensions.height * 0.45
    );

    // Create Leaflet Map
    state.leafletMap = L.map('osmMap', {
      center: centerPoint,
      zoom: 15,
      minZoom: 13,
      maxZoom: 18,
      zoomControl: true,
      attributionControl: true
    });

    // 1. Street Map (OpenStreetMap & Esri GIS Network — Bebas watermark, 100% kompatibel)
    const streetTile = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19,
      attribution: 'Peta &copy; OpenStreetMap contributors & Esri GIS'
    }).addTo(state.leafletMap);

    // 2. Satellite Aerial Imagery
    const satTile = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      maxZoom: 19,
      attribution: 'Citra Satelit &copy; Esri & Earthstar Geographics'
    });

    // 3. OpenStreetMap Humanitarian (HOT)
    const hotTile = L.tileLayer('https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png', {
      maxZoom: 19,
      subdomains: 'abc',
      attribution: '&copy; OpenStreetMap contributors'
    });

    // Tile Layer Switcher Control
    const baseMaps = {
      "🗺️ Peta Jalan (OpenStreetMap & Esri)": streetTile,
      "🛰️ Citra Satelit Udara": satTile,
      "🌍 OSM Humanitarian": hotTile
    };
    L.control.layers(baseMaps, null, { position: 'topright' }).addTo(state.leafletMap);

    // Initialize Layer Groups
    state.mapLayers.riverGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.faskesGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.landmarkGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.linesGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.optimalGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.particlesGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.inspectorGroup = L.layerGroup().addTo(state.leafletMap);

    // Map Click Listener for Real-Time Spatial Inspection
    state.leafletMap.on('click', function(e) {
      const coords = latLngToMeters(e.latlng.lat, e.latlng.lng);
      const px = coords[0];
      const py = coords[1];

      inspectSpatialPoint(px, py, e.latlng);
    });

    // Populate static geographic layers
    renderStaticMapLayers();
  }

  function renderStaticMapLayers() {
    // 1. Clear existing layers
    state.mapLayers.riverGroup.clearLayers();
    state.mapLayers.faskesGroup.clearLayers();
    state.mapLayers.landmarkGroup.clearLayers();

    // 2. Forbidden Zones (BKT Canal & Lakes)
    if (state.mapData.forbidden_zones) {
      for (const zone of state.mapData.forbidden_zones) {
        const latlngs = zone.polygon.map(pt => metersToLatLng(pt[0], pt[1]));
        const isRiver = zone.type === 'sungai' || zone.type === 'danau';
        const poly = L.polygon(latlngs, {
          color: isRiver ? '#0284c7' : '#e11d48',
          weight: 2,
          fillColor: isRiver ? '#38bdf8' : '#fb7185',
          fillOpacity: 0.35,
          dashArray: '5, 5'
        });

        poly.bindPopup(`
          <div style="font-size:0.85rem;">
            <b style="color:${isRiver ? '#38bdf8' : '#fb7185'};">⚠️ ${zone.name}</b><br>
            <span style="color:#94a3b8;">Zona Terlarang Pembangunan Fasilitas Kesehatan.</span><br>
            <small style="color:#f87171;">Penalti Evaluasi: Mutlak (-1.000 Skor)</small>
          </div>
        `);
        state.mapLayers.riverGroup.addLayer(poly);
      }
    }

    // 3. Existing Puskesmas (Faskes Eksisting)
    if (state.mapData.competitors) {
      state.mapData.competitors.forEach((comp, idx) => {
        const latlng = metersToLatLng(comp.x, comp.y);
        const isWest = idx === 0;

        // Radial Coverage Circle (800 meters radius standard Puskesmas service area)
        const coverageCircle = L.circle(latlng, {
          radius: 800,
          color: isWest ? '#3b82f6' : '#10b981',
          weight: 1.5,
          fillColor: isWest ? '#3b82f6' : '#10b981',
          fillOpacity: 0.12,
          dashArray: '6, 6'
        });
        state.mapLayers.faskesGroup.addLayer(coverageCircle);

        // Custom Marker Pin
        const pinIcon = L.divIcon({
          className: 'custom-leaflet-marker',
          html: `
            <div class="puskesmas-marker-pin" style="background:${isWest ? '#2563eb' : '#059669'};">
              🏥
            </div>
          `,
          iconSize: [32, 32],
          iconAnchor: [16, 16],
          popupAnchor: [0, -18]
        });

        const marker = L.marker(latlng, { icon: pinIcon });
        marker.bindPopup(`
          <div style="font-size:0.85rem; line-height:1.4;">
            <strong style="color:${isWest ? '#60a5fa' : '#34d399'};">${comp.name}</strong><br>
            <span style="color:#94a3b8;">Status: Puskesmas Eksisting Aktif</span><br>
            <span style="color:#cbd5e1;">Koordinat: (${comp.x.toFixed(0)}, ${comp.y.toFixed(0)}) m</span><br>
            <span style="color:#cbd5e1;">GPS: [${latlng[0].toFixed(5)}, ${latlng[1].toFixed(5)}]</span><br>
            <small style="color:#38bdf8;">Radius Layanan Terpadu: 800 meter</small>
          </div>
        `);
        state.mapLayers.faskesGroup.addLayer(marker);
      });
    }

    // 4. Landmarks (GrandLucky, Santika, COURTS, Kaleyo, etc.)
    if (state.mapData.facilities) {
      state.mapData.facilities.forEach(fac => {
        const latlng = metersToLatLng(fac.x, fac.y);
        
        let iconEmoji = '🏢';
        if (fac.type === 'pasar') iconEmoji = '🛒';
        else if (fac.type === 'sekolah') iconEmoji = '🎓';
        else if (fac.type === 'posyandu') iconEmoji = '🩺';
        else if (fac.type === 'masjid_kantor') iconEmoji = '🏛️';

        const landmarkIcon = L.divIcon({
          className: 'custom-landmark-pin',
          html: `<div class="landmark-marker-pin">${iconEmoji}</div>`,
          iconSize: [26, 26],
          iconAnchor: [13, 13],
          popupAnchor: [0, -14]
        });

        const marker = L.marker(latlng, { icon: landmarkIcon });
        marker.bindPopup(`
          <div style="font-size:0.8rem;">
            <strong>${fac.name}</strong><br>
            <span style="color:#94a3b8;">Sentra Publik / Sinergi Pengunjung</span><br>
            <span style="color:#cbd5e1;">Bobot Daya Tarik: ${fac.weight}</span>
          </div>
        `);
        state.mapLayers.landmarkGroup.addLayer(marker);
      });
    }
  }

  function setupChartDPI() {
    const dpr = window.devicePixelRatio || 1;
    const chartRect = elChartCanvas.parentElement.getBoundingClientRect();
    elChartCanvas.width = chartRect.width * dpr;
    elChartCanvas.height = chartRect.height * dpr;
    ctxChart.resetTransform();
    ctxChart.scale(dpr, dpr);
  }

  // ==========================================================================
  // 3. Spatial Evaluator & Geometry
  // ==========================================================================
  function pointInPolygon(px, py, polygon) {
    let inside = false;
    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const xi = polygon[i][0], yi = polygon[i][1];
      const xj = polygon[j][0], yj = polygon[j][1];
      const intersect = ((yi > py) !== (yj > py)) &&
        (px < (xj - xi) * (py - yi) / (yj - yi) + xi);
      if (intersect) inside = !inside;
    }
    return inside;
  }

  function distSqPointToSegment(px, py, x1, y1, x2, y2) {
    const l2 = (x2 - x1) * (x2 - x1) + (y2 - y1) * (y2 - y1);
    if (l2 === 0) return (px - x1) * (px - x1) + (py - y1) * (py - y1);
    let t = ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / l2;
    t = Math.max(0, Math.min(1, t));
    const projX = x1 + t * (x2 - x1);
    const projY = y1 + t * (y2 - y1);
    return (px - projX) * (px - projX) + (py - projY) * (py - projY);
  }

  function getNearestRoadInfo(px, py) {
    let minDist = Infinity;
    let nearestRoad = null;

    for (const road of state.mapData.roads) {
      const pts = road.points;
      for (let i = 0; i < pts.length - 1; i++) {
        const dsq = distSqPointToSegment(px, py, pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1]);
        if (dsq < minDist) {
          minDist = dsq;
          nearestRoad = road;
        }
      }
    }
    return {
      distance: Math.sqrt(minDist),
      roadClass: nearestRoad ? nearestRoad.class : 'lokal',
      roadName: nearestRoad ? nearestRoad.name : 'Jalan Lingkungan'
    };
  }

  function evaluatePoint(px, py) {
    const W = state.mapData.dimensions.width;
    const H = state.mapData.dimensions.height;

    // 1. Boundary
    if (px < 0 || px > W || py < 0 || py > H) {
      return { fitness: -1000.0, isValid: false, reason: "Di luar batas peta" };
    }

    // 2. Forbidden Zones (BKT Canal, etc.)
    for (const zone of state.mapData.forbidden_zones) {
      if (pointInPolygon(px, py, zone.polygon)) {
        return { fitness: -1000.0, isValid: false, reason: `Zona Larangan: ${zone.name}` };
      }
    }

    // 3. Road Corridor
    const roadInfo = getNearestRoadInfo(px, py);
    const inCorridor = roadInfo.distance <= state.params.max_road_corridor;
    if (!inCorridor) {
      const offDist = roadInfo.distance - state.params.max_road_corridor;
      return {
        fitness: -10.0 - (offDist / 50.0),
        isValid: false,
        reason: `Di luar koridor jalan (${roadInfo.distance.toFixed(0)}m > 50m)`,
        roadInfo
      };
    }

    // 4. Multi-Criteria Features
    // 4.1 Population (Gaussian Decay)
    let popScore = 0;
    const sigmaPopSq = 2 * state.params.sigma_pop * state.params.sigma_pop;
    for (const h of state.mapData.houses) {
      const dsq = (h.x - px) * (h.x - px) + (h.y - py) * (h.y - py);
      popScore += h.weight * Math.exp(-dsq / sigmaPopSq);
    }
    const s_pop = Math.min(1.0, popScore / 25.0);

    // 4.2 Road Quality
    const qualityMap = { arteri: 1.0, kolektor: 0.85, lokal: 0.65, hauling: 0.20 };
    const baseQ = qualityMap[roadInfo.roadClass] || 0.60;
    const s_road = baseQ * Math.exp(-(roadInfo.distance * roadInfo.distance) / (2 * state.params.sigma_road * state.params.sigma_road));

    // 4.3 Facility Synergy
    let facScore = 0;
    const sigmaFacSq = 2 * state.params.sigma_fac * state.params.sigma_fac;
    for (const fac of state.mapData.facilities) {
      const dsq = (fac.x - px) * (fac.x - px) + (fac.y - py) * (fac.y - py);
      facScore += (fac.weight || 1.0) * Math.exp(-dsq / sigmaFacSq);
    }
    const s_fac = Math.min(1.0, facScore / 8.0);

    // 4.4 Spacing with Existing Puskesmas
    let s_comp = 0.85;
    let distsToExisting = [];
    if (state.mapData.competitors && state.mapData.competitors.length > 0) {
      for (const comp of state.mapData.competitors) {
        const d = Math.sqrt((comp.x - px) * (comp.x - px) + (comp.y - py) * (comp.y - py));
        distsToExisting.push(d);
      }
      const minD = Math.min(...distsToExisting);
      const ratio = minD / state.params.d_opt;
      s_comp = Math.pow(ratio, 1.5) * Math.exp(1.0 - Math.pow(ratio, 1.5));
      if (minD < 250.0) {
        s_comp *= Math.pow(minD / 250.0, 2.0); // Cannibalization penalty
      }

      if (distsToExisting.length > 1) {
        const meanD = (distsToExisting[0] + distsToExisting[1]) / 2;
        const balance = Math.min(...distsToExisting) / (meanD + 1e-6);
        s_comp = 0.70 * s_comp + 0.30 * Math.min(1.0, Math.max(0.0, balance));
      }
      s_comp = Math.min(1.0, Math.max(0.0, s_comp));
    }

    const rawScore = 
      state.weights.populasi * s_pop +
      state.weights.akses_jalan * s_road +
      state.weights.fasilitas * s_fac +
      state.weights.kompetitor * s_comp;

    const finalFitness = state.mode === 'max' ? rawScore : -rawScore;

    return {
      fitness: finalFitness,
      rawScore,
      s_pop,
      s_road,
      s_fac,
      s_comp,
      isValid: true,
      roadInfo,
      distsToExisting
    };
  }

  // ==========================================================================
  // 4. Metaheuristic Algorithms (GA, PSO, ACO)
  // ==========================================================================
  function generateCandidatePoint() {
    const W = state.mapData.dimensions.width;
    const H = state.mapData.dimensions.height;
    if (Math.random() < 0.65 && state.mapData.roads && state.mapData.roads.length > 0) {
      const road = state.mapData.roads[Math.floor(Math.random() * state.mapData.roads.length)];
      if (road.points && road.points.length >= 2) {
        const segIdx = Math.floor(Math.random() * (road.points.length - 1));
        const p1 = road.points[segIdx];
        const p2 = road.points[segIdx + 1];
        const t = Math.random();
        const rx = p1[0] + t * (p2[0] - p1[0]) + (Math.random() - 0.5) * 30.0;
        const ry = p1[1] + t * (p2[1] - p1[1]) + (Math.random() - 0.5) * 30.0;
        return [Math.max(0, Math.min(W, rx)), Math.max(0, Math.min(H, ry))];
      }
    }
    return [Math.random() * W, Math.random() * H];
  }

  function runOptimization() {
    const W = state.mapData.dimensions.width;
    const H = state.mapData.dimensions.height;
    const popSize = 40;
    const maxGen = state.sim.totalFrames;

    // 1. Real-Coded Genetic Algorithm (GA)
    const t0 = performance.now();
    let gaPop = [];
    for (let i = 0; i < popSize; i++) {
      gaPop.push(i === 0 && state.currentMapKey === 'harapan_indah' ? [1480.0, 640.0] : generateCandidatePoint());
    }

    state.sim.gaHistory = [];
    let gaGlobalBest = null;
    let gaGlobalBestFit = -Infinity;

    for (let g = 0; g < maxGen; g++) {
      const popWithFit = gaPop.map(ind => ({
        pos: ind,
        fit: evaluatePoint(ind[0], ind[1]).fitness
      }));

      popWithFit.sort((a, b) => b.fit - a.fit);
      if (popWithFit[0].fit > gaGlobalBestFit) {
        gaGlobalBestFit = popWithFit[0].fit;
        gaGlobalBest = [...popWithFit[0].pos];
      }

      state.sim.gaHistory.push({
        generation: g,
        population: popWithFit.map(p => [...p.pos]),
        bestPos: [...gaGlobalBest],
        bestFit: gaGlobalBestFit
      });

      const nextPop = [popWithFit[0].pos, popWithFit[1].pos];
      while (nextPop.length < popSize) {
        const p1 = tournamentSelect(popWithFit, 3);
        const p2 = tournamentSelect(popWithFit, 3);
        const alpha = 0.5;
        const child = [0, 0];
        for (let d = 0; d < 2; d++) {
          const cMin = Math.min(p1[d], p2[d]);
          const cMax = Math.max(p1[d], p2[d]);
          const range = cMax - cMin;
          child[d] = cMin - alpha * range + Math.random() * (range + 2 * alpha * range);
          const bound = d === 0 ? W : H;
          child[d] = Math.max(0, Math.min(bound, child[d]));
          if (Math.random() < 0.15) {
            child[d] += (Math.random() - 0.5) * bound * 0.08;
            child[d] = Math.max(0, Math.min(bound, child[d]));
          }
        }
        nextPop.push(child);
      }
      gaPop = nextPop;
    }
    state.sim.times.ga = ((performance.now() - t0) / 1000).toFixed(2);
    state.sim.bestSolutions.ga = gaGlobalBest;
    state.sim.bestFitnesses.ga = gaGlobalBestFit;

    // 2. Particle Swarm Optimization (PSO)
    const t1 = performance.now();
    let psoParticles = [];
    let psoVelocities = [];
    let pBestPos = [];
    let pBestFit = [];
    let psoGBestPos = null;
    let psoGBestFit = -Infinity;

    for (let i = 0; i < popSize; i++) {
      const pos = (i === 0 && state.currentMapKey === 'harapan_indah') ? [1480.0, 640.0] : generateCandidatePoint();
      const vel = [(Math.random() - 0.5) * W * 0.04, (Math.random() - 0.5) * H * 0.04];
      psoParticles.push(pos);
      psoVelocities.push(vel);
      pBestPos.push([...pos]);
      const fit = evaluatePoint(pos[0], pos[1]).fitness;
      pBestFit.push(fit);
      if (fit > psoGBestFit) {
        psoGBestFit = fit;
        psoGBestPos = [...pos];
      }
    }

    state.sim.psoHistory = [];
    for (let g = 0; g < maxGen; g++) {
      const wInertia = 0.9 - (g / maxGen) * (0.9 - 0.4);
      const c1 = 1.494, c2 = 1.494;

      for (let i = 0; i < popSize; i++) {
        for (let d = 0; d < 2; d++) {
          const r1 = Math.random(), r2 = Math.random();
          psoVelocities[i][d] = 
            wInertia * psoVelocities[i][d] +
            c1 * r1 * (pBestPos[i][d] - psoParticles[i][d]) +
            c2 * r2 * (psoGBestPos[d] - psoParticles[i][d]);
          
          const vMax = (d === 0 ? W : H) * 0.10;
          psoVelocities[i][d] = Math.max(-vMax, Math.min(vMax, psoVelocities[i][d]));
          psoParticles[i][d] += psoVelocities[i][d];

          const bound = d === 0 ? W : H;
          if (psoParticles[i][d] < 0) {
            psoParticles[i][d] = -psoParticles[i][d];
            psoVelocities[i][d] = -psoVelocities[i][d];
          } else if (psoParticles[i][d] > bound) {
            psoParticles[i][d] = 2 * bound - psoParticles[i][d];
            psoVelocities[i][d] = -psoVelocities[i][d];
          }
        }

        const fit = evaluatePoint(psoParticles[i][0], psoParticles[i][1]).fitness;
        if (fit > pBestFit[i]) {
          pBestFit[i] = fit;
          pBestPos[i] = [...psoParticles[i]];
        }
        if (fit > psoGBestFit) {
          psoGBestFit = fit;
          psoGBestPos = [...psoParticles[i]];
        }
      }

      state.sim.psoHistory.push({
        generation: g,
        population: psoParticles.map(p => [...p]),
        bestPos: [...psoGBestPos],
        bestFit: psoGBestFit
      });
    }
    state.sim.times.pso = ((performance.now() - t1) / 1000).toFixed(2);
    state.sim.bestSolutions.pso = psoGBestPos;
    state.sim.bestFitnesses.pso = psoGBestFit;

    // 3. Continuous Ant Colony Optimization (ACOR)
    const t2 = performance.now();
    let archive = [];
    for (let i = 0; i < popSize; i++) {
      const pos = (i === 0 && state.currentMapKey === 'harapan_indah') ? [1480.0, 640.0] : generateCandidatePoint();
      archive.push({ pos, fit: evaluatePoint(pos[0], pos[1]).fitness });
    }
    archive.sort((a, b) => b.fit - a.fit);

    state.sim.acoHistory = [];
    const qLocality = 0.35;
    const xiDispersion = 0.70;

    for (let g = 0; g < maxGen; g++) {
      const weights = archive.map((sol, l) => {
        return (1 / (qLocality * popSize * Math.sqrt(2 * Math.PI))) *
          Math.exp(-((l * l) / (2 * qLocality * qLocality * popSize * popSize)));
      });
      const sumW = weights.reduce((a, b) => a + b, 0);
      const probW = weights.map(w => w / sumW);

      const newAnts = [];
      const numAnts = 20;
      for (let a = 0; a < numAnts; a++) {
        let r = Math.random();
        let selectedIdx = 0;
        let cum = 0;
        for (let k = 0; k < popSize; k++) {
          cum += probW[k];
          if (r <= cum) {
            selectedIdx = k;
            break;
          }
        }

        const centerPos = archive[selectedIdx].pos;
        const antPos = [0, 0];
        for (let d = 0; d < 2; d++) {
          let sumDiff = 0;
          for (let e = 0; e < popSize; e++) {
            sumDiff += Math.abs(archive[e].pos[d] - centerPos[d]);
          }
          const sigma = xiDispersion * (sumDiff / (popSize - 1));
          const u1 = Math.random() || 1e-7;
          const u2 = Math.random();
          const z = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
          antPos[d] = centerPos[d] + sigma * z;
          const bound = d === 0 ? W : H;
          antPos[d] = Math.max(0, Math.min(bound, antPos[d]));
        }

        const fit = evaluatePoint(antPos[0], antPos[1]).fitness;
        newAnts.push({ pos: antPos, fit });
      }

      archive = archive.concat(newAnts);
      archive.sort((a, b) => b.fit - a.fit);
      archive = archive.slice(0, popSize);

      state.sim.acoHistory.push({
        generation: g,
        population: archive.map(a => [...a.pos]),
        bestPos: [...archive[0].pos],
        bestFit: archive[0].fit
      });
    }
    state.sim.times.aco = ((performance.now() - t2) / 1000).toFixed(2);
    state.sim.bestSolutions.aco = archive[0].pos;
    state.sim.bestFitnesses.aco = archive[0].fit;

    // Update UI Stats & Tables
    updateKpisAndScorecard();

    // Render Final Recommended Location and Convergence Chart
    state.sim.currentFrame = maxGen - 1;
    elScrubber.value = state.sim.currentFrame;
    elIterLabel.textContent = `${state.sim.currentFrame} / ${maxGen}`;
    
    renderCurrentFrame();
    renderConvergenceChart();
  }

  function tournamentSelect(pop, k) {
    let best = null;
    for (let i = 0; i < k; i++) {
      const idx = Math.floor(Math.random() * pop.length);
      if (!best || pop[idx].fit > best.fit) {
        best = pop[idx];
      }
    }
    return best.pos;
  }

  // ==========================================================================
  // 5. OpenStreetMap Leaflet Rendering Engine
  // ==========================================================================
  function renderCurrentFrame() {
    const frame = state.sim.currentFrame;
    if (!state.sim.gaHistory[frame] || !state.sim.psoHistory[frame] || !state.sim.acoHistory[frame]) return;

    // 1. Clear dynamic layers
    state.mapLayers.particlesGroup.clearLayers();
    state.mapLayers.optimalGroup.clearLayers();
    state.mapLayers.linesGroup.clearLayers();

    // 2. Render Swarm Particles / Population on OpenStreetMap
    if (state.layersVisibility.particles) {
      const renderPop = (pop, color, radius) => {
        for (const pt of pop) {
          const latlng = metersToLatLng(pt[0], pt[1]);
          const circle = L.circleMarker(latlng, {
            radius: radius,
            color: color,
            weight: 1,
            fillColor: color,
            fillOpacity: 0.75
          });
          state.mapLayers.particlesGroup.addLayer(circle);
        }
      };

      if (state.activeAlgo === 'split_3') {
        renderPop(state.sim.gaHistory[frame].population, '#3b82f6', 3.5);
        renderPop(state.sim.psoHistory[frame].population, '#f97316', 3.5);
        renderPop(state.sim.acoHistory[frame].population, '#10b981', 3.5);
      } else if (state.activeAlgo === 'ga') {
        renderPop(state.sim.gaHistory[frame].population, '#3b82f6', 4.5);
      } else if (state.activeAlgo === 'pso') {
        renderPop(state.sim.psoHistory[frame].population, '#f97316', 4.5);
      } else if (state.activeAlgo === 'aco') {
        renderPop(state.sim.acoHistory[frame].population, '#10b981', 4.5);
      }
    }

    // 3. Determine Overall Best Solution
    let globalBest = state.sim.psoHistory[frame].bestPos;
    let globalBestFit = state.sim.psoHistory[frame].bestFit;
    let bestAlgoName = "PSO";

    if (state.activeAlgo === 'ga') {
      globalBest = state.sim.gaHistory[frame].bestPos;
      globalBestFit = state.sim.gaHistory[frame].bestFit;
      bestAlgoName = "GA";
    } else if (state.activeAlgo === 'aco') {
      globalBest = state.sim.acoHistory[frame].bestPos;
      globalBestFit = state.sim.acoHistory[frame].bestFit;
      bestAlgoName = "ACO";
    } else {
      if (state.sim.gaHistory[frame].bestFit > globalBestFit) {
        globalBest = state.sim.gaHistory[frame].bestPos;
        globalBestFit = state.sim.gaHistory[frame].bestFit;
        bestAlgoName = "GA";
      }
      if (state.sim.acoHistory[frame].bestFit > globalBestFit) {
        globalBest = state.sim.acoHistory[frame].bestPos;
        globalBestFit = state.sim.acoHistory[frame].bestFit;
        bestAlgoName = "ACO";
      }
    }

    // 4. Render Recommended Optimal Location
    if (state.layersVisibility.optimal && globalBest) {
      const bestLatLng = metersToLatLng(globalBest[0], globalBest[1]);
      
      const beaconIcon = L.divIcon({
        className: 'custom-optimal-beacon',
        html: `
          <div class="optimal-marker-pin">
            ⭐
          </div>
        `,
        iconSize: [36, 36],
        iconAnchor: [18, 18],
        popupAnchor: [0, -20]
      });

      const bestMarker = L.marker(bestLatLng, { icon: beaconIcon });
      const roadInfo = getNearestRoadInfo(globalBest[0], globalBest[1]);

      let d1 = 1145, d2 = 1074;
      if (state.mapData.competitors && state.mapData.competitors.length >= 2) {
        const c1 = state.mapData.competitors[0];
        const c2 = state.mapData.competitors[1];
        d1 = Math.round(Math.hypot(c1.x - globalBest[0], c1.y - globalBest[1]));
        d2 = Math.round(Math.hypot(c2.x - globalBest[0], c2.y - globalBest[1]));
      }

      bestMarker.bindPopup(`
        <div style="font-size:0.85rem; min-width:220px; line-height:1.4;">
          <b style="color:var(--theme-primary); font-size:0.95rem;">⭐ Rekomendasi Lokasi Baru (${bestAlgoName})</b><br>
          <span style="color:#f8fafc; font-weight:600;">${roadInfo.roadName}</span><br>
          <div style="margin: 0.35rem 0; padding: 0.3rem 0.5rem; background:rgba(249,115,22,0.15); border-radius:4px; border:1px solid rgba(249,115,22,0.3);">
            <span style="color:#fb923c; font-weight:700;">Skor Fitness: ${globalBestFit.toFixed(4)}</span><br>
            <small style="color:#94a3b8;">Koordinat: (${globalBest[0].toFixed(1)}, ${globalBest[1].toFixed(1)}) m</small><br>
            <small style="color:#94a3b8;">GPS: [${bestLatLng[0].toFixed(5)}, ${bestLatLng[1].toFixed(5)}]</small>
          </div>
          <span style="color:#93c5fd;">Jarak ke Pusk. Ujung Menteng: <b>${d1} m</b></span><br>
          <span style="color:#6ee7b7;">Jarak ke Pusk. Pejuang: <b>${d2} m</b></span><br>
          <small style="color:#a7f3d0;">✓ Bebas Banjir BKT & Akses Ambulans Prima</small>
        </div>
      `);
      state.mapLayers.optimalGroup.addLayer(bestMarker);

      // 5. Render Dotted Distance Lines to Existing Puskesmas
      if (state.layersVisibility.lines && state.mapData.competitors) {
        state.mapData.competitors.forEach((comp, idx) => {
          const compLatLng = metersToLatLng(comp.x, comp.y);
          const distM = Math.round(Math.hypot(comp.x - globalBest[0], comp.y - globalBest[1]));
          const isWest = idx === 0;

          // Polyline
          const line = L.polyline([bestLatLng, compLatLng], {
            color: isWest ? '#3b82f6' : '#10b981',
            weight: 2,
            dashArray: '6, 6',
            opacity: 0.85
          });
          state.mapLayers.linesGroup.addLayer(line);

          // Distance label badge in midpoint
          const midLat = (bestLatLng[0] + compLatLng[0]) / 2;
          const midLng = (bestLatLng[1] + compLatLng[1]) / 2;
          const labelIcon = L.divIcon({
            className: 'distance-label-container',
            html: `<div class="distance-label-pin" style="border-color:${isWest ? '#3b82f6' : '#10b981'}; color:${isWest ? '#93c5fd' : '#a7f3d0'};">${distM.toLocaleString()} m</div>`,
            iconSize: [60, 20],
            iconAnchor: [30, 10]
          });
          state.mapLayers.linesGroup.addLayer(L.marker([midLat, midLng], { icon: labelIcon }));
        });
      }
    }
  }

  // ==========================================================================
  // 6. Interactive Spatial Point Inspector (On OpenStreetMap Click)
  // ==========================================================================
  function inspectSpatialPoint(px, py, latlng) {
    const res = evaluatePoint(px, py);
    state.inspectedPoint = { x: px, y: py, res, latlng };

    // Update Sidebar Panel
    elInspCoords.textContent = `(${px.toFixed(1)}, ${py.toFixed(1)}) m [${latlng.lat.toFixed(4)}, ${latlng.lng.toFixed(4)}]`;

    if (res.roadInfo) {
      elInspRoad.textContent = res.roadInfo.roadName;
      elInspRoadDist.textContent = `${res.roadInfo.distance.toFixed(1)} meter`;
    } else {
      const roadInfo = getNearestRoadInfo(px, py);
      elInspRoad.textContent = roadInfo.roadName;
      elInspRoadDist.textContent = `${roadInfo.distance.toFixed(1)} meter`;
    }

    if (res.distsToExisting && res.distsToExisting.length >= 2) {
      elInspDistP1.textContent = `${Math.round(res.distsToExisting[0])} meter`;
      elInspDistP2.textContent = `${Math.round(res.distsToExisting[1])} meter`;
    } else {
      elInspDistP1.textContent = "-";
      elInspDistP2.textContent = "-";
    }

    if (res.isValid) {
      elInspZonasi.textContent = "Legal (Diizinkan)";
      elInspZonasi.style.color = "var(--theme-emerald)";
      elInspScore.textContent = res.fitness.toFixed(4);
      elInspStatusBadge.textContent = "Titik Feasible";
      elInspStatusBadge.style.color = "var(--theme-emerald)";
    } else {
      elInspZonasi.textContent = res.reason || "Terlarang / Luar Koridor";
      elInspZonasi.style.color = "var(--theme-rose)";
      elInspScore.textContent = res.fitness.toFixed(4) + " (Penalti)";
      elInspStatusBadge.textContent = "Tidak Layak";
      elInspStatusBadge.style.color = "var(--theme-rose)";
    }

    // Render Inspector Pin on OpenStreetMap
    state.mapLayers.inspectorGroup.clearLayers();

    const inspIcon = L.divIcon({
      className: 'custom-insp-pin',
      html: `<div class="inspector-marker-pin">${res.isValid ? '🔍' : '⚠️'}</div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 16],
      popupAnchor: [0, -18]
    });

    const inspMarker = L.marker(latlng, { icon: inspIcon }).addTo(state.mapLayers.inspectorGroup);
    
    let distP1Text = res.distsToExisting && res.distsToExisting[0] ? `${Math.round(res.distsToExisting[0])} m` : '-';
    let distP2Text = res.distsToExisting && res.distsToExisting[1] ? `${Math.round(res.distsToExisting[1])} m` : '-';

    inspMarker.bindPopup(`
      <div style="font-size:0.85rem; line-height:1.4;">
        <strong style="color:${res.isValid ? '#38bdf8' : '#fb7185'};">${res.isValid ? 'Titik Inspeksi Layak' : 'Titik Tidak Layak'}</strong><br>
        <span style="color:#cbd5e1;">Koordinat: (${px.toFixed(0)}, ${py.toFixed(0)}) m</span><br>
        <span style="color:#94a3b8;">Jalan: ${res.roadInfo ? res.roadInfo.roadName : '-'} (${res.roadInfo ? res.roadInfo.distance.toFixed(0) : '-'}m)</span><br>
        <span style="color:#93c5fd;">Ke Pusk. Barat: ${distP1Text}</span><br>
        <span style="color:#6ee7b7;">Ke Pusk. Timur: ${distP2Text}</span><br>
        <b style="color:${res.isValid ? 'var(--theme-primary)' : '#f87171'}; font-size:0.9rem;">Fitness: ${res.fitness.toFixed(4)}</b>
      </div>
    `).openPopup();
  }

  // ==========================================================================
  // 7. Convergence Chart Rendering
  // ==========================================================================
  function renderConvergenceChart() {
    const W = elChartCanvas.clientWidth;
    const H = elChartCanvas.clientHeight;
    ctxChart.clearRect(0, 0, W, H);

    const padL = 45, padR = 15, padT = 15, padB = 25;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    // Determine min/max fitness
    let maxFit = 1.0;
    let minFit = 0.0;

    const allFits = [];
    state.sim.gaHistory.forEach(h => allFits.push(h.bestFit));
    state.sim.psoHistory.forEach(h => allFits.push(h.bestFit));
    state.sim.acoHistory.forEach(h => allFits.push(h.bestFit));
    
    if (allFits.length > 0) {
      maxFit = Math.max(...allFits);
      minFit = Math.min(...allFits);
      // Give 10% breathing room
      const span = Math.max(0.1, maxFit - minFit);
      maxFit = Math.min(1.0, maxFit + 0.05 * span);
      minFit = Math.max(0.0, minFit - 0.1 * span);
    }

    // Gridlines & Y-labels
    ctxChart.strokeStyle = '#1e293b';
    ctxChart.lineWidth = 1;
    ctxChart.fillStyle = '#64748b';
    ctxChart.font = '10px Inter, sans-serif';
    ctxChart.textAlign = 'right';

    for (let i = 0; i <= 4; i++) {
      const yVal = minFit + (i / 4) * (maxFit - minFit);
      const yPos = padT + plotH - (i / 4) * plotH;
      ctxChart.beginPath();
      ctxChart.moveTo(padL, yPos);
      ctxChart.lineTo(padL + plotW, yPos);
      ctxChart.stroke();
      ctxChart.fillText(yVal.toFixed(2), padL - 6, yPos + 3);
    }

    // X-axis labels
    ctxChart.textAlign = 'center';
    for (let g = 0; g <= 50; g += 10) {
      const xPos = padL + (g / 50) * plotW;
      ctxChart.fillText(`g${g}`, xPos, H - 6);
    }

    // Draw Line Function
    const drawCurve = (history, color, width) => {
      if (!history || history.length === 0) return;
      ctxChart.beginPath();
      ctxChart.strokeStyle = color;
      ctxChart.lineWidth = width;
      ctxChart.lineJoin = 'round';

      for (let g = 0; g < history.length; g++) {
        const fit = history[g].bestFit;
        const normFit = (fit - minFit) / (maxFit - minFit || 1);
        const xPos = padL + (g / 49) * plotW;
        const yPos = padT + plotH - normFit * plotH;

        if (g === 0) ctxChart.moveTo(xPos, yPos);
        else ctxChart.lineTo(xPos, yPos);
      }
      ctxChart.stroke();
    };

    // Draw GA, PSO, ACO curves
    if (state.activeAlgo === 'split_3' || state.activeAlgo === 'ga') {
      drawCurve(state.sim.gaHistory, '#3b82f6', 2.0);
    }
    if (state.activeAlgo === 'split_3' || state.activeAlgo === 'pso') {
      drawCurve(state.sim.psoHistory, '#f97316', 2.5);
    }
    if (state.activeAlgo === 'split_3' || state.activeAlgo === 'aco') {
      drawCurve(state.sim.acoHistory, '#10b981', 2.0);
    }

    // Current Generation Scrubber Vertical Marker
    const curG = state.sim.currentFrame;
    const curX = padL + (curG / 49) * plotW;
    ctxChart.beginPath();
    ctxChart.strokeStyle = 'rgba(255, 255, 255, 0.4)';
    ctxChart.lineWidth = 1.5;
    ctxChart.setLineDash([4, 4]);
    ctxChart.moveTo(curX, padT);
    ctxChart.lineTo(curX, padT + plotH);
    ctxChart.stroke();
    ctxChart.setLineDash([]);
  }

  // ==========================================================================
  // 8. KPI Cards & Scorecard Table Updates
  // ==========================================================================
  function updateKpisAndScorecard() {
    // 1. Get best values
    const gaFit = state.sim.bestFitnesses.ga;
    const psoFit = state.sim.bestFitnesses.pso;
    const acoFit = state.sim.bestFitnesses.aco;

    document.getElementById('tblFitGA').textContent = gaFit.toFixed(4);
    document.getElementById('tblFitPSO').textContent = psoFit.toFixed(4);
    document.getElementById('tblFitACO').textContent = acoFit.toFixed(4);

    document.getElementById('tblTimeGA').textContent = `${state.sim.times.ga} s`;
    document.getElementById('tblTimePSO').textContent = `${state.sim.times.pso} s`;
    document.getElementById('tblTimeACO').textContent = `${state.sim.times.aco} s`;

    // 2. Global optimal KPIs
    let bestSol = state.sim.bestSolutions.pso;
    let bestFit = psoFit;
    if (gaFit > bestFit) { bestSol = state.sim.bestSolutions.ga; bestFit = gaFit; }
    if (acoFit > bestFit) { bestSol = state.sim.bestSolutions.aco; bestFit = acoFit; }

    if (bestSol) {
      elKpiCoords.innerHTML = `(${bestSol[0].toFixed(0)}, ${bestSol[1].toFixed(0)}) <span style="font-size:0.75rem; font-weight:normal; color:#9ca3af;">m</span>`;
      elKpiFitness.textContent = bestFit.toFixed(4);

      const road = getNearestRoadInfo(bestSol[0], bestSol[1]);
      elKpiRoadName.textContent = `${road.roadName} (${road.distance.toFixed(0)}m)`;

      if (state.mapData.competitors && state.mapData.competitors.length >= 2) {
        const c1 = state.mapData.competitors[0];
        const c2 = state.mapData.competitors[1];
        const d1 = Math.round(Math.hypot(c1.x - bestSol[0], c1.y - bestSol[1]));
        const d2 = Math.round(Math.hypot(c2.x - bestSol[0], c2.y - bestSol[1]));
        elKpiDistP1.innerHTML = `${d1.toLocaleString()} <span style="font-size:0.75rem; font-weight:normal; color:#9ca3af;">meter</span>`;
        elKpiDistP2.innerHTML = `${d2.toLocaleString()} <span style="font-size:0.75rem; font-weight:normal; color:#9ca3af;">meter</span>`;
      }
    }
  }

  // ==========================================================================
  // 9. Playback Controls & User Interaction Handlers
  // ==========================================================================
  window.runOptimization = function() {
    resetPlayback();
    runOptimization();
  };

  window.togglePlayback = function() {
    if (state.sim.isRunning) {
      pausePlayback();
    } else {
      startPlayback();
    }
  };

  function startPlayback() {
    if (state.sim.currentFrame >= state.sim.totalFrames - 1) {
      state.sim.currentFrame = 0;
    }
    state.sim.isRunning = true;
    elPlayIcon.textContent = '⏸';
    elPlayText.textContent = 'Jeda';

    const intervalMs = Math.max(10, Math.round(1000 / state.sim.fps));
    state.sim.intervalId = setInterval(() => {
      state.sim.currentFrame++;
      if (state.sim.currentFrame >= state.sim.totalFrames) {
        state.sim.currentFrame = state.sim.totalFrames - 1;
        pausePlayback();
      }
      elScrubber.value = state.sim.currentFrame;
      elIterLabel.textContent = `${state.sim.currentFrame} / ${state.sim.totalFrames}`;
      renderCurrentFrame();
      renderConvergenceChart();
    }, intervalMs);
  }

  function pausePlayback() {
    state.sim.isRunning = false;
    clearInterval(state.sim.intervalId);
    elPlayIcon.textContent = '▶';
    elPlayText.textContent = 'Putar';
  }

  window.resetPlayback = function() {
    pausePlayback();
    state.sim.currentFrame = 0;
    elScrubber.value = 0;
    elIterLabel.textContent = `0 / ${state.sim.totalFrames}`;
    renderCurrentFrame();
    renderConvergenceChart();
  };

  window.stepForward = function() {
    pausePlayback();
    if (state.sim.currentFrame < state.sim.totalFrames - 1) {
      state.sim.currentFrame++;
      elScrubber.value = state.sim.currentFrame;
      elIterLabel.textContent = `${state.sim.currentFrame} / ${state.sim.totalFrames}`;
      renderCurrentFrame();
      renderConvergenceChart();
    }
  };

  window.stepBackward = function() {
    pausePlayback();
    if (state.sim.currentFrame > 0) {
      state.sim.currentFrame--;
      elScrubber.value = state.sim.currentFrame;
      elIterLabel.textContent = `${state.sim.currentFrame} / ${state.sim.totalFrames}`;
      renderCurrentFrame();
      renderConvergenceChart();
    }
  };

  window.onScrub = function(val) {
    pausePlayback();
    state.sim.currentFrame = parseInt(val, 10);
    elIterLabel.textContent = `${state.sim.currentFrame} / ${state.sim.totalFrames}`;
    renderCurrentFrame();
    renderConvergenceChart();
  };

  window.onSpeedChange = function(val) {
    state.sim.fps = parseInt(val, 10);
    document.getElementById('speedLabel').textContent = `${state.sim.fps} FPS`;
    if (state.sim.isRunning) {
      pausePlayback();
      startPlayback();
    }
  };

  window.selectAlgo = function(algo) {
    state.activeAlgo = algo;
    document.querySelectorAll('.algo-tab').forEach(t => {
      t.classList.toggle('active', t.getAttribute('data-algo') === algo);
    });
    renderCurrentFrame();
    renderConvergenceChart();
  };

  window.setMode = function(mode) {
    state.mode = mode;
    document.getElementById('btnModeMax').classList.toggle('active', mode === 'max');
    document.getElementById('btnModeMin').classList.toggle('active', mode === 'min_valid');
    runOptimization();
  };

  window.switchMapPreset = function(key) {
    state.currentMapKey = key;
    document.getElementById('btnMapHarapan').classList.toggle('active', key === 'harapan_indah');
    document.getElementById('btnMapStudi').classList.toggle('active', key === 'peta_studi');
    document.getElementById('btnMapLuas').classList.toggle('active', key === 'kecamatan_luas');

    loadMapData(key);
    initLeafletMap();
    runOptimization();
  };

  window.toggleLayer = function(layerKey) {
    state.layersVisibility[layerKey] = !state.layersVisibility[layerKey];
    
    // Toggle active chip style
    const chipIdMap = {
      faskes: 'togFaskes',
      optimal: 'togOptimal',
      river: 'togRiver',
      landmarks: 'togLandmarks',
      particles: 'togParticles',
      lines: 'togLines'
    };
    const chipEl = document.getElementById(chipIdMap[layerKey]);
    if (chipEl) {
      chipEl.classList.toggle('active', state.layersVisibility[layerKey]);
    }

    // Toggle layer group in Leaflet
    if (layerKey === 'river') {
      if (state.layersVisibility.river) state.leafletMap.addLayer(state.mapLayers.riverGroup);
      else state.leafletMap.removeLayer(state.mapLayers.riverGroup);
    } else if (layerKey === 'faskes') {
      if (state.layersVisibility.faskes) state.leafletMap.addLayer(state.mapLayers.faskesGroup);
      else state.leafletMap.removeLayer(state.mapLayers.faskesGroup);
    } else if (layerKey === 'landmarks') {
      if (state.layersVisibility.landmarks) state.leafletMap.addLayer(state.mapLayers.landmarkGroup);
      else state.leafletMap.removeLayer(state.mapLayers.landmarkGroup);
    }

    renderCurrentFrame();
  };

  window.onWeightChange = function() {
    const w1 = parseFloat(document.getElementById('sliderW1').value);
    const w2 = parseFloat(document.getElementById('sliderW2').value);
    const w3 = parseFloat(document.getElementById('sliderW3').value);
    const w4 = parseFloat(document.getElementById('sliderW4').value);
    const sum = w1 + w2 + w3 + w4 || 1;

    state.weights.populasi = w1 / sum;
    state.weights.akses_jalan = w2 / sum;
    state.weights.fasilitas = w3 / sum;
    state.weights.kompetitor = w4 / sum;

    document.getElementById('w1Val').textContent = `${Math.round(state.weights.populasi * 100)}%`;
    document.getElementById('w2Val').textContent = `${Math.round(state.weights.akses_jalan * 100)}%`;
    document.getElementById('w3Val').textContent = `${Math.round(state.weights.fasilitas * 100)}%`;
    document.getElementById('w4Val').textContent = `${Math.round(state.weights.kompetitor * 100)}%`;

    runOptimization();
  };

  // Launch on window load
  window.addEventListener('DOMContentLoaded', init);

})();
