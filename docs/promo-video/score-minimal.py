"""Soundtrack for the minimal cut (minimal.html).

Usage: python3 score-minimal.py <timeline.json> <out.wav>

Restrained on purpose: a soft pad, one piano-like note on every cut, a light
pulse only while the product is on screen, and a low thump under each closing
word. Every note and effect is placed from the timeline's event times.
"""
import json
import sys
import wave

import numpy as np

from synth import SR, bell, highpass, kick, lowpass, midi, noise, pad_chord, place, place_stereo, tt

timeline = json.load(open(sys.argv[1]))
BEAT = 60 / timeline["bpm"]
BAR = BEAT * 4
SHOTS = timeline["shots"]
DUR = timeline["duration"] + 1.5
N = int(DUR * SR)
music = np.zeros((N, 2))
sfx = np.zeros((N, 2))


def piano(note, sec=2.5, gain=1.0):
    """A soft, slightly detuned struck tone: fast attack, long two-stage decay."""
    x = tt(sec)
    f = midi(note)
    partials = [(1, 1.0, 1.6), (2, 0.42, 2.6), (3, 0.18, 3.8), (4, 0.09, 5.0), (5, 0.05, 6.5)]
    sig = sum(a * (np.sin(2 * np.pi * f * k * x) + 0.6 * np.sin(2 * np.pi * f * k * 1.0015 * x)) * np.exp(-x * d)
              for k, a, d in partials)
    hammer = lowpass(highpass(noise(sec), 1500), 6000) * np.exp(-x * 160) * 0.05
    return (sig / 1.6 + hammer) * np.minimum(1, x / 0.004) * gain


def sub(note, sec=0.9):
    x = tt(sec)
    return np.sin(2 * np.pi * midi(note) * x) * np.exp(-x * 3.2) * np.minimum(1, x / 0.01)


# ---------- harmony: one chord per bar ----------
CHORDS = {
    "C": ([48, 55, 60, 64, 67, 71], 36),   # Cmaj7
    "Am": ([45, 52, 57, 60, 64, 67], 33),  # Am7
    "F": ([41, 48, 57, 60, 64, 69], 29),   # Fmaj7
    "G": ([43, 50, 55, 59, 62, 69], 31),   # G6/9
}
PLAN = ["C", "C", "Am", "Am", "F", "F", "G", "C", "Am", "F", "G", "G", "C", "C", "C", "C"]
bars = int(np.ceil(timeline["duration"] / BAR))
for b in range(bars):
    name = PLAN[min(b, len(PLAN) - 1)]
    notes, root = CHORDS[name]
    t0 = b * BAR
    last = b == bars - 1
    place_stereo(music, t0, pad_chord(notes, BAR + (1.5 if last else 0.4), 900), 0.2)
    place(music, t0, sub(root + 12, BAR * 0.9), 0.22)

# light pulse while the product is on screen
pulse_from, pulse_to = SHOTS["D"][0], SHOTS["F"][1]
t = pulse_from
while t < pulse_to - 1e-6:
    k = round((t - pulse_from) / BEAT)
    if k % 2 == 0:
        place(music, t, kick(0.8), 0.32)
    tick = highpass(highpass(noise(0.04), 8000), 8000) * np.exp(-tt(0.04) * 90)
    place(music, t + BEAT / 2, tick, 0.05, 0.3)
    t += BEAT

# ---------- a piano note on every cut, then the closing chord ----------
MELODY = {"A": 76, "B": 79, "C": 84, "D": 83, "E": 81, "F": 79, "G": 84, "H": 72}
for e in timeline["events"]:
    t, kind = e["t"], e["type"]
    if kind in ("start", "cut"):
        place(sfx, t, piano(MELODY[e["shot"]], 2.6), 0.22, -0.2 + 0.4 * (e["i"] % 2))
        if kind == "cut":
            air = lowpass(highpass(noise(0.5), 1500), 5000) * np.sin(np.pi * tt(0.5) / 0.5) ** 2
            place(sfx, t - 0.25, air, 0.035)
    elif kind == "word":
        place(sfx, t, sub(36, 1.2), 0.55)
        place(sfx, t, piano([84, 86, 88][e["i"]], 2.0), 0.2)
    elif kind == "bubble":
        place(sfx, t, bell([72, 76, 79][e["i"]], 1.2), 0.1, [-0.3, 0.3, 0][e["i"]])
    elif kind == "final":
        for i, n in enumerate([60, 64, 67, 71, 74, 79]):
            place(sfx, t + i * 0.09, piano(n, 3.5), 0.13, -0.5 + i * 0.2)
    elif kind == "click":
        x = tt(0.025)
        place(sfx, t, highpass(noise(0.025), 3000) * np.exp(-x * 300), 0.35, 0.2)
    elif kind == "key":
        x = tt(0.02)
        place(sfx, t, highpass(noise(0.02), 3500) * np.exp(-x * 350), 0.14, 0.1)
    elif kind == "ding":
        place(sfx, t, bell(91, 1.0), 0.07, 0.3)

# ---------- mix ----------
mix = music * 0.85 + sfx
x = np.arange(N) / SR
end = timeline["duration"]
mix *= np.clip((end + 1.2 - x) / 1.6, 0, 1)[:, None]
mix = np.tanh(mix / np.max(np.abs(mix)) * 2.2)  # gentle limiting, then normalize
mix /= np.max(np.abs(mix)) / 0.85
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print(f"wrote {sys.argv[2]}: {DUR:.2f}s, {len(timeline['events'])} events")
