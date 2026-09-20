"""Exporta controles de animación portables; no necesita Blender ni un motor gráfico."""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import librosa
import numpy as np
import scipy
import soundfile as sf
from scipy.signal import butter, find_peaks, sosfiltfilt


BASE = Path(__file__).resolve().parent
HOP = 256
WINDOW = 2048
RATE = 60


def normalize(values):
    reference = float(np.percentile(values, 95))
    if reference < 1e-8:
        return np.zeros_like(values), reference
    return np.clip(values / reference, 0, 1), reference


def envelope(values, dt, attack, release):
    result = np.empty_like(values)
    previous = 0.0
    for i, value in enumerate(values):
        tau = attack if value > previous else release
        alpha = 1.0 if tau == 0 else 1 - np.exp(-dt / tau)
        previous += alpha * (value - previous)
        result[i] = previous
    return result


def rms(values):
    return librosa.feature.rms(y=values, frame_length=WINDOW, hop_length=HOP,
                               center=True, pad_mode="constant")[0]


def bass_events(values, times, duration):
    # Positive changes in bass RMS: candidates, not source-separated kick drums.
    novelty = np.maximum(np.diff(values, prepend=values[0]), 0)
    reference = float(np.percentile(novelty, 99))
    if reference < 1e-8:
        return [], novelty
    dt = times[1] - times[0]
    peaks, _ = find_peaks(novelty, height=reference * 0.15,
                         prominence=reference * 0.12,
                         distance=max(1, round(0.12 / dt)))
    floor = float(np.percentile(values, 95)) * 0.08
    events = [{"time_s": round(float(times[i]), 6),
               "strength": round(float(np.clip(novelty[i] / reference, 0, 1)), 5)}
              for i in peaks if times[i] < duration and values[i] > floor]
    return events, novelty


def pulse_at(times, events):
    pulse = np.zeros_like(times)
    for event in events:
        delta = times - event["time_s"]
        active = (delta >= 0) & (delta <= 1.0)
        pulse[active] = np.maximum(pulse[active],
                                  event["strength"] * np.exp(-delta[active] / 0.10))
    return pulse


