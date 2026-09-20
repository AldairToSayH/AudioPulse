# Archivo para llevar a otro proyecto

Lleva **audio_reactividad.json** al otro proyecto. Es el análisis completo de la canción, con instrucciones dentro del propio archivo. Lleva también el **MP3 original** si quieres reproducirlo o incluirlo en el video: el JSON no contiene sonido.

## Mensaje para la otra IA

> Lee audio_reactividad.json con código. Revisa primero instructions_for_ai, signal_definitions, source y sampling. Quiero que animes los objetos que te indicaré usando los datos reales de esta canción: bass_pulse y events.bass_transients para escala, luces e impactos; mid, high y detail para partículas y texturas; energy_smooth para la intensidad del movimiento de cámara. Sincroniza todo en segundos con el audio original. Los arrays de signals comparten índices y time_s; interpola las señales al FPS de mi proyecto y usa los tiempos de events para los cambios discretos. Adapta suggested_mappings al motor que usemos. creative_timeline contiene mi propuesta artística para los primeros 75 segundos, pero sus secciones no están verificadas musicalmente. El análisis cubre toda la canción. No confundas beats estimados con golpes de bombo confirmados.

Después añade al mensaje qué objetos quieres animar y en qué herramienta estás trabajando.

## Qué contiene

- Energía general RMS y versión suavizada para cámara.
- Energía de graves (20–150 Hz), medios (150–2000 Hz) y agudos (2000–16000 Hz, limitado por la frecuencia de muestreo).
- Transitorios de graves con tiempo y fuerza estimada; pulso de ataque inmediato y caída de 100 ms desde cada evento.
- BPM y tiempos de beats estimados.
- Señales a 60 muestras por segundo, independientes del FPS del nuevo proyecto.
- Resumen por intervalos de 10 segundos, reglas de sincronización y ejemplos de mapeo.
- Tu guía opcional de intro/subida/drop a 0/30/45/75 segundos, separada de las mediciones.

Todos los tiempos se refieren al inicio del archivo original, incluido su silencio inicial. Las señales normalizadas van de 0 a 1; las terminadas en `_raw` conservan la amplitud RMS lineal. La normalización se hace por señal usando su percentil 95 y limitando los picos a 1, por lo que no permite comparar sonoridad absoluta entre canciones.

La detección es automática: un transitorio grave puede ser un bombo u otro sonido grave. No se han separado instrumentos ni eliminado voces. Los filtros y ventanas de análisis tienen resolución temporal finita; revisa visualmente y de oído el ajuste final. Cambiar la canción, recortarla o alterar su velocidad requiere ajustar el reloj o volver a analizarla.

## Volver a exportar

Desde la carpeta `musica`, en PowerShell:

```powershell
.\.venv\Scripts\python.exe export_audio.py
```

Para otro audio:

```powershell
.\.venv\Scripts\python.exe export_audio.py "otra_cancion.mp3" --output "exportacion\otra_cancion.json"
```

El exportador es `export_audio.py`; el análisis original de `music.py` se conserva. El JSON se puede usar sin instalar Python en el proyecto receptor si su herramienta tiene otro lector de JSON.
