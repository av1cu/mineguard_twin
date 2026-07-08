import streamlit as st
import os

def render_page():
    # Page Header Info
    st.markdown("""
    <style>
        .reportview-container .main .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    browser_api_url = "http://localhost:8000"
    
    # We embed the complete unified industrial SCADA console inside a single sandboxed iframe
    html_code = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <style>
        * {
          box-sizing: border-box;
          margin: 0;
          padding: 0;
        }
        body {
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
          background-color: #030712;
          color: #f3f4f6;
          height: 100vh;
          overflow: hidden;
          display: flex;
        }
        
        /* SCADA Main Layout Split */
        .scada-container {
          display: flex;
          width: 100vw;
          height: 100vh;
          border: 1px solid #1f2937;
        }
        
        /* Left Section: Map canvas */
        .map-section {
          flex: 1;
          position: relative;
          background-color: #070a13;
        }
        canvas {
          display: block;
          width: 100%;
          height: 100%;
          cursor: grab;
        }
        canvas:active {
          cursor: grabbing;
        }
        
        /* Right Section: SCADA Sidebar */
        .sidebar {
          width: 380px;
          border-left: 1px solid #1f2937;
          background-color: #0b0f19;
          display: flex;
          flex-direction: column;
          overflow-y: auto;
          box-shadow: -4px 0 20px rgba(0, 0, 0, 0.4);
        }
        
        .sidebar-header {
          padding: 16px;
          border-bottom: 1px solid #1f2937;
          background: linear-gradient(180deg, #0f172a, #0b0f19);
        }
        .sidebar-header h2 {
          font-size: 16px;
          font-weight: 700;
          color: #38bdf8;
          text-transform: uppercase;
          letter-spacing: 1px;
          display: flex;
          align-items: center;
          gap: 8px;
        }
        .system-status {
          font-size: 11px;
          color: #9ca3af;
          margin-top: 6px;
          display: flex;
          justify-content: space-between;
        }
        
        /* Sidebar Blocks */
        .control-panel {
          padding: 16px;
          border-bottom: 1px solid #1f2937;
        }
        .panel-title {
          font-size: 11px;
          font-weight: 600;
          color: #6b7280;
          text-transform: uppercase;
          margin-bottom: 10px;
          letter-spacing: 0.5px;
        }
        .btn-group {
          display: flex;
          gap: 8px;
          margin-bottom: 12px;
        }
        button {
          flex: 1;
          padding: 8px 12px;
          border-radius: 4px;
          border: 1px solid #374151;
          background-color: #1f2937;
          color: #fff;
          font-size: 12px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s;
        }
        button:hover {
          background-color: #374151;
          border-color: #4b5563;
        }
        button.btn-primary {
          background-color: #0284c7;
          border-color: #0369a1;
        }
        button.btn-primary:hover {
          background-color: #0369a1;
        }
        button.btn-danger {
          background-color: #dc2626;
          border-color: #b91c1c;
        }
        button.btn-danger:hover {
          background-color: #b91c1c;
        }
        
        /* Speed and Select controls */
        .control-row {
          margin-bottom: 10px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          font-size: 12px;
        }
        .control-row label {
          color: #9ca3af;
        }
        select, input[type="range"] {
          background-color: #1f2937;
          border: 1px solid #374151;
          color: #fff;
          border-radius: 4px;
          padding: 4px 8px;
          font-size: 12px;
          outline: none;
        }
        select {
          width: 150px;
        }
        
        /* Equipment List Grid */
        .equipment-block {
          padding: 16px;
          border-bottom: 1px solid #1f2937;
          flex: 1;
        }
        .equipment-list {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .equipment-card {
          background-color: #111827;
          border: 1px solid #1f2937;
          border-radius: 6px;
          padding: 10px;
          cursor: pointer;
          transition: all 0.2s;
          position: relative;
        }
        .equipment-card:hover, .equipment-card.selected {
          border-color: #0284c7;
          background-color: #1e293b;
        }
        .card-header-row {
          display: flex;
          justify-content: space-between;
          font-size: 12px;
          font-weight: 700;
          margin-bottom: 4px;
        }
        .status-badge {
          font-size: 9px;
          padding: 1px 4px;
          border-radius: 3px;
          font-weight: 800;
          text-transform: uppercase;
        }
        .badge-running { background-color: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid #10b981; }
        .badge-stopped { background-color: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid #ef4444; }
        .badge-loading { background-color: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid #f59e0b; }
        
        .card-body-row {
          display: flex;
          justify-content: space-between;
          font-size: 11px;
          color: #9ca3af;
        }
        
        /* Event alarm list */
        .alarms-block {
          padding: 16px;
          max-height: 250px;
          overflow-y: auto;
          background-color: #0c0f1d;
        }
        .alarm-item {
          padding: 8px;
          border-radius: 4px;
          margin-bottom: 6px;
          font-size: 11px;
          background-color: #1e1b1b;
          border: 1px solid #7f1d1d;
          animation: pulse-red 2s infinite;
        }
        .alarm-item-title {
          font-weight: bold;
          color: #ef4444;
          margin-bottom: 2px;
        }
        .alarm-item-desc {
          color: #fca5a5;
        }
        
        @keyframes pulse-red {
          0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.4); }
          70% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
          100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
        }
        
        /* Hover HUD Telemetry overlay */
        .hud-telemetry {
          position: absolute;
          top: 16px;
          left: 16px;
          background-color: rgba(15, 23, 42, 0.85);
          border: 1px solid #0284c7;
          border-radius: 6px;
          padding: 12px;
          width: 250px;
          pointer-events: none;
          display: none;
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
          backdrop-filter: blur(4px);
        }
        .hud-title {
          font-size: 12px;
          font-weight: 700;
          color: #38bdf8;
          margin-bottom: 6px;
          border-bottom: 1px solid #334155;
          padding-bottom: 4px;
        }
        .hud-row {
          display: flex;
          justify-content: space-between;
          font-size: 11px;
          margin-bottom: 4px;
        }
        .hud-label {
          color: #94a3b8;
        }
        .hud-value {
          font-weight: 600;
          color: #f8fafc;
        }
        
        /* Controls floating help block */
        .controls-help {
          position: absolute;
          bottom: 16px;
          left: 16px;
          background-color: rgba(15, 23, 42, 0.7);
          border: 1px solid #334155;
          border-radius: 4px;
          padding: 6px 10px;
          font-size: 10px;
          color: #94a3b8;
          pointer-events: none;
        }
      </style>
    </head>
    <body>
      <div class="scada-container">
        <!-- Canvas/Map Section -->
        <div class="map-section">
          <canvas id="scadaCanvas"></canvas>
          
          <!-- Hover HUD Overlay -->
          <div id="hudOverlay" class="hud-telemetry"></div>
          
          <!-- Instructions -->
          <div class="controls-help">
            🖱️ Перетаскивание: зажмите ЛКМ | 🔍 Масштаб: Колесико мыши
          </div>
        </div>
        
        <!-- Sidebar Controls Section -->
        <div class="sidebar">
          <div class="sidebar-header">
            <h2>⚙️ SCADA Digital Twin</h2>
            <div class="system-status">
              <span id="txtRunId">RUN ID: ---</span>
              <span id="txtTick">ТИК: 0 / 120</span>
            </div>
          </div>
          
          <!-- Playback controls -->
          <div class="control-panel">
            <div class="panel-title">Системные команды</div>
            <div class="btn-group">
              <button id="btnPlay" class="btn-primary">▶️ Пуск</button>
              <button id="btnPause">⏸️ Пауза</button>
              <button id="btnReset" class="btn-danger">⏮️ Сброс</button>
            </div>
            <div class="control-row">
              <label>Диспетчеризация:</label>
              <select id="selDispatcher">
                <option value="NaiveDispatcher">NaiveDispatcher</option>
                <option value="SmartDispatcher">SmartDispatcher</option>
              </select>
            </div>
            <div class="control-row">
              <label>Скорость симуляции:</label>
              <span id="lblSpeed">1.0 tick/s</span>
            </div>
            <input type="range" id="rngSpeed" min="0.5" max="20.0" step="0.5" value="1.0" style="width: 100%; margin-top: 4px;">
          </div>
          
          <!-- Equipment list -->
          <div class="equipment-block">
            <div class="panel-title">Телеметрия Самосвалов</div>
            <div id="equipmentList" class="equipment-list"></div>
          </div>
          
          <!-- Alarms Block -->
          <div class="alarms-block">
            <div class="panel-title" style="color: #ef4444;">⚠️ Лог тревог</div>
            <div id="alarmsList"></div>
          </div>
        </div>
      </div>
      
      <script>
        const canvas = document.getElementById('scadaCanvas');
        const ctx = canvas.getContext('scadaCanvas' ? '2d' : '3d');
        const hud = document.getElementById('hudOverlay');
        
        // Setup Resize
        function resizeCanvas() {
            canvas.width = canvas.parentElement.clientWidth;
            canvas.height = canvas.parentElement.clientHeight;
        }
        window.addEventListener('resize', resizeCanvas);
        resizeCanvas();
        
        // Scale & Pan States
        let zoom = 1.0;
        let panX = 0;
        let panY = 0;
        let isDragging = false;
        let startX = 0;
        let startY = 0;
        
        // Selected Equipment for target ring
        let selectedEquipmentId = null;
        
        // Data States
        let trucksData = {};
        let routesData = [];
        let alarmsData = [];
        let simulationState = { is_running: false, current_tick: 0, dispatcher: "NaiveDispatcher", run_id: "", speed_rate: 1.0 };
        
        // Map constants
        const chargingSite = { name: "DemoChargingSite", x: 0, y: 0 };
        const loadSites = [
            { name: "Shovel-01", x: 10, y: 20 },
            { name: "Shovel-02", x: -15, y: 30 },
            { name: "Shovel-03", x: 5, y: -25 }
        ];
        const dumpSites = [
            { name: "Dump-01", x: 40, y: 0 },
            { name: "Dump-02", x: -40, y: -10 }
        ];
        
        // Scale Factor
        const scale = 8.5;
        
        // Mouse Controls
        canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            startX = e.clientX - panX;
            startY = e.clientY - panY;
        });
        
        canvas.addEventListener('mousemove', (e) => {
            const rect = canvas.getBoundingClientRect();
            const mx = e.clientX - rect.left;
            const my = e.clientY - rect.top;
            
            if (isDragging) {
                panX = e.clientX - startX;
                panY = e.clientY - startY;
            }
            
            checkHover(mx, my);
        });
        
        canvas.addEventListener('mouseup', () => { isDragging = false; });
        canvas.addEventListener('mouseleave', () => { isDragging = false; });
        
        canvas.addEventListener('wheel', (e) => {
            e.preventDefault();
            const zoomFactor = 1.15;
            if (e.deltaY < 0) {
                zoom *= zoomFactor;
            } else {
                zoom /= zoomFactor;
            }
            zoom = Math.max(0.4, Math.min(zoom, 5.0));
        });
        
        // Coordinate transforms
        function toCanvasCoords(x, y) {
            const cx = canvas.width / 2;
            const cy = canvas.height / 2;
            return {
                x: cx + x * scale,
                y: cy - y * scale
            };
        }
        
        function toRealWorldCoords(mx, my) {
            const cx = canvas.width / 2;
            const cy = canvas.height / 2;
            const tx = (mx - panX - cx) / (scale * zoom) + cx;
            const ty = (cy - (my - panY)) / (scale * zoom) + cy;
            // Unmap canvas centering mapping
            return {
                x: (mx - panX - cx) / (scale * zoom),
                y: (cy - (my - panY)) / (scale * zoom)
            };
        }
        
        // Telemetry Hover Check
        function checkHover(mx, my) {
            const realCoords = toRealWorldCoords(mx, my);
            let found = null;
            
            // Check Trucks
            for (const id in trucksData) {
                const t = trucksData[id];
                const dist = Math.sqrt(Math.pow(realCoords.x - t.rx, 2) + Math.pow(realCoords.y - t.ry, 2));
                if (dist < 3.0) {
                    found = { type: 'truck', data: t };
                    break;
                }
            }
            
            // Check Shovels
            if (!found) {
                loadSites.forEach(s => {
                    const dist = Math.sqrt(Math.pow(realCoords.x - s.x, 2) + Math.pow(realCoords.y - s.y, 2));
                    if (dist < 3.5) {
                        found = { type: 'shovel', data: s };
                    }
                });
            }
            
            // Check Dumps
            if (!found) {
                dumpSites.forEach(s => {
                    const dist = Math.sqrt(Math.pow(realCoords.x - s.x, 2) + Math.pow(realCoords.y - s.y, 2));
                    if (dist < 3.5) {
                        found = { type: 'dump', data: s };
                    }
                });
            }
            
            // Render HUD Box
            if (found) {
                hud.style.display = 'block';
                if (found.type === 'truck') {
                    const t = found.data;
                    hud.innerHTML = `
                      <div class="hud-title">📡 Самосвал: ${t.equipment_id}</div>
                      <div class="hud-row"><span class="hud-label">Водитель:</span><span class="hud-value">${t.driver_id}</span></div>
                      <div class="hud-row"><span class="hud-label">Статус:</span><span class="hud-value" style="color: ${getStatusColor(t.status)}">${t.status.toUpperCase()}</span></div>
                      <div class="hud-row"><span class="hud-label">Скорость:</span><span class="hud-value">${t.speed} км/ч</span></div>
                      <div class="hud-row"><span class="hud-label">Риск-фактор:</span><span class="hud-value" style="color: ${getRiskColor(t.risk_level)}">${t.risk_level.toUpperCase()}</span></div>
                      <div class="hud-row"><span class="hud-label">Усталость (PERCLOS):</span><span class="hud-value">${t.fatigue_score}%</span></div>
                      <div class="hud-row"><span class="hud-label">Координаты:</span><span class="hud-value">${t.rx.toFixed(1)}, ${t.ry.toFixed(1)}</span></div>
                    `;
                } else if (found.type === 'shovel') {
                    const s = found.data;
                    hud.innerHTML = `
                      <div class="hud-title">⛏️ Погрузочный узел: ${s.name}</div>
                      <div class="hud-row"><span class="hud-label">Координаты:</span><span class="hud-value">${s.x}, ${s.y}</span></div>
                    `;
                } else if (found.type === 'dump') {
                    const s = found.data;
                    hud.innerHTML = `
                      <div class="hud-title">⛰️ Разгрузочный узел: ${s.name}</div>
                      <div class="hud-row"><span class="hud-label">Координаты:</span><span class="hud-value">${s.x}, ${s.y}</span></div>
                    `;
                }
            } else {
                hud.style.display = 'none';
            }
        }
        
        function getStatusColor(status) {
            if (status === 'stopped') return '#ef4444';
            if (status === 'loading') return '#f59e0b';
            if (status === 'unload') return '#a8a29e';
            return '#10b981';
        }
        
        function getRiskColor(risk) {
            if (risk === 'critical' || risk === 'high') return '#ef4444';
            if (risk === 'medium') return '#f59e0b';
            return '#10b981';
        }
        
        // Graphics Drawing
        function drawGrid(cx, cy) {
            ctx.strokeStyle = 'rgba(31, 41, 55, 0.3)';
            ctx.lineWidth = 1;
            const gridSize = 35;
            
            const startX_grid = Math.floor((-cx - panX) / zoom / gridSize) * gridSize;
            const endX_grid = Math.ceil((canvas.width - cx - panX) / zoom / gridSize) * gridSize;
            
            const startY_grid = Math.floor((-cy - panY) / zoom / gridSize) * gridSize;
            const endY_grid = Math.ceil((canvas.height - cy - panY) / zoom / gridSize) * gridSize;
            
            for (let x = startX_grid; x <= endX_grid; x += gridSize) {
                ctx.beginPath();
                ctx.moveTo(x, startY_grid);
                ctx.lineTo(x, endY_grid);
                ctx.stroke();
            }
            for (let y = startY_grid; y <= endY_grid; y += gridSize) {
                ctx.beginPath();
                ctx.moveTo(startX_grid, y);
                ctx.lineTo(endX_grid, y);
                ctx.stroke();
            }
        }
        
        function drawRoads() {
            ctx.strokeStyle = '#1e293b';
            ctx.lineWidth = 16;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            
            const c_pos = toCanvasCoords(chargingSite.x, chargingSite.y);
            
            // Draw wide base roads
            loadSites.forEach(ls => {
                const ls_pos = toCanvasCoords(ls.x, ls.y);
                ctx.beginPath(); ctx.moveTo(c_pos.x, c_pos.y); ctx.lineTo(ls_pos.x, ls_pos.y); ctx.stroke();
                
                dumpSites.forEach(ds => {
                    const ds_pos = toCanvasCoords(ds.x, ds.y);
                    ctx.beginPath(); ctx.moveTo(ls_pos.x, ls_pos.y); ctx.lineTo(ds_pos.x, ds_pos.y); ctx.stroke();
                });
            });
            
            // Inner dashes
            ctx.strokeStyle = '#334155';
            ctx.lineWidth = 2;
            ctx.setLineDash([8, 8]);
            loadSites.forEach(ls => {
                const ls_pos = toCanvasCoords(ls.x, ls.y);
                ctx.beginPath(); ctx.moveTo(c_pos.x, c_pos.y); ctx.lineTo(ls_pos.x, ls_pos.y); ctx.stroke();
                
                dumpSites.forEach(ds => {
                    const ds_pos = toCanvasCoords(ds.x, ds.y);
                    ctx.beginPath(); ctx.moveTo(ls_pos.x, ls_pos.y); ctx.lineTo(ds_pos.x, ds_pos.y); ctx.stroke();
                });
            });
            ctx.setLineDash([]);
        }
        
        function drawSites() {
            // Charging Site
            const c_pos = toCanvasCoords(chargingSite.x, chargingSite.y);
            ctx.fillStyle = '#1d4ed8';
            ctx.beginPath(); ctx.arc(c_pos.x, c_pos.y, 14, 0, Math.PI * 2); ctx.fill();
            ctx.strokeStyle = '#3b82f6';
            ctx.lineWidth = 2;
            ctx.stroke();
            
            ctx.fillStyle = '#fff';
            ctx.font = '10px Courier';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('⚡', c_pos.x, c_pos.y);
            
            ctx.font = 'bold 9px sans-serif';
            ctx.fillStyle = '#3b82f6';
            ctx.fillText(chargingSite.name, c_pos.x, c_pos.y + 24);
            
            // Shovels (Load Sites)
            loadSites.forEach(ls => {
                const pos = toCanvasCoords(ls.x, ls.y);
                ctx.fillStyle = '#a16207';
                ctx.beginPath(); ctx.arc(pos.x, pos.y, 12, 0, Math.PI * 2); ctx.fill();
                ctx.strokeStyle = '#eab308';
                ctx.lineWidth = 2;
                ctx.stroke();
                
                ctx.fillStyle = '#fff';
                ctx.font = '9px sans-serif';
                ctx.fillText('⛏️', pos.x, pos.y);
                
                ctx.font = 'bold 9px sans-serif';
                ctx.fillStyle = '#eab308';
                ctx.fillText(ls.name, pos.x, pos.y - 20);
            });
            
            // Dumps
            dumpSites.forEach(ds => {
                const pos = toCanvasCoords(ds.x, ds.y);
                ctx.fillStyle = '#44403c';
                ctx.beginPath(); ctx.arc(pos.x, pos.y, 13, 0, Math.PI * 2); ctx.fill();
                ctx.strokeStyle = '#78716c';
                ctx.lineWidth = 2;
                ctx.stroke();
                
                ctx.fillStyle = '#fff';
                ctx.font = '9px sans-serif';
                ctx.fillText('⛰️', pos.x, pos.y);
                
                ctx.font = 'bold 9px sans-serif';
                ctx.fillStyle = '#a8a29e';
                ctx.fillText(ds.name, pos.x, pos.y - 20);
            });
        }
        
        function drawTruckVector(ctx, color, risk, isTargeted) {
            // Draw Target Rings
            if (isTargeted) {
                ctx.strokeStyle = '#0ea5e9';
                ctx.lineWidth = 1.5;
                ctx.beginPath();
                ctx.arc(0, 0, 22, 0, Math.PI * 2);
                ctx.stroke();
                ctx.beginPath();
                ctx.moveTo(-28, 0); ctx.lineTo(-18, 0);
                ctx.moveTo(18, 0); ctx.lineTo(28, 0);
                ctx.moveTo(0, -28); ctx.lineTo(0, -18);
                ctx.moveTo(0, 18); ctx.lineTo(0, 28);
                ctx.stroke();
            }
            
            // Concentric risk ring
            if (risk === 'critical' || risk === 'high') {
                const pulse = Math.abs(Math.sin(Date.now() / 150)) * 6;
                ctx.strokeStyle = 'rgba(239, 68, 68, 0.4)';
                ctx.lineWidth = 2;
                ctx.beginPath();
                ctx.arc(0, 0, 15 + pulse, 0, Math.PI*2);
                ctx.stroke();
            }
            
            // Wheels
            ctx.fillStyle = '#111827';
            ctx.fillRect(-10, -8, 4, 2);
            ctx.fillRect(3, -8, 4, 2);
            ctx.fillRect(-10, 6, 4, 2);
            ctx.fillRect(3, 6, 4, 2);
            
            // Dumper chassis body
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.roundRect(-12, -6, 17, 12, 1.5);
            ctx.fill();
            ctx.strokeStyle = '#ffffff';
            ctx.lineWidth = 1;
            ctx.stroke();
            
            // Driver cabin
            ctx.fillStyle = '#1e293b';
            ctx.fillRect(5, -5, 5, 10);
            
            // Cab window highlight
            ctx.fillStyle = '#38bdf8';
            ctx.fillRect(7, -3, 2, 6);
        }
        
        function draw() {
            // Clear screen
            ctx.fillStyle = '#070a13';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            const cx = canvas.width / 2;
            const cy = canvas.height / 2;
            
            ctx.save();
            ctx.translate(panX, panY);
            ctx.translate(cx, cy);
            ctx.scale(zoom, zoom);
            ctx.translate(-cx, -cy);
            
            // Draw grid & components
            drawGrid(cx, cy);
            drawRoads();
            drawSites();
            
            // Draw Dynamic Trucks
            for (const id in trucksData) {
                const t = trucksData[id];
                const pos = toCanvasCoords(t.rx, t.ry);
                
                ctx.save();
                ctx.translate(pos.x, pos.y);
                ctx.rotate(t.angle);
                
                let color = '#10b981'; // Green
                if (t.risk_level === 'medium') color = '#f59e0b';
                else if (t.risk_level === 'high' || t.risk_level === 'critical') color = '#ef4444';
                
                drawTruckVector(ctx, color, t.risk_level, (t.equipment_id === selectedEquipmentId));
                ctx.restore();
                
                // Add flat text labels
                ctx.fillStyle = '#fff';
                ctx.font = 'bold 9px monospace';
                ctx.textAlign = 'center';
                ctx.fillText(t.equipment_id, pos.x, pos.y - 15);
                
                // Add status flag
                let symbol = "";
                if (t.status === 'stopped') symbol = "🛑";
                else if (t.status === 'loading') symbol = "⏳";
                else if (t.status === 'unload') symbol = "🗑️";
                if (symbol) {
                    ctx.font = '10px Arial';
                    ctx.fillText(symbol, pos.x, pos.y + 20);
                }
            }
            
            ctx.restore();
        }
        
        // 60FPS Render Animate Loop (LERP)
        function animate() {
            for (const id in trucksData) {
                const t = trucksData[id];
                const dx = t.tx - t.rx;
                const dy = t.ty - t.ry;
                
                // Move 8% closer on every frame (smooth slider!)
                t.rx += dx * 0.08;
                t.ry += dy * 0.08;
                
                const dist = Math.sqrt(dx*dx + dy*dy);
                if (dist > 0.03) {
                    // Update angle facing target
                    t.angle = Math.atan2(dy, -dx); // Note negative because canvas Y is inverted
                }
            }
            
            draw();
            requestAnimationFrame(animate);
        }
        requestAnimationFrame(animate);
        
        // HTTP API Calls
        function updateTelemetry() {
            // 1. Fetch simulation status & equipment positions
            fetch('{browser_api_url}/api/simulation/state')
                .then(res => res.json())
                .then(state => {
                    simulationState = state;
                    document.getElementById('txtRunId').innerText = `RUN ID: ${state.run_id || '---'}`;
                    document.getElementById('txtTick').innerText = `ТИК: ${state.current_tick} / ${state.max_ticks}`;
                    document.getElementById('lblSpeed').innerText = `${state.speed_rate.toFixed(1)} tick/s`;
                    document.getElementById('rngSpeed').value = state.speed_rate;
                    document.getElementById('selDispatcher').value = state.dispatcher;
                    
                    // Toggle Start/Pause buttons visually
                    if (state.is_running) {
                        document.getElementById('btnPlay').classList.add('btn-primary');
                        document.getElementById('btnPause').classList.remove('btn-primary');
                    } else {
                        document.getElementById('btnPlay').classList.remove('btn-primary');
                        if (state.current_tick > 0) {
                            document.getElementById('btnPause').classList.add('btn-primary');
                        }
                    }
                    
                    // Parse trucks
                    const listContainer = document.getElementById('equipmentList');
                    let listHtml = "";
                    
                    state.trucks.forEach(t => {
                        const id = t.equipment_id;
                        // Add or update targets
                        if (!trucksData[id]) {
                            trucksData[id] = {
                                equipment_id: id,
                                tx: t.current_position_x,
                                ty: t.current_position_y,
                                rx: t.current_position_x,
                                ry: t.current_position_y,
                                angle: 0,
                                risk_level: t.risk_level,
                                status: t.status,
                                speed: t.speed,
                                driver_id: t.driver_id,
                                fatigue_score: t.fatigue_score
                            };
                        } else {
                            trucksData[id].tx = t.current_position_x;
                            trucksData[id].ty = t.current_position_y;
                            trucksData[id].risk_level = t.risk_level;
                            trucksData[id].status = t.status;
                            trucksData[id].speed = t.speed;
                            trucksData[id].driver_id = t.driver_id;
                            trucksData[id].fatigue_score = t.fatigue_score;
                        }
                        
                        const selectedClass = (id === selectedEquipmentId) ? 'selected' : '';
                        const badgeClass = `status-badge badge-${t.status === 'stopped' ? 'stopped' : t.status === 'loading' ? 'loading' : 'running'}`;
                        
                        listHtml += `
                          <div class="equipment-card ${selectedClass}" onclick="selectTruck('${id}')">
                            <div class="card-header-row">
                              <span>${id} (${t.driver_id})</span>
                              <span class="${badgeClass}">${t.status}</span>
                            </div>
                            <div class="card-body-row">
                              <span>Скорость: ${t.speed} км/ч</span>
                              <span style="color: ${getRiskColor(t.risk_level)}">Риск: ${t.risk_level}</span>
                            </div>
                          </div>
                        `;
                    });
                    listContainer.innerHTML = listHtml;
                })
                .catch(err => console.error("Telemetry fetch error:", err));
                
            // 2. Fetch Alarms Log
            fetch('{browser_api_url}/api/events?limit=4')
                .then(res => res.json())
                .then(events => {
                    const alarmsContainer = document.getElementById('alarmsList');
                    let alarmsHtml = "";
                    events.forEach(e => {
                        if (e.risk_level === 'critical' || e.risk_level === 'high') {
                            alarmsHtml += `
                              <div class="alarm-item">
                                <div class="alarm-item-title">⚠️ ${e.event_type.toUpperCase()} [${e.risk_level}]</div>
                                <div class="alarm-item-desc">${e.description} (${e.equipment_id || 'Mine'})</div>
                              </div>
                            `;
                        }
                    });
                    alarmsContainer.innerHTML = alarmsHtml || '<div style="color: #4b5563; font-size: 11px; text-align: center; padding-top: 10px;">Нет активных тревог</div>';
                })
                .catch(err => console.error("Alarms fetch error:", err));
        }
        
        // Select Equipment Target
        window.selectTruck = function(id) {
            if (selectedEquipmentId === id) {
                selectedEquipmentId = null; // Deselect
            } else {
                selectedEquipmentId = id;
                // Move view to focus on the selected truck
                const t = trucksData[id];
                if (t) {
                    panX = 0;
                    panY = 0;
                    zoom = 1.3;
                    const pos = toCanvasCoords(t.rx, t.ry);
                    const cx = canvas.width / 2;
                    const cy = canvas.height / 2;
                    panX = cx - pos.x;
                    panY = cy - pos.y;
                }
            }
            updateTelemetry();
        };
        
        // Action Event Handlers
        document.getElementById('btnPlay').addEventListener('click', () => {
            const disp = document.getElementById('selDispatcher').value;
            const sp = document.getElementById('rngSpeed').value;
            fetch(`{browser_api_url}/api/simulation/start?dispatcher=${disp}&speed=${sp}`, { method: 'POST' })
                .then(updateTelemetry);
        });
        
        document.getElementById('btnPause').addEventListener('click', () => {
            fetch('{browser_api_url}/api/simulation/stop', { method: 'POST' })
                .then(updateTelemetry);
        });
        
        document.getElementById('btnReset').addEventListener('click', () => {
            fetch('{browser_api_url}/api/simulation/reset', { method: 'POST' })
                .then(() => {
                    trucksData = {};
                    selectedEquipmentId = null;
                    panX = 0;
                    panY = 0;
                    zoom = 1.0;
                    updateTelemetry();
                });
        });
        
        document.getElementById('rngSpeed').addEventListener('input', (e) => {
            const sp = e.target.value;
            document.getElementById('lblSpeed').innerText = `${parseFloat(sp).toFixed(1)} tick/s`;
            fetch(`{browser_api_url}/api/simulation/speed?speed=${sp}`, { method: 'POST' });
        });
        
        // Loop API Polling
        setInterval(updateTelemetry, 500);
        updateTelemetry();
      </script>
    </body>
    </html>
    """
    
    html_code = html_code.replace("{browser_api_url}", browser_api_url)
    st.components.v1.html(html_code, height=720, scrolling=False)
