# Syntetické trailerové SFX (deterministické, seed 7): riser do dropu, obrácený whoosh, sub-basový úder.
# python scripts/synth_sfx.py <ffmpeg.exe>   → public/audio/sfx/{riser-synth,whoosh-reverse,sub-drop}.wav
import subprocess, sys, wave, numpy as np
from pathlib import Path
SR = 44100; OUT = Path(__file__).resolve().parent.parent / 'public/audio/sfx'; FF = sys.argv[1]
rng = np.random.default_rng(7)

def save(name, x):
    x = x / max(1e-9, np.abs(x).max()) * 0.89  # -1 dBFS
    st = np.stack([x, x], 1) if x.ndim == 1 else x
    with wave.open(str(OUT / name), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())
    print('ok', name, f'{len(st) / SR:.2f}s')

def lowpass(x, fc):  # jednopólový LP s časově proměnnou frekvencí
    y = np.zeros_like(x); acc = 0.0
    a = 1 - np.exp(-2 * np.pi * fc / SR)
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc); y[i] = acc
    return y

# 1) riser 4.4 s: šum se stoupajícím filtrem + exponenciální sweep tónu + zrychlující tremolo
T = 4.4; t = np.arange(int(T * SR)) / SR; p = t / T
noise = rng.standard_normal(len(t))
fc = 300 * (40 ** p)                               # 300 Hz → 12 kHz
n = lowpass(noise, fc) - lowpass(noise, fc * 0.25)  # pásmová propust
f = 90 * (8 ** p); tone = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.5 * np.sin(4 * np.pi * np.cumsum(f) / SR)
trem = 0.75 + 0.25 * np.sin(2 * np.pi * np.cumsum(3 + 15 * p ** 2) / SR)
env = (10 ** (-38 * (1 - p) ** 1.6 / 20)) * trem
riser = (0.8 * n / np.abs(n).max() + 0.45 * tone) * env
riser[-int(0.015 * SR):] *= np.linspace(1, 0, int(0.015 * SR))
riser[:int(0.3 * SR)] *= np.linspace(0, 1, int(0.3 * SR))  # bez cvaknutí na startu filtru
save('riser-synth.wav', riser)

# 2) obrácený whoosh (nasátí před dropem) z Mixkit air-woosh-deep
raw = subprocess.run([FF, '-v', 'quiet', '-i', str(OUT / 'air-woosh-deep.mp3'), '-ac', '1', '-ar', str(SR), '-f', 'wav', '-'], capture_output=True).stdout[44:]
w = np.frombuffer(raw, np.int16).astype(np.float32)[::-1].copy()
w[-int(0.01 * SR):] *= np.linspace(1, 0, int(0.01 * SR))
save('whoosh-reverse.wav', w)

# 3) sub-basový úder 2.2 s: 55 → 32 Hz, rychlý náběh, exponenciální doznění, jemné saturační zkreslení
T = 2.2; t = np.arange(int(T * SR)) / SR
f = 32 + 23 * np.exp(-t * 6)
sub = np.tanh(1.6 * np.sin(2 * np.pi * np.cumsum(f) / SR)) * np.exp(-t * 2.2) * np.minimum(1, t / 0.004)
save('sub-drop.wav', sub)