def export(source, destination):
    info = sf.info(str(source))
    print("Leyendo audio...", flush=True)
    y, sr = librosa.load(str(source), sr=None, mono=True)
    duration = len(y) / sr
    if duration < 1:
        raise ValueError("Se requiere al menos un segundo de audio.")
    times = librosa.frames_to_time(np.arange(len(rms(y))), sr=sr, hop_length=HOP)
    measured = {"rms": rms(y)}
    bands = {"bass": [20, 150], "mid": [150, 2000], "high": [2000, min(16000, sr * 0.49)]}
    if bands["high"][1] <= bands["high"][0]:
        raise ValueError("Frecuencia de muestreo insuficiente para analizar agudos.")
    for name, (low, high) in bands.items():
        print(f"Analizando {name}: {low}-{high} Hz...", flush=True)
        filtered = sosfiltfilt(butter(4, [low, high], btype="bandpass", fs=sr, output="sos"), y)
        measured[name] = rms(filtered)
    normalized = {}
    references = {}
    for name, values in measured.items():
        normalized[name], references[name] = normalize(values)
    dt = HOP / sr
    normalized["energy_smooth"] = envelope(normalized["rms"], dt, 0.10, 0.35)
    events, _ = bass_events(measured["bass"], times, duration)
    print("Estimando tempo y beats...", flush=True)
    onset = librosa.onset.onset_strength(y=y, sr=sr, hop_length=HOP)
    tempo, beat_frames = librosa.beat.beat_track(onset_envelope=onset, sr=sr, hop_length=HOP)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr, hop_length=HOP)
    tempo = float(np.asarray(tempo).reshape(-1)[0])
    grid = np.arange(int(np.ceil(duration * RATE)), dtype=float) / RATE
    grid = np.append(grid[grid < duration], duration)
    values = {name: np.interp(grid, times, data) for name, data in normalized.items()}
    values["bass_pulse"] = pulse_at(grid, events)
    values["detail"] = envelope((values["mid"] + values["high"]) / 2, 1 / RATE, 0.03, 0.12)
    signals = {"time_s": np.round(grid, 6).tolist()}
    signals.update({name: np.round(data, 5).tolist() for name, data in values.items()})
    for name, data in measured.items():
        signals[name + "_raw"] = np.round(np.interp(grid, times, data), 7).tolist()

    sections = []
    for start in np.arange(0, duration, 10):
        end = min(start + 10, duration)
        mask = (grid >= start) & (grid < end)
        sections.append({"start_s": round(float(start), 6), "end_s": round(float(end), 6),
                         "mean_energy": round(float(values["rms"][mask].mean()), 4),
                         "mean_bass": round(float(values["bass"][mask].mean()), 4),
                         "bass_transient_count": int(sum(start <= e["time_s"] < end for e in events))})
    definitions = {
        "time_s": "Segundos desde el inicio del MP3 decodificado; sin recortar el silencio inicial.",
        "rms": "RMS general normalizado 0..1; proxy de amplitud, no LUFS ni volumen percibido.",
        "bass": "RMS de 20..150 Hz normalizado 0..1.",
        "mid": "RMS de 150..2000 Hz normalizado 0..1.",
        "high": "RMS de 2000..16000 Hz (o límite indicado en bands_hz) normalizado 0..1.",
        "energy_smooth": "RMS normalizado con ataque 100 ms y liberación 350 ms, para cámara.",
        "bass_pulse": "Máximo de los pulsos de transitorios graves: strength*exp(-(t-time_s)/0.10) para t>=time_s; se truncan a 1 s.",
        "detail": "Promedio de mid y high, suavizado con ataque 30 ms/liberación 120 ms.",
        "rms_raw": "RMS del audio mono, amplitud lineal de muestras decodificadas.",
        "bass_raw": "RMS lineal tras filtro de graves.",
        "mid_raw": "RMS lineal tras filtro de medios.",
        "high_raw": "RMS lineal tras filtro de agudos.",
    }
    data = {
        "schema": "portable-audio-reactivity", "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "description": "Análisis de audio para que otra IA anime objetos, luces, partículas y cámara en cualquier proyecto.",
        "source": {"file_name": source.name, "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                   "duration_s": round(duration, 6), "sample_rate_hz": sr,
                   "original_channels": info.channels, "analysis_mix": "mono promedio de canales",
                   "audio_embedded": False, "vocals_removed": False,
                   "instrumental_verified": False},
        "analysis": {"libraries": {"librosa": librosa.__version__, "numpy": np.__version__, "scipy": scipy.__version__},
                     "hop_samples": HOP, "hop_s": HOP / sr, "rms_window_samples": WINDOW,
                     "rms_window_s": WINDOW / sr, "centered_windows": True,
                     "bands_hz": bands, "band_filter": "Butterworth orden 4, sosfiltfilt bidireccional; offline, fase cero",
                     "normalization": "Cada canal / su percentil 95 de toda la canción, limitado a 0..1. Canales casi silenciosos -> 0.",
                     "normalization_p95": references,
                     "timing_note": "Tiempos estimados. Ventanas centradas y filtros pueden extender transitorios alrededor del ataque; revisar sincronía de oído si se necesita precisión de fotograma.",
                     "bass_detection": "Picos de incremento positivo de RMS grave; separación mínima 120 ms. No distingue con certeza bombo, bajo, voces u otros sonidos graves."},
        "rhythm": {"estimated_bpm": round(tempo, 4), "verified": False,
                   "beat_times_s": [round(float(t), 6) for t in beat_times if t < duration],
                   "note": "Rejilla rítmica estimada; los beats no son necesariamente golpes de bombo. Puede haber ambigüedad de mitad/doble tempo."},
        "events": {"bass_transients": events},
        "sampling": {"nominal_rate_hz": RATE, "sample_count": len(grid),
                     "layout": "Arrays paralelos: el índice i de cada señal corresponde a time_s[i].",
                     "interpolation": "Lineal para señales continuas. Para impactos exactos, usar events y reconstruir el pulso desde su tiempo.",
                     "last_sample": "Incluye el final exacto; el último intervalo puede ser menor que 1/60 s.",
                     "out_of_range": "Para t<0 o t>duration_s usar señales 0; detener eventos al acabar el audio."},
        "signal_definitions": definitions,
        "creative_timeline": {"status": "user_requested_unverified", "optional": True,
                              "note": "Guía creativa del usuario, no estructura detectada. No asumir que la canción tiene un drop a los 45 s.",
                              "segments": [
                                  {"start_s": 0, "end_s": 30, "label": "intro_breakdown", "visual_energy_from": 0.2, "visual_energy_to": 0.2, "direction": "Movimiento lento, colores fríos, cámara mínima."},
                                  {"start_s": 30, "end_s": 45, "label": "build_up", "visual_energy_from": 0.5, "visual_energy_to": 0.8, "direction": "Zoom-in progresivo, distorsión creciente, colores más cálidos."},
                                  {"start_s": 45, "end_s": 75, "label": "drop", "visual_energy_from": 1.0, "visual_energy_to": 1.0, "direction": "Movimiento intenso, agitación de cámara y cambios de color en transitorios graves."}],
                              "after_75_s": "Sin dirección artística impuesta; seguir las señales medidas o definir nuevas secciones."},
        "suggested_mappings": {
            "status": "Ejemplos editables, no keyframes definitivos ni unidades propias de un motor.",
            "object_scale_multiplier": "1 + 0.18 * bass_pulse",
            "emission_multiplier": "1 + 2.5 * bass_pulse",
            "particle_speed_multiplier": "0.3 + 2.7 * detail",
            "texture_complexity_0_1": "detail",
            "camera_motion_amount_0_1": "energy_smooth",
            "camera_motion_usage": "Multiplicar por la amplitud de pan/rotación deseada; integrar velocidades usando dt en segundos. No asignar energía directamente a posición si se busca una trayectoria fluida.",
            "color_changes": "Disparar al cruzar cada bass_transient.time_s (prev_t < event_t <= t), incluso si salta un fotograma. Elegir paleta en el proyecto receptor.",
            "frame_conversion": "frame = start_frame + round(time_s * project_fps). El muestreo de 60 Hz no obliga a renderizar a 60 FPS."
        },
        "overview_10s": sections,
        "instructions_for_ai": [
            "Leer primero los metadatos y signal_definitions. Procesar los arrays con código; no es necesario meter todos los números en el contexto de un chat.",
            "Usar el audio original con el mismo comienzo y sin cambiar velocidad. Si se usa un recorte: source_time_s = project_time_s + trim_start_s.",
            "Interpolar los arrays en el tiempo del audio. Aplicar events para impactos y cambios discretos; restablecer el cursor de eventos al retroceder o repetir el audio.",
            "Usar graves para pulsos y luces; medios/agudos para partículas/texturas; energy_smooth para amplitud del movimiento de cámara.",
            "Adaptar suggested_mappings a los objetos que solicite el usuario. La guía creative_timeline es opcional y no es un resultado del análisis.",
            "Este JSON no contiene la canción ni una escena o video. Los eventos y el BPM son estimaciones automáticas, no etiquetas musicales verificadas."
        ],
        "signals": signals,
    }
    validate(data)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Readable metadata, compact numeric arrays (one signal per line).
    metadata = {key: value for key, value in data.items() if key != "signals"}
    header = json.dumps(metadata, ensure_ascii=False, indent=2, allow_nan=False)
    rows = ["    " + json.dumps(name) + ": " + json.dumps(array, separators=(",", ":"), allow_nan=False)
            for name, array in signals.items()]
    destination.write_text(header[:-2] + ',\n  "signals": {\n' + ",\n".join(rows) + "\n  }\n}\n", encoding="utf-8")
    # Reopen the actual artifact so truncated or invalid output cannot pass silently.
    validate(json.loads(destination.read_text(encoding="utf-8")))
    print(json.dumps({"output": str(destination), "duration_s": duration,
                      "estimated_bpm": tempo, "samples": len(grid), "beats": len(data["rhythm"]["beat_times_s"]),
                      "bass_transients": len(events), "bytes": destination.stat().st_size}, indent=2), flush=True)


