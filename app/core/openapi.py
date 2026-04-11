from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Definición de etiquetas para organizar la documentación
tags_metadata = [
    {"name": "auth", "description": "Operaciones de autenticación, login y registro de diferentes roles."},
    {"name": "Administrador de Sistema", "description": "Gestión global del sistema por superusuarios."},
    {"name": "Administrador de Escuela", "description": "Gestión específica para los administradores de cada plantel."},
    {"name": "Representante", "description": "Funcionalidades para padres y representantes de alumnos."},
    {"name": "Catálogos Públicos", "description": "Endpoints de consulta general para catálogos del sistema."},
    {"name": "Escuelas Públicas", "description": "Consulta de información pública de escuelas."},
    {"name": "Año Académico", "description": "Gestión de períodos escolares."},
]

def setup_openapi(app: FastAPI):
    """Configura los endpoints personalizados para la documentación OpenAPI/Swagger/ReDoc."""
    
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
            <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
            <link rel="stylesheet" type="text/css" href="https://cdn.jsdelivr.net/npm/swagger-ui-themes@3.0.1/themes/3.x/theme-obsidian.css">
            <link rel="icon" type="image/png" href="/static/logo.png">
            <link rel="shortcut icon" href="/static/logo.png">
            <link rel="apple-touch-icon" href="/static/logo.png">
            <title>{app.title} - Swagger UI</title>
            </head>
            <body>
            <div id="swagger-ui"></div>
            <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
            <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-standalone-preset.js"></script>
            <script>
            window.onload = () => {{
                window.ui = SwaggerUIBundle({{
                    url: '{app.openapi_url or "/openapi.json"}',
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIBundle.SwaggerUIStandalonePreset
                    ],
                    layout: "BaseLayout",
                    deepLinking: true,
                    showExtensions: true,
                    showCommonExtensions: true
                }})
            }}
            </script>
            </body>
            </html>
            """
        )

    @app.get("/redoc", include_in_schema=False)
    async def custom_redoc_html():
        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
            <title>{app.title} - ReDoc</title>
            <meta charset="utf-8"/>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="icon" type="image/png" href="/static/logo.png">
            <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700" rel="stylesheet">
            <style>
              body {{ margin: 0; padding: 0; }}
            </style>
            </head>
            <body>
            <div id="redoc-container"></div>
            <script src="https://cdn.redoc.ly/redoc/latest/bundles/redoc.standalone.js"></script>
            <script>
                Redoc.init(
                    '{app.openapi_url or "/openapi.json"}',
                    {{
                        expandResponses: '200,201',
                        requiredPropsFirst: true,
                        hideHostname: false,
                        sortPropsAlphabetically: true,
                        downloadDefinition: true,
                        theme: {{
                            colors: {{
                                primary: {{
                                    main: '#32329f'
                                }}
                            }}
                        }}
                    }},
                    document.getElementById('redoc-container')
                );
            </script>
            </body>
            </html>
            """
        )
