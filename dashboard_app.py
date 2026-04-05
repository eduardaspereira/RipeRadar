"""
RipeRadar V2 - Web Dashboard (Flask)
====================================
Interface de monitoramento em tempo real para retalhistas.

Funcionalidades:
- Real-time chart de TTW por prateleira
- Heatmap de urgência (green/yellow/red)
- Alertas imediatos
- Relatório PDF diário
- Integração com API de POS/etiquetas eletrónicas

Executar: python dashbboard_app.py
Acessar: http://localhost:5000
"""

from flask import Flask, render_template, jsonify, send_file
from flask_socketio import SocketIO, emit
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from io import BytesIO, StringIO
import matplotlib.pyplot as plt
import seaborn as sns

# ======== FLASK APP SETUP ========

app = Flask(__name__)
app.config['SECRET_KEY'] = 'riperadar-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# ======== DATA SIMULATOR (em produção, vem do RPi via API) ========

class ShelfSimulator:
    """Simula estado de 3 prateleiras com frutas em diferentes estados"""
    
    def __init__(self):
        self.shelves = {
            'shelf_1': {
                'name': 'Prateleira 1 - Maçãs',
                'fruit_type': 'Apple',
                'boxes': [
                    {'id': '1A', 'ttw': 72, 'voc': 45, 'color': 'verde'},
                    {'id': '1B', 'ttw': 48, 'voc': 70, 'color': 'amarelo'},
                    {'id': '1C', 'ttw': 18, 'voc': 150, 'color': 'laranja'},
                ]
            },
            'shelf_2': {
                'name': 'Prateleira 2 - Bananas',
                'fruit_type': 'Banana',
                'boxes': [
                    {'id': '2A', 'ttw': 24, 'voc': 80, 'color': 'amarelo'},
                    {'id': '2B', 'ttw': 6, 'voc': 320, 'color': 'vermelho'},
                    {'id': '2C', 'ttw': 120, 'voc': 20, 'color': 'verde'},
                ]
            },
            'shelf_3': {
                'name': 'Prateleira 3 - Pêras',
                'fruit_type': 'Pear',
                'boxes': [
                    {'id': '3A', 'ttw': 96, 'voc': 30, 'color': 'verde'},
                    {'id': '3B', 'ttw': 60, 'voc': 55, 'color': 'amarelo'},
                    {'id': '3C', 'ttw': 36, 'voc': 120, 'color': 'laranja'},
                ]
            }
        }
    
    def get_shelf_status(self):
        """Retorna status atual de todas as prateleiras"""
        status = []
        
        total_ttw = 0
        total_boxes = 0
        critical_count = 0
        
        for shelf_id, shelf_data in self.shelves.items():
            shelf_status = {
                'id': shelf_id,
                'name': shelf_data['name'],
                'fruit_type': shelf_data['fruit_type'],
                'boxes': shelf_data['boxes'],
                'avg_ttw': np.mean([b['ttw'] for b in shelf_data['boxes']]),
                'max_voc': np.max([b['voc'] for b in shelf_data['boxes']]),
            }
            
            # Determinar urgência
            avg_ttw = shelf_status['avg_ttw']
            if avg_ttw < 6:
                shelf_status['urgency'] = 'CRITICAL'
                critical_count += len(shelf_data['boxes'])
            elif avg_ttw < 24:
                shelf_status['urgency'] = 'HIGH'
                critical_count += sum(1 for b in shelf_data['boxes'] if b['ttw'] < 24)
            elif avg_ttw < 72:
                shelf_status['urgency'] = 'MEDIUM'
            else:
                shelf_status['urgency'] = 'LOW'
            
            status.append(shelf_status)
            total_ttw += shelf_status['avg_ttw']
            total_boxes += len(shelf_data['boxes'])
        
        return {
            'timestamp': datetime.now().isoformat(),
            'shelves': status,
            'global_stats': {
                'avg_ttw_hours': round(total_ttw / len(self.shelves), 1),
                'critical_items': critical_count,
                'total_boxes': total_boxes,
                'waste_reduction_today': np.random.randint(5, 25),  # € simulado
            }
        }
    
    def simulate_degradation(self):
        """Simula degradação ao longo do tempo"""
        for shelf in self.shelves.values():
            for box in shelf['boxes']:
                box['ttw'] = max(0, box['ttw'] - np.random.uniform(0.5, 2))
                box['voc'] = min(500, box['voc'] + np.random.uniform(0, 20))
                
                # Mudar cor conforme TTW
                if box['ttw'] < 6:
                    box['color'] = 'vermelho'
                elif box['ttw'] < 24:
                    box['color'] = 'laranja'
                elif box['ttw'] < 72:
                    box['color'] = 'amarelo'
                else:
                    box['color'] = 'verde'


simulator = ShelfSimulator()

# ======== FLASK ROUTES ========

@app.route('/')
def index():
    """Home page do dashboard"""
    return render_template('dashboard.html')


@app.route('/api/shelf-status')
def api_shelf_status():
    """Endpoint API para status das prateleiras"""
    return jsonify(simulator.get_shelf_status())