def validate(data):
    signals = data["signals"]
    t = np.asarray(signals["time_s"])
    duration = data["source"]["duration_s"]
    assert len(t) == data["sampling"]["sample_count"]
    assert t[0] == 0 and abs(t[-1] - duration) < 1e-5
    assert np.all(np.diff(t) > 0)
    for name, values in signals.items():
        a = np.asarray(values)
        assert len(a) == len(t) and np.isfinite(a).all(), name
        if name != "time_s" and not name.endswith("_raw"):
            assert np.all((a >= 0) & (a <= 1)), name
    events = data["events"]["bass_transients"]
    assert all(0 <= e["time_s"] < duration and 0 <= e["strength"] <= 1 for e in events)
    assert all(a["time_s"] < b["time_s"] for a, b in zip(events, events[1:]))
    assert all(0 <= t < duration for t in data["rhythm"]["beat_times_s"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audio", nargs="?", type=Path)
    parser.add_argument("--output", type=Path, default=BASE / "exportacion" / "audio_reactividad.json")
    args = parser.parse_args()
    if args.audio is None:
        candidates = list(BASE.glob("*.mp3"))
        if len(candidates) != 1:
            parser.error("Indica el archivo de audio: python export_audio.py cancion.mp3")
        args.audio = candidates[0]
    export(args.audio.resolve(), args.output.resolve())
