# Real Estate Explorer

Este proyecto es una aplicación web hecha con Dash para explorar datos del mercado inmobiliario (en concreto de Texas)
Permite visualizar zonas en un mapa, filtrar viviendas, estudiar precios y obtener estimaciones usando modelos entrenados
El objetivo es ofrecer una herramienta sencilla para analizar datos reales del mercado

## Objetivos del proyecto

- Visualizar datos inmobiliarios en mapas y gráficos
- Filtrar viviendas por precio, ZIP y características básicas
- Estimar precios y tiempo esperado en el mercado
- Consultar comparables y métricas de cada zona

## Contenido del proyecto

├── app.py                    # Aplicación principal con la interfaz y callbacks de Dash
├── requirements.txt          # Lista de librerías necesarias
├── Procfile                  # Comando de arranque para despliegue
├── render.yaml               # Configuración para desplegar la app en Render
├── data/
│   └── sold_data.csv         # Datos originales de viviendas vendidas sacadas de Redfin
├── assets/
│   ├── style.css             # Estilos personalizados de toda la aplicación
│   └── Fotos/                # Imágenes usadas en el hero y elementos visuales
│       ├── hero1.jpg
│       ├── hero2.jpg
│       ├── hero3.jpg
│       └── ...               # Resto de imágenes del proyecto
└── src/
    ├── etl.py                # Limpieza y preparación de datos
    ├── graphics.py           # Generación de mapas y gráficos
    ├── model.py              # Carga de modelos y generación de predicciones
    └── train_models.py       # Entrenamiento de modelos de precio y tiempo de mercado
