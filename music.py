import os

import librosa
import librosa.display
import matplotlib
import numpy as np
matplotlib.use("Agg")
import matplotlib.pyplot as plt


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_FILE = os.path.join(
    BASE_DIR,
    "LATIN MAFIA - vivo si me exiges (Visualizer) - (192 Kbps).mp3",
)

print(f"Buscando archivo: {AUDIO_FILE}")
if not os.path.exists(AUDIO_FILE):
    raise FileNotFoundError(f"No se encontró el archivo MP3: {AUDIO_FILE}")

# 1. Cargar la canción
# sr=None mantiene la frecuencia de muestreo original del archivo
# mono=True reduce a un canal, útil para análisis general

y, sr = librosa.load(AUDIO_FILE, sr=None, mono=True)
print(f"Duración: {len(y) / sr:.2f} s")
print(f"Frecuencia de muestreo: {sr} Hz")

# 2. Extraer RMS (energía/volumen)
rms = librosa.feature.rms(y=y)

# 3. Extraer BPM y beats
tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
tempo_value = float(np.asarray(tempo).mean()) if isinstance(tempo, (list, tuple, np.ndarray)) else float(tempo)

print(f"Tempo estimado: {tempo_value:.2f} BPM")
print(f"Número de beats detectados: {len(beat_frames)}")

# 4. Mostrar algunas mediciones básicas
print(f"RMS promedio: {rms.mean():.6f}")
print(f"RMS máximo: {rms.max():.6f}")

# 5. Gráfico opcional (guardado como imagen)
plt.figure(figsize=(12, 4))
librosa.display.waveshow(y, sr=sr, alpha=0.7)
plt.title("Forma de onda")
plt.tight_layout()
plt.savefig(os.path.join(BASE_DIR, "onda.png"), dpi=150)
plt.close()

plt.figure(figsize=(12, 4))
plt.plot(rms.T, label="RMS")
plt.title("Energía RMS")
plt.xlabel("Tiempo")
plt.ylabel("Amplitud")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(BASE_DIR, "rms.png"), dpi=150)
plt.close()

print("Archivos generados: onda.png y rms.png")