"""Synthesizes the promo soundtrack from the timeline that render.mjs exports.

Usage: python3 score.py <timeline.json> <out.wav>

Everything is generated here with numpy: no samples, no downloads. The music
follows the scene grid (112 BPM, Am-F-C-G) and every sound effect is placed at
an event time taken from video.html, so picture and sound cannot drift apart.
"""
import json
import sys
import wave

import numpy as np

from synth import *  # noqa: F401,F403  (SR, rng, instruments)

timeline = json.load(open(sys.argv[1]))
BEAT = 60 / timeline["bpm"]
BAR = BEAT * 4
SC = timeline["scenes"]
INTRO = timeline.get("intro", 0.0)  # cover poster before the first bar
DUR = timeline["duration"] + 1.0
N = int(DUR * SR)
music = np.zeros((N, 2))
sfx = np.zeros((N, 2))


# ---------- harmony ----------
# chord tones (MIDI) per bar: Am F C G
PROG = {
    "Am": ([57, 60, 64, 69], 45),
    "F": ([57, 60, 65, 69], 41),
    "C": ([55, 60, 64, 67], 48),
    "G": ([55, 59, 62, 67], 43),
}
ORDER = ["Am", "F", "C", "G"]
TOTAL_BARS = 25


def chord_for(bar):
    if bar >= 21:
        return ["F", "G", "C", "C"][min(bar - 21, 3)]
    return ORDER[bar % 4]


def bar_t(b):
    return INTRO + b * BAR


for b in range(TOTAL_BARS):
    t0 = bar_t(b)
    name = chord_for(b)
    notes, root = PROG[name]
    intro = b < 4
    collapse = 4 <= b < 6
    groove = 6 <= b < 19
    claims = 19 <= b < 21
    outro = b >= 21

    # pad
    if intro:
        place_stereo(music, t0, pad_chord([57, 64], BAR + 0.3, 500 + 250 * b), 0.22 + 0.05 * b)
    elif collapse:
        if b == 5:
            place_stereo(music, t0, pad_chord([60, 64, 67, 72], BAR + 0.3, 900), 0.22)
    elif b == 24:
        place_stereo(music, t0, pad_chord([48, 55, 60, 64, 67, 72], BAR * 1.0 + 0.6, 1600), 0.34)
    else:
        place_stereo(music, t0, pad_chord(notes, BAR + 0.3, 1800 if groove else 1300), 0.26)

    for beat in range(4):
        tb = t0 + beat * BEAT
        # heartbeat in the intro
        if intro:
            if beat in (0, 2):
                place(music, tb, kick(), 0.35 + 0.1 * b)
            for s in range(4 if b >= 2 else 2):
                place(music, tb + s * BEAT / (4 if b >= 2 else 2), hat(), 0.05 + 0.03 * b, 0.3)
            place(music, tb, bass_note(45, BEAT * 0.9), 0.35)
        if collapse and b == 5:
            # snare roll accelerating into the reveal
            hits = 2 ** (beat + 1)
            for s in range(hits):
                place(music, tb + s * BEAT / hits, clap(), 0.12 + 0.07 * beat, rng.uniform(-0.2, 0.2))
        if groove or outro and b < 24:
            light = outro or (16 <= b < 17.75)
            place(music, tb, kick(), 0.55 if light and beat % 2 else 0.85)
            if beat in (1, 3):
                place(music, tb, clap(), 0.45 if not light else 0.3)
            for s in range(2):
                place(music, tb + s * BEAT / 2, hat(open_=s == 1 and beat == 3), 0.09 if s else 0.06, 0.35)
            # bass: root on the beat, octave on the off-beat
            place(music, tb, bass_note(root, BEAT * 0.45), 0.5)
            place(music, tb + BEAT / 2, bass_note(root + 12, BEAT * 0.4), 0.32)
            # arpeggio
            arp = notes + [notes[1] + 12]
            for s in range(2):
                n = arp[(beat * 2 + s) % len(arp)] + 12
                place(music, tb + s * BEAT / 2, pluck(n, 0.35, 0.8), 0.09, -0.4 + 0.8 * ((beat * 2 + s) % 2))
        if claims:
            if beat % 2 == 0:
                place(music, tb, kick(1.2), 0.9)
                place(music, tb, bass_note(root, BEAT * 1.6), 0.6)
            else:
                place(music, tb, clap(), 0.35)
            place(music, tb, hat(), 0.08, 0.3)

# ---------- sound effects from the picture ----------
PENTA = [69, 72, 74, 76, 79, 81, 84, 86, 88, 91, 93, 96]


