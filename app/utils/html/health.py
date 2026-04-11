
HEALTH_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vitaly - System Health</title>
    <link rel="icon" type="image/png" href="/static/logo.png">
    <link href="https://fonts.googleapis.com/css2?family=Comfortaa:wght@400;700&family=Varela+Round&display=swap" rel="stylesheet">
    <style>
        :root {{
            --primary-deep: #1D1A56;
            --secondary-care: #99C5EA;
            --sun-energy: #FDD22F;
            --white-soft: #F8F9EF;
            --success: #4CAF50;
            --error: #FF5252;
        }}

        body {{
            margin: 0;
            font-family: 'Varela Round', sans-serif;
            background-color: var(--white-soft);
            color: var(--primary-deep);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}

        .health-card {{
            background: white;
            padding: 2.5rem;
            border-radius: 30px;
            box-shadow: 0 15px 35px rgba(29, 26, 86, 0.1);
            width: 90%;
            max-width: 500px;
            text-align: center;
        }}

        .header {{
            margin-bottom: 2rem;
        }}

        .title {{
            font-family: 'Comfortaa', cursive;
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--primary-deep);
            margin-bottom: 0.5rem;
            letter-spacing: -1px;
        }}

        .title span {{
            color: var(--secondary-care);
        }}

        .metric-group {{
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            margin-bottom: 2rem;
        }}

        .metric-item {{
            background: var(--white-soft);
            padding: 1rem 1.5rem;
            border-radius: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 1px solid rgba(29, 26, 86, 0.05);
        }}

        .label {{
            font-weight: 600;
            color: #666;
            font-size: 0.9rem;
        }}

        .value {{
            font-weight: 700;
            font-size: 1rem;
        }}

        .status-pill {{
            padding: 4px 12px;
            border-radius: 50px;
            font-size: 0.75rem;
            text-transform: uppercase;
            font-weight: 800;
        }}

        .online {{ background: #e8f5e9; color: var(--success); }}
        .offline {{ background: #ffebee; color: var(--error); }}
        .connected {{ background: #e3f2fd; color: #1976d2; }}

        .btn-back {{
            display: inline-block;
            margin-top: 1rem;
            color: var(--secondary-care);
            text-decoration: none;
            font-weight: 700;
            font-size: 0.9rem;
            transition: all 0.2s;
        }}

        .btn-back:hover {{
            color: var(--primary-deep);
            transform: translateX(-5px);
        }}

        .pulse-icon {{
            font-size: 3rem;
            margin-bottom: 1rem;
            display: block;
        }}
    </style>
</head>
<body>
    <div class="health-card">
        <div class="header">
            <span class="pulse-icon">🩺</span>
            <div class="title">vitaly<span>.</span></div>
            <div style="color: #666; font-weight: 700; margin-bottom: 1rem;">Health Status Dashboard</div>
            <div style="color: #888; font-size: 0.8rem;">Backend API v{version}</div>
        </div>

        <div class="metric-group">
            <div class="metric-item">
                <span class="label">API Status</span>
                <span class="value status-pill {status_class}">{status}</span>
            </div>
            <div class="metric-item">
                <span class="label">Base de Datos</span>
                <span class="value status-pill connected">{database}</span>
            </div>
            <div class="metric-item">
                <span class="label">Ubicación</span>
                <span class="value" style="font-size: 0.8rem; color: #888;">Supabase Cloud</span>
            </div>
        </div>

        <a href="/" class="btn-back">← Volver al Portal</a>
    </div>
</body>
</html>
"""