@app.route('/api/historical/<shelf_id>')
def api_historical(shelf_id):
    """Endpoint para dados históricos de uma prateleira"""
    # Em produção: carregar de BD
    
    hours = np.arange(0, 24, 0.5)
    ttw_values = 120 - (hours ** 1.1)  # Degradação exponencial
    ttw_values = np.maximum(0, ttw_values)
    
    return jsonify({
        'hours': hours.tolist(),
        'ttw': ttw_values.tolist(),
        'shelf_id': shelf_id,
    })


@app.route('/api/report')
def api_report():
    """Gera relatório diário em PDF"""
    
    # Criar figura
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle('RipeRadar - Relatório Diário', fontsize=16, fontweight='bold')
    
    # Gráfico 1: TTW Distribution
    ax = axes[0, 0]
    shelves_names = [s['name'] for s in simulator.shelves.values()]
    ttw_values = [s['avg_ttw'] for s in simulator.shelves.values()]
    colors_chart = ['green' if t > 72 else 'orange' if t > 24 else 'red' for t in ttw_values]
    ax.bar(range(len(shelves_names)), ttw_values, color=colors_chart)
    ax.set_ylabel('TTW (hours)')
    ax.set_title('Time-to-Waste por Prateleira')
    ax.set_xticks(range(len(shelves_names)))
    ax.set_xticklabels([s.split(' - ')[1] for s in shelves_names], rotation=45)
    ax.axhline(y=24, color='orange', linestyle='--', label='Urgent threshold')
    ax.axhline(y=6, color='red', linestyle='--', label='Critical threshold')
    ax.legend()
    
    # Gráfico 2: VOC Levels
    ax = axes[0, 1]
    voc_values = [s['max_voc'] for s in simulator.shelves.values()]
    ax.bar(range(len(shelves_names)), voc_values, color='purple', alpha=0.7)
    ax.set_ylabel('VOC Index')
    ax.set_title('Níveis Máximos de VOC')
    ax.set_xticks(range(len(shelves_names)))
    ax.set_xticklabels([s.split(' - ')[1] for s in shelves_names], rotation=45)
    
    # Gráfico 3: Desperdício Evitado (simulado)
    ax = axes[1, 0]
    hours_list = np.arange(0, 24, 2)
    waste_saved = np.cumsum(np.random.rand(len(hours_list)) * 5)
    ax.fill_between(hours_list, waste_saved, alpha=0.3, color='green')
    ax.plot(hours_list, waste_saved, marker='o', color='green', linewidth=2)
    ax.set_xlabel('Hora do dia')
    ax.set_ylabel('€ Economizados')
    ax.set_title('Desperdício Evitado (Hoje)')
    ax.grid(alpha=0.3)
    
    # Gráfico 4: Alertas Timeline
    ax = axes[1, 1]
    ax.text(0.5, 0.8, 'Resumo de Alertas', ha='center', fontsize=12, fontweight='bold', transform=ax.transAxes)
    alerts_text = """
    🔴 6 alertas críticos
    🟠 12 alertas de urgência
    🟡 8 alertas de monitoração
    
    Ação recomendada:
    • Reduzir preço prateleira 2 em 50%
    • Reordenar stock prateleira 1
    • Manter monitoração prateleira 3
    """
    ax.text(0.1, 0.5, alerts_text, fontsize=10, transform=ax.transAxes, family='monospace')
    ax.axis('off')
    
    plt.tight_layout()
    
    # Salvar em buffer
    buf = BytesIO()
    plt.savefig(buf, format='pdf')
    buf.seek(0)
    plt.close()
    
    return send_file(
        buf,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'RipeRadar_Report_{datetime.now().strftime("%Y%m%d")}.pdf'
    )


# ======== WEBSOCKET EVENTS (Real-time updates) ========

@socketio.on('connect')
def handle_connect():
    print('✅ Cliente conectado')
    # Enviar status inicial
    status = simulator.get_shelf_status()
    emit('status_update', status)


@socketio.on('request_update')
def handle_update_request():
    """Cliente solicita atualização em tempo real"""
    simulator.simulate_degradation()
    status = simulator.get_shelf_status()
    emit('status_update', status, broadcast=True)


@socketio.on_error_default
def default_error_handler(e):
    print(f'❌ Erro: {str(e)}')


# ======== HELPER: Gerador de HTML template ========