def riser(sec):
    x = tt(sec)
    n = noise(sec)
    sweep = 300 + 7000 * (x / sec) ** 2
    sig = lowpass(n, sweep) * (x / sec) ** 1.5
    tone = np.sin(2 * np.pi * np.cumsum(220 + 660 * (x / sec) ** 2) / SR) * 0.25 * (x / sec) ** 2
    return sig + tone


def swish():
    sec = 0.4
    x = tt(sec)
    n = noise(sec)
    e = np.sin(np.pi * x / sec) ** 2
    return lowpass(highpass(n, 600), 1500 + 6000 * x / sec) * e


def boom():
    x = tt(2.5)
    sub = np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-x * 6)) / SR) * np.exp(-x * 1.6)
    crash = highpass(noise(2.5), 3000) * np.exp(-x * 2.2) * 0.4
    return sub + crash


def click():
    x = tt(0.03)
    return highpass(noise(0.03), 2500) * np.exp(-x * 260)


for e in timeline["events"]:
    t, kind = e["t"], e["type"]
    if kind == "pop":
        place(sfx, t, pluck(PENTA[e["i"]], 0.5, 1.2), 0.32, -0.6 + 1.2 * ((e["i"] * 5) % 12) / 11)
    elif kind == "riser":
        place(sfx, t, riser(e["len"]), 0.35)
    elif kind == "boom":
        place(sfx, t, boom(), 0.9)
    elif kind == "hit":
        if e.get("soft"):
            place(sfx, t, bell(72, 2.0), 0.18, -0.2)
            place(sfx, t, bell(79, 2.0), 0.12, 0.2)
        else:
            place(sfx, t, kick(1.3), 0.9)
            place(sfx, t, highpass(noise(2.0), 4000) * np.exp(-tt(2.0) * 2.5), 0.3)
    elif kind == "bubble":
        x = tt(0.25)
        f = midi([72, 76, 79][e["i"]]) * (1 + 0.6 * (1 - np.exp(-x * 30)))
        place(sfx, t, np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-x * 14), 0.35, [-0.3, 0.3, 0][e["i"]])
    elif kind == "click":
        place(sfx, t, click(), 0.55, 0.2)
    elif kind == "key":
        place(sfx, t, click() * rng.uniform(0.6, 1.0), 0.22 if e.get("soft") else 0.32, rng.uniform(-0.3, 0.3))
    elif kind == "ding":
        place(sfx, t, bell(88, 1.2), 0.16, 0.3)
    elif kind == "swish":
        place(sfx, t - 0.15, swish(), 0.25)
    elif kind == "type":
        for k in range(6):
            place(sfx, t + k * 0.045, click() * 0.7, 0.18, 0.4)
    elif kind == "ok":
        place(sfx, t, pluck(84, 0.4, 0.6), 0.15, 0.4)
    elif kind == "node":
        place(sfx, t, bell([69, 72, 76, 81][e["i"]], 1.2), 0.17, [-0.6, 0, 0.6, 0][e["i"]])
    elif kind == "slam":
        place(sfx, t, boom()[: int(0.8 * SR)], 0.45)
        place(sfx, t, pluck([81, 84, 88, 93][e["i"]], 0.5, 1.4), 0.25)
    elif kind == "intro":
        # a soft C-major shimmer under the cover poster
        for n, p in ((72, -0.3), (76, 0.3), (79, 0.0)):
            place(sfx, t + 0.02, bell(n, 2.0), 0.08, p)
        place_stereo(sfx, t, pad_chord([60, 64, 67], INTRO + 0.4, 1200), 0.2)
    elif kind == "final":
        for n, p in ((60, -0.4), (64, 0.0), (67, 0.4), (72, 0.1)):
            place(sfx, t, bell(n + 12, 3.5), 0.13, p)

# ---------- mix ----------
# duck the music briefly under the louder effects
duck = np.ones(N)
for e in timeline["events"]:
    if e["type"] in ("boom", "slam", "hit"):
        i = int(e["t"] * SR)
        n = int(0.5 * SR)
        duck[i : i + n] = np.minimum(duck[i : i + n], 0.55 + 0.45 * np.linspace(0, 1, len(duck[i : i + n])))
mix = music * duck[:, None] * 0.8 + sfx
# master fade-in/out and soft clip
x = np.arange(N) / SR
mix *= np.clip(x / 0.05, 0, 1)[:, None] * np.clip((timeline["duration"] + 0.6 - x) / 1.2, 0, 1)[:, None]
mix = np.tanh(mix * 1.1)
mix /= np.max(np.abs(mix)) / 0.89
pcm = (mix * 32767).astype("<i2")
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print(f"wrote {sys.argv[2]}: {DUR:.2f}s, {len(timeline['events'])} events")
