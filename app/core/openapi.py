"""Personalización de la documentación interactiva (Swagger UI y ReDoc).

Define también ``tags_metadata``, el agrupamiento por dominio que FastAPI usa
para ordenar los endpoints en ``/docs``.
"""

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

# Definición de etiquetas para organizar la documentación
tags_metadata = [
    {"name": "auth", "description": "Registro de roles, logout y el alias obsoleto `POST /auth/login`."},
    {"name": "Autenticación - Clientes", "description": "Portal de clientes: login de administradores de escuela, doctores y representantes."},
    {"name": "Autenticación - Administración", "description": "Portal de administración: login exclusivo de administradores de sistema."},
    {"name": "Administrador de Sistema", "description": "Gestión global del sistema por superusuarios."},
    {"name": "Administrador de Sistema - Feat. Escuela", "description": "Gestión de escuelas por parte del administrador de sistema."},
    {"name": "Administrador de Sistema - Configuración", "description": "Configuración global del sistema (tabla `settings`)."},
    {"name": "Administrador de Escuela", "description": "Gestión específica para los administradores de cada plantel."},
    {"name": "Administrador de Escuela - Estudiantes", "description": "Gestión de estudiantes, representantes y salones de clase."},
    {"name": "Administrador de Escuela - Salones", "description": "Gestión de salones, grados y categorías académicas."},
    {"name": "Administrador de Escuela - Eventos", "description": "Gestión de eventos y comunicados de la escuela."},
    {"name": "Administrador de Escuela - Médico", "description": "Gestión de casos médicos y personal de salud."},
    {"name": "Representante", "description": "Funcionalidades para padres y representantes de alumnos."},
    {"name": "Catálogos Públicos", "description": "Endpoints de consulta general para catálogos del sistema."},
    {"name": "Escuelas Públicas", "description": "Consulta de información pública de escuelas."},
    {"name": "Año Académico", "description": "Gestión de períodos escolares."},
]

def setup_openapi(app: FastAPI):
    """Registra las rutas de documentación interactiva con el tema de Vitaly.

    Sustituye las páginas por defecto de FastAPI (deshabilitadas con
    ``docs_url=None`` y ``redoc_url=None`` en ``app/main.py``) por versiones
    personalizadas servidas desde CDN. Ambas quedan fuera del esquema OpenAPI.

    Args:
        app: Instancia de FastAPI sobre la que se registran ``/docs`` y ``/redoc``.

    Returns:
        None: Registra las rutas como efecto secundario sobre ``app``.
    """
    
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """Sirve la interfaz Swagger UI personalizada.

        Returns:
            HTMLResponse: Página HTML de Swagger UI apuntando a ``/openapi.json``.
        """
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
        """Sirve la documentación de referencia en ReDoc.

        Returns:
            HTMLResponse: Página HTML de ReDoc apuntando a ``/openapi.json``.
        """
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