def create_html_template():
    """Cria HTML template do dashboard"""
    return """<!DOCTYPE html>
<html lang="pt-PT">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RipeRadar Dashboard</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            background: white;
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        header h1 {
            color: #667eea;
            font-size: 28px;
        }
        
        header p {
            color: #666;
            font-size: 14px;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            text-align: center;
        }
        
        .stat-card h3 {
            color: #666;
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        
        .stat-card .value {
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        
        .stat-card.critical .value {
            color: #e74c3c;
        }
        
        .stat-card.saved .value {
            color: #27ae60;
        }
        
        .shelves-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .shelf-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        
        .shelf-card h2 {
            color: #333;
            font-size: 16px;
            margin-bottom: 15px;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }
        
        .box-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 5px;
            background: #f8f9fa;
            border-left: 4px solid #ccc;
        }
        
        .box-item.verde {
            border-left-color: #27ae60;
            background: #d5f4e6;
        }
        
        .box-item.amarelo {
            border-left-color: #f39c12;
            background: #fef5e7;
        }
        
        .box-item.laranja {
            border-left-color: #e67e22;
            background: #fdebd0;
        }
        
        .box-item.vermelho {
            border-left-color: #e74c3c;
            background: #fadbd8;
        }
        
        .box-id {
            font-weight: bold;
            color: #333;
            min-width: 50px;
        }
        
        .box-ttw {
            color: #666;
            font-size: 13px;
        }
        
        .box-badge {
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 11px;
            font-weight: bold;
            color: white;
        }
        
        .badge-critical {
            background: #e74c3c;
        }
        
        .badge-urgent {
            background: #e67e22;
        }
        
        .badge-medium {
            background: #f39c12;
        }
        
        .badge-low {
            background: #27ae60;
        }
        
        .actions {
            display: flex;
            gap: 10px;
            margin-top: 20px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }
        
        button {
            flex: 1;
            padding: 10px;
            border: none;
            border-radius: 5px;
            background: #667eea;
            color: white;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: background 0.3s;
        }
        
        button:hover {
            background: #764ba2;
        }
        
        .timestamp {
            font-size: 12px;
            color: #999;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>🍎 RipeRadar Dashboard</h1>
                <p>Smart Shelf Monitoring System</p>
            </div>
            <div id="timestamp"></div>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <h3>Média TTW</h3>
                <div class="value" id="avgTTW">--</div>
            </div>
            <div class="stat-card critical">
                <h3>Itens Críticos</h3>
                <div class="value" id="criticalItems">0</div>
            </div>
            <div class="stat-card saved">
                <h3>Economizado Hoje</h3>
                <div class="value" id="wasteSaved">€--</div>
            </div>
        </div>
        
        <div class="shelves-grid" id="shelvesContainer">
            <!-- Shelves populadas dinamicamente -->
        </div>
        
        <div class="actions">
            <button onclick="downloadReport()">📥 Descarregar Relatório PDF</button>
            <button onclick="refreshData()">🔄 Atualizar Agora</button>
        </div>
    </div>
    
    <script>
        const socket = io();
        
        socket.on('status_update', function(data) {
            updateDashboard(data);
        });
        
        function updateDashboard(data) {
            // Atualizar stats globais
            document.getElementById('avgTTW').textContent = data.global_stats.avg_ttw_hours + 'h';
            document.getElementById('criticalItems').textContent = data.global_stats.critical_items;
            document.getElementById('wasteSaved').textContent = '€' + data.global_stats.waste_reduction_today;
            document.getElementById('timestamp').textContent = new Date(data.timestamp).toLocaleTimeString('pt-PT');
            
            // Renderizar prateleiras
            let html = '';
            for (let shelf of data.shelves) {
                html += `
                    <div class="shelf-card">
                        <h2>${shelf.name}</h2>
                        ${shelf.boxes.map(box => `
                            <div class="box-item ${box.color}">
                                <div>
                                    <div class="box-id">${box.id}</div>
                                    <div class="box-ttw">TTW: ${box.ttw.toFixed(1)}h | VOC: ${box.voc.toFixed(0)}</div>
                                </div>
                                <span class="box-badge ${
                                    box.ttw < 6 ? 'badge-critical' :
                                    box.ttw < 24 ? 'badge-urgent' :
                                    box.ttw < 72 ? 'badge-medium' :
                                    'badge-low'
                                }">
                                    ${
                                        box.ttw < 6 ? 'CRÍTICO' :
                                        box.ttw < 24 ? 'URGENTE' :
                                        box.ttw < 72 ? 'MONITOR' :
                                        'OK'
                                    }
                                </span>
                            </div>
                        `).join('')}
                    </div>
                `;
            }
            document.getElementById('shelvesContainer').innerHTML = html;
        }
        
        function refreshData() {
            socket.emit('request_update');
        }
        
        function downloadReport() {
            window.location.href = '/api/report';
        }
        
        // Auto-refresh cada 5 segundos
        setInterval(() => {
            socket.emit('request_update');
        }, 5000);
        
    </script>
</body>
</html>"""


# ======== INICIALIZAR APP ========

if __name__ == '__main__':
    # Criar diretório de templates
    import os
    os.makedirs('templates', exist_ok=True)
    
    # Escrever HTML template
    with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
        f.write(create_html_template())
    
    print("""
    ╔════════════════════════════════════════════════╗
    ║  🍎 RipeRadar Dashboard - WebUI                ║
    ║  ✅ Dashboard disponível em http://localhost:5000
    ║  ✅ Real-time updates via WebSocket            ║
    ║  ✅ Relatório PDF em /api/report              ║
    ╚════════════════════════════════════════════════╝
    """)
    
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
