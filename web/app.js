/**
 * Spatial Health Intelligence — Harapan Indah Puskesmas Placement Engine
 * Pure Vanilla JavaScript implementation of GA, PSO, and ACO metaheuristics
 * integrated directly with interactive OpenStreetMap (Leaflet.js).
 * Focused exclusively on Kota Harapan Indah Bekasi (2.4 x 1.6 km).
 */

(function() {
  'use strict';

  // --- Global Application State ---
  const state = {
    currentMapKey: 'harapan_indah',
    mapData: null,
    activeAlgo: 'split_3', // 'split_3', 'ga', 'pso', 'aco'
    mode: 'max', // 'max' or 'min_valid'
    facilityCount: 1, // 1, 2, or 3 facilities
    curationMode: 'normal', // 'normal' | 'addPoint'
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
      boundary: true,
      density: true,
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
      fps: 40,
      intervalId: null,
      gaHistory: [],
      psoHistory: [],
      acoHistory: [],
      bestSolutions: { ga: null, pso: null, aco: null },
      bestFitnesses: { ga: -Infinity, pso: -Infinity, aco: -Infinity },
      times: { ga: 0.03, pso: 0.01, aco: 0.02 }
    },
    // Leaflet map & layers
    leafletMap: null,
    canvasRenderer: null,
    mapLayers: {
      boundaryGroup: null,
      densityGroup: null,
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
  const elChartGenBadge = document.getElementById('chartGenBadge');

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
  const BBOX = {
    minLng: 106.9635,
    maxLng: 106.9852,
    minLat: -6.1950,
    maxLat: -6.1806,
    widthMeters: 2400.0,
    heightMeters: 1600.0
  };

  function metersToLatLng(x, y) {
    const lng = BBOX.minLng + (x / BBOX.widthMeters) * (BBOX.maxLng - BBOX.minLng);
    const lat = BBOX.minLat + (y / BBOX.heightMeters) * (BBOX.maxLat - BBOX.minLat);
    return [lat, lng];
  }

  function latLngToMeters(lat, lng) {
    const x = ((lng - BBOX.minLng) / (BBOX.maxLng - BBOX.minLng)) * BBOX.widthMeters;
    const y = ((lat - BBOX.minLat) / (BBOX.maxLat - BBOX.minLat)) * BBOX.heightMeters;
    return [x, y];
  }

  // ==========================================================================
  // 2. Initialization & OpenStreetMap Setup
  // ==========================================================================
  function init() {
    loadMapData();
    initLeafletMap();
    initCurationUI();
    setupChartDPI();

    window.addEventListener('resize', () => {
      setupChartDPI();
      renderConvergenceChart();
      if (state.leafletMap) {
        state.leafletMap.invalidateSize();
      }
    });

    // Run initial optimization and animate
    runOptimization();
  }

  function loadMapData() {
    if (window.PRESET_MAPS && window.PRESET_MAPS['harapan_indah']) {
      state.mapData = JSON.parse(JSON.stringify(window.PRESET_MAPS['harapan_indah']));
    } else {
      console.warn('Harapan Indah map preset not found, using fallback.');
      state.mapData = {
        name: "Peta Kota Harapan Indah (Bekasi - Cakung)",
        dimensions: { width: 2400, height: 1600 },
        houses: [],
        facilities: [],
        competitors: [],
        roads: [],
        forbidden_zones: [],
        curated_zones: []
      };
    }

    // Check user custom curation in localStorage
    try {
      const saved = localStorage.getItem('puskesmas_harapan_indah_curation');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed.houses && Array.isArray(parsed.houses) && parsed.houses.length > 0) {
          state.mapData.houses = parsed.houses;
        }
        if (parsed.curated_zones && Array.isArray(parsed.curated_zones) && parsed.curated_zones.length > 0) {
          state.mapData.curated_zones = parsed.curated_zones;
        }
      }
    } catch (e) {
      console.warn('Could not load localStorage curation:', e);
    }

    // Preserve baseline weight for mathematical calibration
    if (state.mapData.houses) {
      state.mapData.houses.forEach(h => {
        if (h.base_weight === undefined) {
          h.base_weight = h.weight;
        }
      });
    }
  }

  function initLeafletMap() {
    if (state.leafletMap) {
      state.leafletMap.remove();
    }

    // High performance Leaflet canvas renderer for smooth particle animations
    state.canvasRenderer = L.canvas({ padding: 0.5 });

    // Center on Harapan Indah
    const centerPoint = metersToLatLng(1200, 800);

    state.leafletMap = L.map('osmMap', {
      center: centerPoint,
      zoom: 15,
      minZoom: 13,
      maxZoom: 18,
      zoomControl: true,
      attributionControl: true
    });

    // 1. Street Map (Primary - Clean & 100% Free)
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

    // Base Maps Switcher
    const baseMaps = {
      "🗺️ Peta Jalan (OSM & Esri)": streetTile,
      "🛰️ Citra Satelit": satTile,
      "🌍 OSM Humanitarian": hotTile
    };
    L.control.layers(baseMaps, null, { position: 'topright' }).addTo(state.leafletMap);

    // Initialize Layer Groups
    state.mapLayers.boundaryGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.densityGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.riverGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.faskesGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.landmarkGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.linesGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.optimalGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.particlesGroup = L.layerGroup().addTo(state.leafletMap);
    state.mapLayers.inspectorGroup = L.layerGroup().addTo(state.leafletMap);

    // Map Click Listener for Spatial Point Inspector or Adding Point
    state.leafletMap.on('click', function(e) {
      const coords = latLngToMeters(e.latlng.lat, e.latlng.lng);
      if (state.curationMode === 'addPoint') {
        handleAddHousePoint(coords[0], coords[1], e.latlng);
      } else {
        inspectSpatialPoint(coords[0], coords[1], e.latlng);
      }
    });

    // Render Static Layers (Simulation Bounding Box, Rivers, Faskes, Landmarks, Density)
    renderStaticMapLayers();

    // Auto-fit to the simulation bounding box
    const simBounds = [
      metersToLatLng(0, 0),
      metersToLatLng(BBOX.widthMeters, BBOX.heightMeters)
    ];
    state.leafletMap.fitBounds(simBounds, { padding: [25, 25] });
  }

  function renderStaticMapLayers() {
    // 1. Simulation Area Bounding Box (KOTAK AREA SIMULASI)
    state.mapLayers.boundaryGroup.clearLayers();
    
    const sw = metersToLatLng(0, 0);
    const ne = metersToLatLng(BBOX.widthMeters, BBOX.heightMeters);
    const nw = metersToLatLng(0, BBOX.heightMeters);

    // Bounding Box Rectangle (Subtle Flat Border, Zero Glow)
    const simBox = L.rectangle([sw, ne], {
      color: '#64748b',
      weight: 1.2,
      dashArray: '6, 6',
      fillColor: '#334155',
      fillOpacity: 0.02
    });
    state.mapLayers.boundaryGroup.addLayer(simBox);

    // Top Header Badge Label on the Box (Subtle Flat Badge)
    const labelMarker = L.marker(nw, {
      icon: L.divIcon({
        className: 'sim-box-badge-container',
        html: `<div class="sim-box-badge">📐 AREA SIMULASI PENEMPATAN PUSKESMAS (2.4 × 1.6 km)</div>`,
        iconSize: [290, 24],
        iconAnchor: [-5, -5]
      }),
      interactive: false
    });
    state.mapLayers.boundaryGroup.addLayer(labelMarker);

    // 2. Forbidden Zones (Kanal BKT & Danau)
    state.mapLayers.riverGroup.clearLayers();
    if (state.mapData.forbidden_zones) {
      for (const zone of state.mapData.forbidden_zones) {
        const latlngs = zone.polygon.map(pt => metersToLatLng(pt[0], pt[1]));
        const isRiver = zone.type === 'sungai' || zone.type === 'danau';
        const poly = L.polygon(latlngs, {
          color: isRiver ? '#0284c7' : '#e11d48',
          weight: 1.0,
          fillColor: isRiver ? '#0284c7' : '#e11d48',
          fillOpacity: 0.15,
          dashArray: '4, 4'
        });

        poly.bindPopup(`
          <div style="font-size:0.8rem; line-height:1.4;">
            <b style="color:${isRiver ? '#38bdf8' : '#fb7185'};">⚠️ ${zone.name}</b><br>
            <span style="color:#94a3b8;">Zona Terlarang Pembangunan Fasilitas Kesehatan.</span><br>
            <small style="color:#f87171;">Penalti Evaluasi: Mutlak (-1.000)</small>
          </div>
        `);
        state.mapLayers.riverGroup.addLayer(poly);
      }
    }

    // 3. Existing Puskesmas (Faskes Eksisting 1 & 2)
    state.mapLayers.faskesGroup.clearLayers();
    if (state.mapData.competitors) {
      state.mapData.competitors.forEach((comp, idx) => {
        const latlng = metersToLatLng(comp.x, comp.y);
        const isWest = idx === 0;

        // Coverage circle (800 meters - subtle outline)
        const coverageCircle = L.circle(latlng, {
          radius: 800,
          color: isWest ? '#3b82f6' : '#10b981',
          weight: 1.0,
          fillColor: isWest ? '#3b82f6' : '#10b981',
          fillOpacity: 0.05,
          dashArray: '4, 4'
        });
        state.mapLayers.faskesGroup.addLayer(coverageCircle);

        // Marker Pin (Flat Minimalist Badge)
        const pinIcon = L.divIcon({
          className: 'custom-faskes-pin',
          html: `
            <div class="puskesmas-marker-pin" style="background:${isWest ? '#1d4ed8' : '#059669'};">
              🏥
            </div>
          `,
          iconSize: [26, 26],
          iconAnchor: [13, 13],
          popupAnchor: [0, -15]
        });

        const marker = L.marker(latlng, { icon: pinIcon });
        marker.bindPopup(`
          <div style="font-size:0.8rem; line-height:1.4;">
            <strong style="color:${isWest ? '#60a5fa' : '#34d399'};">${comp.name}</strong><br>
            <span style="color:#94a3b8;">Puskesmas Eksisting Aktif</span><br>
            <span style="color:#cbd5e1;">Koordinat: (${comp.x.toFixed(0)}, ${comp.y.toFixed(0)}) m</span><br>
            <span style="color:#cbd5e1;">GPS: [${latlng[0].toFixed(5)}, ${latlng[1].toFixed(5)}]</span><br>
            <small style="color:#38bdf8;">Radius Layanan: 800 meter</small>
          </div>
        `);
        state.mapLayers.faskesGroup.addLayer(marker);
      });
    }

    // 4. Landmarks (GrandLucky, Santika, COURTS, Kaleyo, Mang Kabayan, etc.)
    state.mapLayers.landmarkGroup.clearLayers();
    if (state.mapData.facilities) {
      state.mapData.facilities.forEach(fac => {
        const latlng = metersToLatLng(fac.x, fac.y);
        
        let iconEmoji = '🏢';
        if (fac.type === 'pasar') iconEmoji = '🛒';
        else if (fac.type === 'sekolah') iconEmoji = '🎓';
        else if (fac.type === 'posyandu') iconEmoji = '🩺';

        const landmarkIcon = L.divIcon({
          className: 'custom-landmark-pin',
          html: `<div class="landmark-marker-pin">${iconEmoji}</div>`,
          iconSize: [22, 22],
          iconAnchor: [11, 11],
          popupAnchor: [0, -12]
        });

        const marker = L.marker(latlng, { icon: landmarkIcon });
        marker.bindPopup(`
          <div style="font-size:0.78rem;">
            <strong>${fac.name}</strong><br>
            <span style="color:#94a3b8;">Sentra Publik Penunjang</span><br>
            <span style="color:#cbd5e1;">Bobot Daya Tarik: ${fac.weight}</span>
          </div>
        `);
        state.mapLayers.landmarkGroup.addLayer(marker);
      });
    }

    // 5. Population Density Layer (Titik Kepadatan Penduduk)
    renderDensityLayer();
  }

  // Render Sebaran Titik Kepadatan Penduduk
  function renderDensityLayer() {
    state.mapLayers.densityGroup.clearLayers();
    if (!state.layersVisibility.density) return;

    if (state.mapData.houses && state.mapData.houses.length > 0) {
      state.mapData.houses.forEach((h, idx) => {
        const latlng = metersToLatLng(h.x, h.y);
        const w = h.weight || 3.0;

        // Color coding based on density weight
        let dotColor = '#38bdf8'; // Low
        let dotCategory = 'Rendah / Ruko';
        if (w >= 5.0) {
          dotColor = '#ef4444'; // Very Dense
          dotCategory = 'Sangat Padat (Perkampungan)';
        } else if (w >= 4.0) {
          dotColor = '#f97316'; // Dense
          dotCategory = 'Padat (Perumahan Padat)';
        } else if (w >= 3.0) {
          dotColor = '#eab308'; // Medium
          dotCategory = 'Sedang (Hunian Menengah)';
        }

        const circle = L.circleMarker(latlng, {
          radius: Math.max(3.5, Math.min(7.0, 2.5 + w * 0.7)),
          fillColor: dotColor,
          fillOpacity: 0.70,
          color: '#ffffff',
          weight: 0.9,
          renderer: state.canvasRenderer
        });

        circle.bindPopup(`
          <div style="font-size:0.75rem; line-height:1.4; min-width:185px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <b style="color:${dotColor};">👥 Titik #${idx + 1}</b>
              <span style="font-size:0.65rem; color:#94a3b8;">(${h.x.toFixed(0)}, ${h.y.toFixed(0)}) m</span>
            </div>
            <div style="color:#cbd5e1; font-size:0.7rem; margin-bottom:6px;">
              Kategori: <b>${dotCategory}</b>
            </div>
            <div style="background:#0b0f19; border:1px solid #1f2937; border-radius:2px; padding:6px; margin:6px 0;">
              <div style="display:flex; justify-content:space-between; font-size:0.68rem; margin-bottom:4px;">
                <span style="color:#94a3b8;">Bobot Kepadatan:</span>
                <b id="popVal_${idx}" style="color:var(--theme-primary); font-weight:700;">${w.toFixed(1)}</b>
              </div>
              <input type="range" min="1.0" max="6.0" step="0.1" value="${w}" 
                style="width:100%; height:4px; margin:2px 0;" 
                oninput="document.getElementById('popVal_${idx}').textContent = parseFloat(this.value).toFixed(1);" 
                id="popSlider_${idx}">
            </div>
            <div style="display:flex; gap:6px; margin-top:6px;">
              <button style="flex:1; padding:4px 6px; font-size:0.7rem; background:#f97316; color:white; border:none; border-radius:2px; cursor:pointer;" onclick="updateHouseWeight(${idx}, parseFloat(document.getElementById('popSlider_${idx}').value))">💾 Simpan</button>
              <button style="padding:4px 6px; font-size:0.7rem; background:#ef4444; color:white; border:none; border-radius:2px; cursor:pointer;" onclick="removeHousePoint(${idx})">🗑️ Hapus</button>
            </div>
          </div>
        `);

        state.mapLayers.densityGroup.addLayer(circle);
      });
    }
  }

  // Inisialisasi Panel Kurasi Kepadatan
  function initCurationUI() {
    const container = document.getElementById('curationListContainer');
    if (!container) return;

    const zones = state.mapData.curated_zones || [];
    if (zones.length === 0) {
      container.innerHTML = `<div style="font-size:0.75rem; color:#94a3b8;">Data kurasi zona belum dimuat.</div>`;
      return;
    }

    let html = '';
    zones.forEach(z => {
      const w = z.current_weight !== undefined ? z.current_weight : z.default_weight;
      
      let badgeClass = 'low';
      if (w >= 5.0) badgeClass = 'very-dense';
      else if (w >= 4.0) badgeClass = 'dense';
      else if (w >= 3.0) badgeClass = 'medium';

      html += `
        <div class="curation-item">
          <div class="curation-header">
            <span class="curation-name" title="${z.name}">${z.name}</span>
            <div class="curation-badge-val">
              <span class="curation-badge ${badgeClass}" id="curBadge_${z.id}">${z.category}</span>
              <span class="curation-val-text" id="curVal_${z.id}">${w.toFixed(1)}</span>
            </div>
          </div>
          <div class="curation-meta">
            <span>Est. ${z.estimated_families.toLocaleString('id-ID')} KK</span>
            <span style="color:#64748b;">${z.spread_radius}m radius</span>
          </div>
          <input type="range" class="custom-slider" id="curSlider_${z.id}" 
            min="1.0" max="6.0" step="0.1" value="${w}"
            oninput="onZoneSliderInput('${z.id}', this.value)">
        </div>
      `;
    });

    container.innerHTML = html;
  }

  window.onZoneSliderInput = function(zoneId, val) {
    const numVal = parseFloat(val);
    const valEl = document.getElementById(`curVal_${zoneId}`);
    if (valEl) valEl.textContent = numVal.toFixed(1);

    const badgeEl = document.getElementById(`curBadge_${zoneId}`);
    if (badgeEl) {
      let badgeClass = 'curation-badge low';
      let catText = 'Rendah';
      if (numVal >= 5.0) {
        badgeClass = 'curation-badge very-dense';
        catText = 'Sangat Padat';
      } else if (numVal >= 4.0) {
        badgeClass = 'curation-badge dense';
        catText = 'Padat';
      } else if (numVal >= 3.0) {
        badgeClass = 'curation-badge medium';
        catText = 'Sedang';
      }
      badgeEl.className = badgeClass;
      badgeEl.textContent = catText;
    }
  };

  window.applyCurationChanges = function() {
    const zones = state.mapData.curated_zones || [];
    zones.forEach(z => {
      const sliderEl = document.getElementById(`curSlider_${z.id}`);
      if (sliderEl) {
        z.current_weight = parseFloat(sliderEl.value);
      }
    });

    // Kalibrasi ulang bobot tiap rumah berdasarkan klaster zona terdekat
    if (state.mapData.houses) {
      state.mapData.houses.forEach(h => {
        let closestZone = null;
        let minDist = Infinity;
        for (const z of zones) {
          const dx = h.x - z.center_meter[0];
          const dy = h.y - z.center_meter[1];
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < minDist) {
            minDist = dist;
            closestZone = z;
          }
        }
        if (closestZone) {
          const base = h.base_weight !== undefined ? h.base_weight : h.weight;
          const ratio = closestZone.current_weight / (closestZone.default_weight || 4.0);
          h.weight = Math.max(1.0, Math.min(7.0, base * ratio));
        }
      });
    }

    renderDensityLayer();
    runOptimization();
    saveCurationToLocalStorage();

    // Flash status badge
    const badge = document.getElementById('curationStatusBadge');
    if (badge) {
      badge.textContent = '✓ Diterapkan';
      badge.style.color = '#10b981';
      setTimeout(() => {
        badge.textContent = `${zones.length} Klaster Wilayah`;
        badge.style.color = '';
      }, 2500);
    }
  };

  function saveCurationToLocalStorage() {
    try {
      const payload = {
        houses: state.mapData.houses,
        curated_zones: state.mapData.curated_zones
      };
      localStorage.setItem('puskesmas_harapan_indah_curation', JSON.stringify(payload));
    } catch (e) {
      console.warn('Could not save to localStorage:', e);
    }
  }

  window.toggleAddPointMode = function() {
    state.curationMode = state.curationMode === 'addPoint' ? 'normal' : 'addPoint';
    const isAdding = state.curationMode === 'addPoint';

    const btn = document.getElementById('btnAddPointMode');
    const icon = document.getElementById('addPointIcon');
    const text = document.getElementById('addPointText');

    if (btn) {
      if (isAdding) {
        btn.style.background = '#f97316';
        btn.style.color = '#ffffff';
        btn.style.borderColor = '#ea580c';
        icon.textContent = '✖';
        text.textContent = 'Klik Peta untuk Pasang';
      } else {
        btn.style.background = '';
        btn.style.color = '';
        btn.style.borderColor = '';
        icon.textContent = '➕';
        text.textContent = 'Tambah Titik di Peta';
      }
    }

    if (state.leafletMap) {
      state.leafletMap.getContainer().style.cursor = isAdding ? 'crosshair' : '';
    }
  };

  window.handleAddHousePoint = function(px, py, latlng) {
    if (px < 0 || px > BBOX.widthMeters || py < 0 || py > BBOX.heightMeters) {
      alert('Titik baru harus berada di dalam batas Kotak Simulasi Harapan Indah!');
      return;
    }

    const newPoint = {
      x: Math.round(px * 10) / 10,
      y: Math.round(py * 10) / 10,
      weight: 4.5,
      base_weight: 4.5
    };
    state.mapData.houses.push(newPoint);
    saveCurationToLocalStorage();
    renderDensityLayer();
    runOptimization();

    // Status feedback
    const badge = document.getElementById('curationStatusBadge');
    if (badge) {
      badge.textContent = `+ Titik #${state.mapData.houses.length}`;
      badge.style.color = '#38bdf8';
      setTimeout(() => {
        badge.textContent = `${(state.mapData.curated_zones || []).length} Klaster Wilayah`;
        badge.style.color = '';
      }, 2500);
    }
  };

  window.updateHouseWeight = function(idx, newWeight) {
    if (state.mapData.houses && state.mapData.houses[idx]) {
      state.mapData.houses[idx].weight = newWeight;
      state.mapData.houses[idx].base_weight = newWeight;
      saveCurationToLocalStorage();
      renderDensityLayer();
      runOptimization();
      state.leafletMap.closePopup();
    }
  };

  window.removeHousePoint = function(idx) {
    if (state.mapData.houses && state.mapData.houses[idx]) {
      state.mapData.houses.splice(idx, 1);
      saveCurationToLocalStorage();
      renderDensityLayer();
      runOptimization();
      state.leafletMap.closePopup();
    }
  };

  window.exportCurationJSON = function() {
    const exportData = {
      title: "Kurasi Kepadatan Penduduk Kota Harapan Indah",
      exportedAt: new Date().toISOString(),
      dimensions: state.mapData.dimensions,
      curated_zones: state.mapData.curated_zones,
      houses: state.mapData.houses,
      facilities: state.mapData.facilities,
      competitors: state.mapData.competitors,
      roads: state.mapData.roads,
      forbidden_zones: state.mapData.forbidden_zones
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `kurasi_harapan_indah_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  window.importCurationJSON = function(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = function(e) {
      try {
        const imported = JSON.parse(e.target.result);
        if (imported.houses && Array.isArray(imported.houses)) {
          state.mapData.houses = imported.houses;
        }
        if (imported.curated_zones && Array.isArray(imported.curated_zones)) {
          state.mapData.curated_zones = imported.curated_zones;
        }
        if (imported.facilities && Array.isArray(imported.facilities)) {
          state.mapData.facilities = imported.facilities;
        }
        saveCurationToLocalStorage();
        initCurationUI();
        renderDensityLayer();
        runOptimization();
        alert('Data kurasi JSON berhasil dimuat dan diterapkan ke peta!');
      } catch (err) {
        alert('Gagal memuat berkas JSON: ' + err.message);
      }
      event.target.value = '';
    };
    reader.readAsText(file);
  };

  window.resetCurationToDefault = function() {
    try {
      localStorage.removeItem('puskesmas_harapan_indah_curation');
    } catch (e) {}

    // Reload baseline preset
    if (window.PRESET_MAPS && window.PRESET_MAPS['harapan_indah']) {
      state.mapData = JSON.parse(JSON.stringify(window.PRESET_MAPS['harapan_indah']));
    }

    if (state.mapData.houses) {
      state.mapData.houses.forEach(h => {
        h.base_weight = h.weight;
      });
    }

    initCurationUI();
    renderDensityLayer();
    runOptimization();

    const badge = document.getElementById('curationStatusBadge');
    if (badge) {
      badge.textContent = '↺ Default';
      setTimeout(() => {
        badge.textContent = `${(state.mapData.curated_zones || []).length} Klaster Wilayah`;
      }, 2000);
    }
  };

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
    const W = BBOX.widthMeters;
    const H = BBOX.heightMeters;

    // 1. Boundary of simulation box
    if (px < 0 || px > W || py < 0 || py > H) {
      return { fitness: -1000.0, isValid: false, reason: "Di luar batas kotak simulasi" };
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
  // 4. Metaheuristic Algorithms (GA, PSO, ACO) Supporting 1, 2, or 3 Facilities
  // ==========================================================================
  function generateCandidatePoint() {
    const W = BBOX.widthMeters;
    const H = BBOX.heightMeters;
    if (Math.random() < 0.70 && state.mapData.roads && state.mapData.roads.length > 0) {
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

  function generateCandidateIndividual(pCount) {
    const ind = [];
    for (let k = 0; k < pCount; k++) {
      const pt = generateCandidatePoint();
      ind.push(pt[0], pt[1]);
    }
    return ind;
  }

  function evaluateIndividual(ind) {
    const pCount = state.facilityCount || 1;
    let totalRaw = 0;
    const points = [];
    let worstReason = "";
    let anyInvalid = false;
    let worstPenalty = 0;

    for (let k = 0; k < pCount; k++) {
      const px = ind[2 * k];
      const py = ind[2 * k + 1];
      points.push([px, py]);
      const ev = evaluatePoint(px, py);
      if (!ev.isValid) {
        anyInvalid = true;
        worstPenalty = Math.min(worstPenalty, ev.fitness);
        worstReason = ev.reason;
      } else {
        totalRaw += ev.rawScore;
      }
    }

    if (anyInvalid) {
      return {
        fitness: worstPenalty,
        isValid: false,
        reason: worstReason,
        points
      };
    }

    const avgScore = totalRaw / pCount;
    let cannibalPenalty = 0.0;

    // Spacing / Cannibalization penalty if pCount > 1
    if (pCount > 1) {
      for (let i = 0; i < pCount; i++) {
        for (let j = i + 1; j < pCount; j++) {
          const d = Math.hypot(points[i][0] - points[j][0], points[i][1] - points[j][1]);
          if (d < 450.0) {
            const overlap = 1.0 - (d / 450.0);
            cannibalPenalty += 0.50 * (overlap * overlap);
          }
        }
      }
    }

    const netScore = Math.max(0, avgScore - cannibalPenalty);
    const finalFitness = state.mode === 'max' ? netScore : (1.0 - netScore);

    return {
      fitness: finalFitness,
      avgScore,
      cannibalPenalty,
      isValid: true,
      points
    };
  }

  function runOptimization() {
    const W = BBOX.widthMeters;
    const H = BBOX.heightMeters;
    const popSize = 40;
    const maxGen = state.sim.totalFrames;
    const pCount = state.facilityCount || 1;
    const dim = 2 * pCount;

    // 1. Real-Coded Genetic Algorithm (GA)
    const t0 = performance.now();
    let gaPop = [];
    for (let i = 0; i < popSize; i++) {
      gaPop.push(generateCandidateIndividual(pCount));
    }

    state.sim.gaHistory = [];
    let gaGlobalBest = null;
    let gaGlobalBestFit = -Infinity;

    for (let g = 0; g < maxGen; g++) {
      const popWithFit = gaPop.map(ind => ({
        pos: ind,
        fit: evaluateIndividual(ind).fitness
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
        const child = new Array(dim);
        for (let d = 0; d < dim; d++) {
          const cMin = Math.min(p1[d], p2[d]);
          const cMax = Math.max(p1[d], p2[d]);
          const range = cMax - cMin;
          child[d] = cMin - alpha * range + Math.random() * (range + 2 * alpha * range);
          const bound = (d % 2 === 0) ? W : H;
          child[d] = Math.max(0, Math.min(bound, child[d]));
          if (Math.random() < 0.12) {
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
      const pos = generateCandidateIndividual(pCount);
      const vel = [];
      for (let d = 0; d < dim; d++) {
        const bound = (d % 2 === 0) ? W : H;
        vel.push((Math.random() - 0.5) * bound * 0.04);
      }
      psoParticles.push(pos);
      psoVelocities.push(vel);
      pBestPos.push([...pos]);
      const fit = evaluateIndividual(pos).fitness;
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
        for (let d = 0; d < dim; d++) {
          const r1 = Math.random(), r2 = Math.random();
          psoVelocities[i][d] = 
            wInertia * psoVelocities[i][d] +
            c1 * r1 * (pBestPos[i][d] - psoParticles[i][d]) +
            c2 * r2 * (psoGBestPos[d] - psoParticles[i][d]);
          
          const bound = (d % 2 === 0) ? W : H;
          const vMax = bound * 0.10;
          psoVelocities[i][d] = Math.max(-vMax, Math.min(vMax, psoVelocities[i][d]));
          psoParticles[i][d] += psoVelocities[i][d];

          if (psoParticles[i][d] < 0) {
            psoParticles[i][d] = -psoParticles[i][d];
            psoVelocities[i][d] = -psoVelocities[i][d];
          } else if (psoParticles[i][d] > bound) {
            psoParticles[i][d] = 2 * bound - psoParticles[i][d];
            psoVelocities[i][d] = -psoVelocities[i][d];
          }
        }

        const fit = evaluateIndividual(psoParticles[i]).fitness;
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
      const pos = generateCandidateIndividual(pCount);
      archive.push({ pos, fit: evaluateIndividual(pos).fitness });
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
        const antPos = new Array(dim);
        for (let d = 0; d < dim; d++) {
          let sumDiff = 0;
          for (let e = 0; e < popSize; e++) {
            sumDiff += Math.abs(archive[e].pos[d] - centerPos[d]);
          }
          const sigma = xiDispersion * (sumDiff / (popSize - 1));
          const u1 = Math.random() || 1e-7;
          const u2 = Math.random();
          const z = Math.sqrt(-2.0 * Math.log(u1)) * Math.cos(2.0 * Math.PI * u2);
          antPos[d] = centerPos[d] + sigma * z;
          const bound = (d % 2 === 0) ? W : H;
          antPos[d] = Math.max(0, Math.min(bound, antPos[d]));
        }

        const fit = evaluateIndividual(antPos).fitness;
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

    // Update Scorecard Table
    updateKpisAndScorecard();

    // Start Smooth Generational Animation from 0 to 50
    startSmoothPlayback();
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
  // 5. OpenStreetMap Leaflet Rendering Engine (Silky-Smooth Canvas)
  // ==========================================================================
  function renderCurrentFrame() {
    const frame = state.sim.currentFrame;
    if (!state.sim.gaHistory[frame] || !state.sim.psoHistory[frame] || !state.sim.acoHistory[frame]) return;

    // 1. Clear dynamic layers
    state.mapLayers.particlesGroup.clearLayers();
    state.mapLayers.optimalGroup.clearLayers();
    state.mapLayers.linesGroup.clearLayers();

    // 2. High-performance rendering of candidate particles
    if (state.layersVisibility.particles) {
      const renderPop = (pop, color, radius) => {
        const pCount = state.facilityCount || 1;
        for (const ind of pop) {
          for (let k = 0; k < pCount; k++) {
            const px = ind[2 * k];
            const py = ind[2 * k + 1];
            if (px !== undefined && py !== undefined) {
              const latlng = metersToLatLng(px, py);
              const circle = L.circleMarker(latlng, {
                radius: radius,
                color: '#ffffff',
                weight: 1.0,
                fillColor: color,
                fillOpacity: 0.80
              });
              state.mapLayers.particlesGroup.addLayer(circle);
            }
          }
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

    // 3. Determine Best Solution for current frame
    let frameBest = state.sim.psoHistory[frame].bestPos;
    let frameBestFit = state.sim.psoHistory[frame].bestFit;
    let bestAlgoName = "PSO";

    if (state.activeAlgo === 'ga') {
      frameBest = state.sim.gaHistory[frame].bestPos;
      frameBestFit = state.sim.gaHistory[frame].bestFit;
      bestAlgoName = "GA";
    } else if (state.activeAlgo === 'aco') {
      frameBest = state.sim.acoHistory[frame].bestPos;
      frameBestFit = state.sim.acoHistory[frame].bestFit;
      bestAlgoName = "ACO";
    } else {
      if (state.sim.gaHistory[frame].bestFit > frameBestFit) {
        frameBest = state.sim.gaHistory[frame].bestPos;
        frameBestFit = state.sim.gaHistory[frame].bestFit;
        bestAlgoName = "GA";
      }
      if (state.sim.acoHistory[frame].bestFit > frameBestFit) {
        frameBest = state.sim.acoHistory[frame].bestPos;
        frameBestFit = state.sim.acoHistory[frame].bestFit;
        bestAlgoName = "ACO";
      }
    }

    // 4. Render Best Solution Markers on OpenStreetMap (Supporting 1, 2, or 3 Facilities)
    const pCount = state.facilityCount || 1;
    if (state.layersVisibility.optimal && frameBest) {
      const bestCoords = [];
      const bestLatLngs = [];

      for (let k = 0; k < pCount; k++) {
        const bx = frameBest[2 * k];
        const by = frameBest[2 * k + 1];
        if (bx === undefined || by === undefined) continue;
        const bestLatLng = metersToLatLng(bx, by);
        bestCoords.push([bx, by]);
        bestLatLngs.push(bestLatLng);

        const pinLabel = pCount === 1 ? '⭐' : `⭐ #${k + 1}`;
        const pinIcon = L.divIcon({
          className: 'custom-optimal-badge',
          html: `<div class="optimal-marker-pin">${pinLabel}</div>`,
          iconSize: [pCount === 1 ? 28 : 46, 28],
          iconAnchor: [pCount === 1 ? 14 : 23, 14],
          popupAnchor: [0, -16]
        });

        const bestMarker = L.marker(bestLatLng, { icon: pinIcon });
        const roadInfo = getNearestRoadInfo(bx, by);

        let d1 = 1145, d2 = 1074;
        if (state.mapData.competitors && state.mapData.competitors.length >= 2) {
          const c1 = state.mapData.competitors[0];
          const c2 = state.mapData.competitors[1];
          d1 = Math.round(Math.hypot(c1.x - bx, c1.y - by));
          d2 = Math.round(Math.hypot(c2.x - bx, c2.y - by));
        }

        const titleText = pCount === 1 
          ? `⭐ Rekomendasi (${bestAlgoName})`
          : `⭐ Puskesmas Baru #${k + 1} (${bestAlgoName})`;

        bestMarker.bindPopup(`
          <div style="font-size:0.8rem; min-width:210px; line-height:1.4;">
            <b style="color:var(--theme-primary); font-size:0.88rem;">${titleText}</b><br>
            <span style="color:#f8fafc; font-weight:600;">${roadInfo.roadName}</span><br>
            <div style="margin: 0.3rem 0; padding: 0.25rem 0.4rem; background:rgba(249,115,22,0.12); border:1px solid rgba(249,115,22,0.25); border-radius:2px;">
              <span style="color:#fb923c; font-weight:700;">Skor Fitness: ${frameBestFit.toFixed(4)}</span><br>
              <small style="color:#94a3b8;">Koordinat: (${bx.toFixed(0)}, ${by.toFixed(0)}) m</small><br>
              <small style="color:#94a3b8;">GPS: [${bestLatLng[0].toFixed(5)}, ${bestLatLng[1].toFixed(5)}]</small>
            </div>
            <span style="color:#93c5fd;">Ke Pusk. Ujung Menteng: <b>${d1} m</b></span><br>
            <span style="color:#6ee7b7;">Ke Pusk. Pejuang: <b>${d2} m</b></span><br>
            <small style="color:#a7f3d0;">✓ Akses Ambulans & Transportasi Prima</small>
          </div>
        `);
        state.mapLayers.optimalGroup.addLayer(bestMarker);

        // 5. Render Dotted Distance Lines to Existing Puskesmas
        if (state.layersVisibility.lines && state.mapData.competitors) {
          state.mapData.competitors.forEach((comp, idx) => {
            const compLatLng = metersToLatLng(comp.x, comp.y);
            const distM = Math.round(Math.hypot(comp.x - bx, comp.y - by));
            const isWest = idx === 0;

            const line = L.polyline([bestLatLng, compLatLng], {
              color: isWest ? '#3b82f6' : '#10b981',
              weight: 1.2,
              dashArray: '5, 5',
              opacity: 0.70
            });
            state.mapLayers.linesGroup.addLayer(line);

            const midLat = (bestLatLng[0] + compLatLng[0]) / 2;
            const midLng = (bestLatLng[1] + compLatLng[1]) / 2;
            const labelIcon = L.divIcon({
              className: 'distance-label-container',
              html: `<div class="distance-label-pin" style="border-color:${isWest ? '#3b82f6' : '#10b981'}; color:${isWest ? '#93c5fd' : '#a7f3d0'};">${distM.toLocaleString()} m</div>`,
              iconSize: [55, 18],
              iconAnchor: [27, 9]
            });
            state.mapLayers.linesGroup.addLayer(L.marker([midLat, midLng], { icon: labelIcon, interactive: false }));
          });
        }
      }

      // If pCount > 1, render distance line between the newly placed Puskesmas
      if (state.layersVisibility.lines && pCount > 1) {
        for (let i = 0; i < pCount; i++) {
          for (let j = i + 1; j < pCount; j++) {
            const dBetween = Math.round(Math.hypot(bestCoords[i][0] - bestCoords[j][0], bestCoords[i][1] - bestCoords[j][1]));
            const line = L.polyline([bestLatLngs[i], bestLatLngs[j]], {
              color: '#f97316',
              weight: 1.5,
              dashArray: '4, 4',
              opacity: 0.85
            });
            state.mapLayers.linesGroup.addLayer(line);

            const midLat = (bestLatLngs[i][0] + bestLatLngs[j][0]) / 2;
            const midLng = (bestLatLngs[i][1] + bestLatLngs[j][1]) / 2;
            const labelIcon = L.divIcon({
              className: 'distance-label-container',
              html: `<div class="distance-label-pin" style="border-color:#f97316; color:#fdba74;">Jarak: ${dBetween.toLocaleString()} m</div>`,
              iconSize: [85, 18],
              iconAnchor: [42, 9]
            });
            state.mapLayers.linesGroup.addLayer(L.marker([midLat, midLng], { icon: labelIcon, interactive: false }));
          }
        }
      }

      if (bestCoords.length > 0) {
        const roadInfo0 = getNearestRoadInfo(bestCoords[0][0], bestCoords[0][1]);
        updateKpisForPoint(bestCoords[0], frameBestFit, roadInfo0, 0, 0);
      }
    }
  }

  function updateKpisForPoint(pos, fit, road, d1, d2) {
    if (elKpiCoords) elKpiCoords.innerHTML = `(${pos[0].toFixed(0)}, ${pos[1].toFixed(0)}) <span style="font-size:0.75rem; font-weight:normal; color:#9ca3af;">m</span>`;
    if (elKpiFitness) elKpiFitness.textContent = fit.toFixed(4);
    if (elKpiRoadName) elKpiRoadName.textContent = `${road.roadName} (${road.distance.toFixed(0)}m)`;
    if (elKpiDistP1) elKpiDistP1.innerHTML = `${d1.toLocaleString()} <span style="font-size:0.75rem; font-weight:normal; color:#9ca3af;">meter</span>`;
    if (elKpiDistP2) elKpiDistP2.innerHTML = `${d2.toLocaleString()} <span style="font-size:0.75rem; font-weight:normal; color:#9ca3af;">meter</span>`;
  }

  // ==========================================================================
  // 6. Interactive Spatial Point Inspector (On OpenStreetMap Click)
  // ==========================================================================
  function inspectSpatialPoint(px, py, latlng) {
    const res = evaluatePoint(px, py);
    state.inspectedPoint = { x: px, y: py, res, latlng };

    // Update Sidebar Panel
    elInspCoords.textContent = `(${px.toFixed(0)}, ${py.toFixed(0)}) m`;

    if (res.roadInfo) {
      elInspRoad.textContent = res.roadInfo.roadName;
      elInspRoadDist.textContent = `${res.roadInfo.distance.toFixed(1)} m`;
    } else {
      const roadInfo = getNearestRoadInfo(px, py);
      elInspRoad.textContent = roadInfo.roadName;
      elInspRoadDist.textContent = `${roadInfo.distance.toFixed(1)} m`;
    }

    if (res.distsToExisting && res.distsToExisting.length >= 2) {
      elInspDistP1.textContent = `${Math.round(res.distsToExisting[0])} m`;
      elInspDistP2.textContent = `${Math.round(res.distsToExisting[1])} m`;
    } else {
      elInspDistP1.textContent = "-";
      elInspDistP2.textContent = "-";
    }

    if (res.isValid) {
      elInspZonasi.textContent = "Legal (Diizinkan)";
      elInspZonasi.style.color = "var(--theme-emerald)";
      elInspScore.textContent = res.fitness.toFixed(4);
      elInspStatusBadge.textContent = "Titik Sah";
      elInspStatusBadge.style.color = "var(--theme-emerald)";
    } else {
      elInspZonasi.textContent = res.reason || "Terlarang";
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
      iconSize: [26, 26],
      iconAnchor: [13, 13],
      popupAnchor: [0, -15]
    });

    const inspMarker = L.marker(latlng, { icon: inspIcon }).addTo(state.mapLayers.inspectorGroup);
    
    let distP1Text = res.distsToExisting && res.distsToExisting[0] ? `${Math.round(res.distsToExisting[0])} m` : '-';
    let distP2Text = res.distsToExisting && res.distsToExisting[1] ? `${Math.round(res.distsToExisting[1])} m` : '-';

    inspMarker.bindPopup(`
      <div style="font-size:0.8rem; line-height:1.4;">
        <strong style="color:${res.isValid ? '#38bdf8' : '#fb7185'};">${res.isValid ? 'Titik Inspeksi Sah' : 'Titik Tidak Layak'}</strong><br>
        <span style="color:#cbd5e1;">Koordinat: (${px.toFixed(0)}, ${py.toFixed(0)}) m</span><br>
        <span style="color:#94a3b8;">Jalan: ${res.roadInfo ? res.roadInfo.roadName : '-'} (${res.roadInfo ? res.roadInfo.distance.toFixed(0) : '-'}m)</span><br>
        <span style="color:#93c5fd;">Ke Pusk. Barat: ${distP1Text}</span><br>
        <span style="color:#6ee7b7;">Ke Pusk. Timur: ${distP2Text}</span><br>
        <b style="color:${res.isValid ? 'var(--theme-primary)' : '#f87171'};">Fitness: ${res.fitness.toFixed(4)}</b>
      </div>
    `).openPopup();
  }

  // ==========================================================================
  // 7. Convergence Chart Rendering (Synchronized Live Curve)
  // ==========================================================================
  function renderConvergenceChart() {
    const W = elChartCanvas.clientWidth;
    const H = elChartCanvas.clientHeight;
    ctxChart.clearRect(0, 0, W, H);

    const padL = 40, padR = 15, padT = 12, padB = 22;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    let maxFit = 1.0;
    let minFit = 0.0;

    const allFits = [];
    state.sim.gaHistory.forEach(h => allFits.push(h.bestFit));
    state.sim.psoHistory.forEach(h => allFits.push(h.bestFit));
    state.sim.acoHistory.forEach(h => allFits.push(h.bestFit));
    
    if (allFits.length > 0) {
      maxFit = Math.max(...allFits);
      minFit = Math.min(...allFits);
      const span = Math.max(0.1, maxFit - minFit);
      maxFit = Math.min(1.0, maxFit + 0.04 * span);
      minFit = Math.max(0.0, minFit - 0.08 * span);
    }

    // Gridlines & Y-labels (Flat & Minimalist)
    ctxChart.strokeStyle = '#1e293b';
    ctxChart.lineWidth = 1;
    ctxChart.fillStyle = '#64748b';
    ctxChart.font = '9px Inter, sans-serif';
    ctxChart.textAlign = 'right';

    for (let i = 0; i <= 4; i++) {
      const yVal = minFit + (i / 4) * (maxFit - minFit);
      const yPos = padT + plotH - (i / 4) * plotH;
      ctxChart.beginPath();
      ctxChart.moveTo(padL, yPos);
      ctxChart.lineTo(padL + plotW, yPos);
      ctxChart.stroke();
      ctxChart.fillText(yVal.toFixed(2), padL - 5, yPos + 3);
    }

    // X-axis labels
    ctxChart.textAlign = 'center';
    for (let g = 0; g <= 50; g += 10) {
      const xPos = padL + (g / 50) * plotW;
      ctxChart.fillText(`g${g}`, xPos, H - 5);
    }

    // Draw Line up to current frame (Live Progress)
    const curFrame = state.sim.currentFrame;
    const drawCurve = (history, color, width) => {
      if (!history || history.length === 0) return;
      ctxChart.beginPath();
      ctxChart.strokeStyle = color;
      ctxChart.lineWidth = width;
      ctxChart.lineJoin = 'round';

      const limit = Math.min(history.length - 1, curFrame);
      for (let g = 0; g <= limit; g++) {
        const fit = history[g].bestFit;
        const normFit = (fit - minFit) / (maxFit - minFit || 1);
        const xPos = padL + (g / 49) * plotW;
        const yPos = padT + plotH - normFit * plotH;

        if (g === 0) ctxChart.moveTo(xPos, yPos);
        else ctxChart.lineTo(xPos, yPos);
      }
      ctxChart.stroke();
    };

    if (state.activeAlgo === 'split_3' || state.activeAlgo === 'ga') {
      drawCurve(state.sim.gaHistory, '#3b82f6', 1.8);
    }
    if (state.activeAlgo === 'split_3' || state.activeAlgo === 'pso') {
      drawCurve(state.sim.psoHistory, '#f97316', 2.0);
    }
    if (state.activeAlgo === 'split_3' || state.activeAlgo === 'aco') {
      drawCurve(state.sim.acoHistory, '#10b981', 1.8);
    }

    // Progress Vertical Cursor
    const curX = padL + (curFrame / 49) * plotW;
    ctxChart.beginPath();
    ctxChart.strokeStyle = 'rgba(255, 255, 255, 0.35)';
    ctxChart.lineWidth = 1;
    ctxChart.setLineDash([3, 3]);
    ctxChart.moveTo(curX, padT);
    ctxChart.lineTo(curX, padT + plotH);
    ctxChart.stroke();
    ctxChart.setLineDash([]);
  }

  // ==========================================================================
  // 8. KPI Cards & Scorecard Table Updates
  // ==========================================================================
  function updateKpisAndScorecard() {
    const gaFit = state.sim.bestFitnesses.ga;
    const psoFit = state.sim.bestFitnesses.pso;
    const acoFit = state.sim.bestFitnesses.aco;

    document.getElementById('tblFitGA').textContent = gaFit.toFixed(4);
    document.getElementById('tblFitPSO').textContent = psoFit.toFixed(4);
    document.getElementById('tblFitACO').textContent = acoFit.toFixed(4);

    document.getElementById('tblTimeGA').textContent = `${state.sim.times.ga} s`;
    document.getElementById('tblTimePSO').textContent = `${state.sim.times.pso} s`;
    document.getElementById('tblTimeACO').textContent = `${state.sim.times.aco} s`;
  }

  // ==========================================================================
  // 9. Smooth Animation & Playback Engine
  // ==========================================================================
  function startSmoothPlayback() {
    pausePlayback();
    state.sim.currentFrame = 0;
    elScrubber.value = 0;
    elIterLabel.textContent = `0 / ${state.sim.totalFrames}`;
    elChartGenBadge.textContent = `Generasi: 0 / ${state.sim.totalFrames}`;
    
    state.sim.isRunning = true;
    elPlayIcon.textContent = '⏸';
    elPlayText.textContent = 'Jeda';

    const intervalMs = Math.max(15, Math.round(1000 / state.sim.fps));
    state.sim.intervalId = setInterval(() => {
      state.sim.currentFrame++;
      if (state.sim.currentFrame >= state.sim.totalFrames) {
        state.sim.currentFrame = state.sim.totalFrames - 1;
        pausePlayback();
      }
      elScrubber.value = state.sim.currentFrame;
      elIterLabel.textContent = `${state.sim.currentFrame} / ${state.sim.totalFrames}`;
      elChartGenBadge.textContent = `Generasi: ${state.sim.currentFrame} / ${state.sim.totalFrames}`;

      renderCurrentFrame();
      renderConvergenceChart();
    }, intervalMs);
  }

  window.setFacilityCount = function(count) {
    state.facilityCount = parseInt(count, 10) || 1;
    [1, 2, 3].forEach(c => {
      const btn = document.getElementById(`btnCount${c}`);
      if (btn) btn.classList.toggle('active', c === state.facilityCount);
    });
    const tag = document.getElementById('facilityCountTag');
    if (tag) {
      tag.textContent = `${state.facilityCount} Unit`;
    }
    runOptimization();
  };

  window.runOptimization = function() {
    runOptimization();
  };

  window.togglePlayback = function() {
    if (state.sim.isRunning) {
      pausePlayback();
    } else {
      resumePlayback();
    }
  };

  function resumePlayback() {
    if (state.sim.currentFrame >= state.sim.totalFrames - 1) {
      state.sim.currentFrame = 0;
    }
    state.sim.isRunning = true;
    elPlayIcon.textContent = '⏸';
    elPlayText.textContent = 'Jeda';

    const intervalMs = Math.max(15, Math.round(1000 / state.sim.fps));
    state.sim.intervalId = setInterval(() => {
      state.sim.currentFrame++;
      if (state.sim.currentFrame >= state.sim.totalFrames) {
        state.sim.currentFrame = state.sim.totalFrames - 1;
        pausePlayback();
      }
      elScrubber.value = state.sim.currentFrame;
      elIterLabel.textContent = `${state.sim.currentFrame} / ${state.sim.totalFrames}`;
      elChartGenBadge.textContent = `Generasi: ${state.sim.currentFrame} / ${state.sim.totalFrames}`;
      
      renderCurrentFrame();
      renderConvergenceChart();
    }, intervalMs);
  }

  function pausePlayback() {
    state.sim.isRunning = false;
    if (state.sim.intervalId) {
      clearInterval(state.sim.intervalId);
      state.sim.intervalId = null;
    }
    elPlayIcon.textContent = '▶';
    elPlayText.textContent = 'Putar';
  }

  window.resetPlayback = function() {
    pausePlayback();
    state.sim.currentFrame = 0;
    elScrubber.value = 0;
    elIterLabel.textContent = `0 / ${state.sim.totalFrames}`;
    elChartGenBadge.textContent = `Generasi: 0 / ${state.sim.totalFrames}`;
    renderCurrentFrame();
    renderConvergenceChart();
  };

  window.stepForward = function() {
    pausePlayback();
    if (state.sim.currentFrame < state.sim.totalFrames - 1) {
      state.sim.currentFrame++;
      elScrubber.value = state.sim.currentFrame;
      elIterLabel.textContent = `${state.sim.currentFrame} / ${state.sim.totalFrames}`;
      elChartGenBadge.textContent = `Generasi: ${state.sim.currentFrame} / ${state.sim.totalFrames}`;
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
      elChartGenBadge.textContent = `Generasi: ${state.sim.currentFrame} / ${state.sim.totalFrames}`;
      renderCurrentFrame();
      renderConvergenceChart();
    }
  };

  window.onScrub = function(val) {
    pausePlayback();
    state.sim.currentFrame = parseInt(val, 10);
    elIterLabel.textContent = `${state.sim.currentFrame} / ${state.sim.totalFrames}`;
    elChartGenBadge.textContent = `Generasi: ${state.sim.currentFrame} / ${state.sim.totalFrames}`;
    renderCurrentFrame();
    renderConvergenceChart();
  };

  window.onSpeedChange = function(val) {
    state.sim.fps = parseInt(val, 10);
    document.getElementById('speedLabel').textContent = `${state.sim.fps} FPS`;
    if (state.sim.isRunning) {
      pausePlayback();
      resumePlayback();
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

  window.toggleLayer = function(layerKey) {
    state.layersVisibility[layerKey] = !state.layersVisibility[layerKey];
    
    const chipIdMap = {
      boundary: 'togBoundary',
      density: 'togDensity',
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

    if (layerKey === 'boundary') {
      if (state.layersVisibility.boundary) state.leafletMap.addLayer(state.mapLayers.boundaryGroup);
      else state.leafletMap.removeLayer(state.mapLayers.boundaryGroup);
    } else if (layerKey === 'density') {
      if (state.layersVisibility.density) {
        renderDensityLayer();
        state.leafletMap.addLayer(state.mapLayers.densityGroup);
      } else {
        state.leafletMap.removeLayer(state.mapLayers.densityGroup);
      }
    } else if (layerKey === 'river') {
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

  // Expose state globally for inspection and programmatic access
  window.appState = state;

  // Launch on DOM ready
  window.addEventListener('DOMContentLoaded', init);

})();
