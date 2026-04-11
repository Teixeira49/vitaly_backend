
ROOT_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vitaly Backend API - Home</title>
    <link rel="icon" type="image/png" href="/static/logo.png">
    <link href="https://fonts.googleapis.com/css2?family=Comfortaa:wght@400;700&family=Varela+Round&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary-deep: #1D1A56;
            --secondary-care: #99C5EA;
            --sun-energy: #FDD22F;
            --white-soft: #F8F9EF;
            --text-main: #1D1A56;
        }

        body {
            margin: 0;
            padding: 0;
            font-family: 'Varela Round', sans-serif;
            background-color: var(--white-soft);
            color: var(--text-main);
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            background-image: radial-gradient(circle at 10% 20%, rgba(153, 197, 234, 0.1) 0%, transparent 40%),
                              radial-gradient(circle at 90% 80%, rgba(253, 210, 47, 0.1) 0%, transparent 40%);
        }

        .container {
            background: white;
            padding: 3rem;
            border-radius: 30px;
            box-shadow: 0 20px 40px rgba(29, 26, 86, 0.08);
            text-align: center;
            max-width: 600px;
            width: 90%;
            border: 1px solid rgba(29, 26, 86, 0.05);
        }

        .logo-placeholder {
            font-family: 'Comfortaa', cursive;
            font-size: 2.5rem;
            font-weight: 700;
            color: var(--primary-deep);
            margin-bottom: 0.5rem;
            letter-spacing: -1px;
        }

        .logo-placeholder span {
            color: var(--secondary-care);
        }

        h1 {
            font-family: 'Comfortaa', cursive;
            font-size: 1.5rem;
            margin-bottom: 1rem;
            color: var(--primary-deep);
        }

        p {
            color: #666;
            margin-bottom: 2rem;
            line-height: 1.6;
        }

        .button-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1rem;
        }

        .full-width {
            grid-column: span 2;
        }

        .btn {
            padding: 14px 24px;
            border-radius: 20px;
            text-decoration: none;
            font-weight: 600;
            font-size: 0.95rem;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            cursor: pointer;
            border: none;
        }

        .btn:hover {
            transform: translateY(-3px);
            box-shadow: 0 8px 15px rgba(29, 26, 86, 0.15);
        }

        .btn:active {
            transform: translateY(0);
        }

        .btn-primary {
            background-color: var(--primary-deep);
            color: white;
        }

        .btn-secondary {
            background-color: var(--secondary-care);
            color: var(--primary-deep);
        }

        .btn-warning {
            background-color: var(--sun-energy);
            color: var(--primary-deep);
        }

        .btn-outline {
            background-color: transparent;
            border: 2px solid var(--secondary-care);
            color: var(--primary-deep);
        }

        .footer {
            margin-top: 2rem;
            font-size: 0.8rem;
            color: #aaa;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            background: #e8f5e9;
            color: #2e7d32;
            padding: 6px 12px;
            border-radius: 50px;
            font-size: 0.8rem;
            font-weight: 700;
            margin-bottom: 2rem;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            background: #4caf50;
            border-radius: 50%;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.4; }
            100% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="status-badge">
            <div class="status-dot"></div>
            SISTEMA ACTIVO
        </div>
        <div class="logo-placeholder">vitaly<span>.</span></div>
        <h1>Portal de Backend API</h1>
        <p>Bienvenido al núcleo digital de Vitaly. Aquí puedes gestionar la documentación técnica y acceder a las plataformas de servicio.</p>
        
        <div class="button-grid">
            <a href="/health-visual" class="btn btn-warning full-width">
                ⚡ Health Status Dashboard
            </a>
            <a href="/docs" class="btn btn-primary">
                📘 Swagger UI
            </a>
            <a href="/redoc" class="btn btn-primary">
                📖 ReDoc
            </a>
            <a href="https://vitaly-care-for-families.lovable.app" target="_blank" class="btn btn-secondary">
                👨‍👩‍👧 User Dashboard
            </a>
            <a href="https://vitaly-admin-dashboard.lovable.app" target="_blank" class="btn btn-secondary">
                🛡️ Admin Dashboard
            </a>
        </div>

        <div class="footer">
            Vitaly API v0.4.0 &bull; 2024 &bull; Designed for Health
        </div>
    </div>
</body>
</html>
"""
