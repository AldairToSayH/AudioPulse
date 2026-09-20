# BeatScope

BeatScope es un proyecto de análisis de audio con Python que permite cargar una canción, extraer características musicales y generar visualizaciones útiles para estudiar su energía y ritmo.

## ¿Para qué sirve?

Este proyecto está pensado para:
- analizar archivos de audio en formato MP3,
- medir la energía general de la canción usando RMS,
- estimar el tempo en BPM,
- detectar beats principales,
- generar gráficos visuales de la onda y la energía sonora.

Es útil para aprendizaje, exploración musical y proyectos básicos de procesamiento de audio.

## Características

- Carga de archivos MP3 desde la carpeta del proyecto.
- Extracción de RMS (Root Mean Square) para analizar volumen y energía.
- Estimación del tempo en BPM usando librosa.
- Detección de beats.
- Generación de imágenes PNG con la forma de onda y la energía RMS.

## Requisitos

Necesitas tener Python instalado y las siguientes librerías:

- librosa
- matplotlib
- numpy
- soundfile

## Instalación

Desde la carpeta del proyecto, ejecuta:

```bash
pip install librosa matplotlib numpy soundfile
```

## Uso

1. Coloca tu archivo MP3 dentro de la carpeta del proyecto.
2. Asegúrate de que el nombre del archivo coincida con el que está definido en el script.
3. Ejecuta:

```bash
python music.py
```

## Resultado esperado

El script genera:
- una salida en consola con duración, frecuencia de muestreo, BPM y RMS,
- dos imágenes:
  - onda.png
  - rms.png

## Estructura del proyecto

```text
musica/
├── README.md
├── music.py
├── LATIN MAFIA - vivo si me exiges (Visualizer) - (192 Kbps).mp3
├── onda.png
├── rms.png
└── .gitignore
```

## Nota

Este proyecto está orientado a análisis musical básico y educación en audio con Python. No pretende reemplazar herramientas profesionales de producción o análisis de audio avanzado.
