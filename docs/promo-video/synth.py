"""Shared numpy DSP helpers and instruments for the promo soundtracks."""
import numpy as np

SR = 48000
rng = np.random.default_rng(822)


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def tt(sec):
    return np.arange(int(sec * SR)) / SR


def env(n, a=0.005, d=0.2, s=0.0, r=0.0, total=None):
    """Attack/decay envelope with optional sustain tail, in samples."""
    total = total or n
    x = np.arange(total) / SR
    e = np.where(x < a, x / max(a, 1e-6), s + (1 - s) * np.exp(-(x - a) / max(d, 1e-6)))
    if r:
        e *= np.clip((total / SR - x) / r, 0, 1)
    return e


def _onepole(x, cutoff):
    """One-pole low-pass as an FFT convolution with its (truncated) impulse response."""
    a = np.exp(-2 * np.pi * cutoff / SR)
    h = (1 - a) * a ** np.arange(max(8, int(np.log(1e-5) / np.log(a)) + 1))
    n = len(x) + len(h) - 1
    size = 1 << (n - 1).bit_length()
    H = np.fft.rfft(h, size)
    X = np.fft.rfft(x, size, axis=0)
    y = np.fft.irfft(X * (H[:, None] if x.ndim > 1 else H), size, axis=0)
    return y[: len(x)]


def lowpass(x, cutoff):
    """One-pole low-pass; a time-varying cutoff blends a bank of fixed filters."""
    if np.ndim(cutoff) == 0:
        return _onepole(x, float(cutoff))
    cutoff = np.asarray(cutoff, dtype=float)
    bank = np.geomspace(cutoff.min(), cutoff.max(), 8)
    outs = np.stack([_onepole(x, c) for c in bank])
    pos = np.interp(np.log(cutoff), np.log(bank), np.arange(len(bank)))
    lo = np.floor(pos).astype(int).clip(0, len(bank) - 2)
    w = pos - lo
    if x.ndim > 1:
        w = w[:, None]
    idx = np.arange(len(x))
    return outs[lo, idx] * (1 - w) + outs[lo + 1, idx] * w


def highpass(x, cutoff):
    return x - lowpass(x, cutoff)


def place(buf, t, sig, gain=1.0, pan=0.0):
    i = int(t * SR)
    if i >= len(buf) or i + len(sig) <= 0:
        return
    if i < 0:
        sig, i = sig[-i:], 0
    sig = sig[: len(buf) - i]
    left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i : i + len(sig), 0] += sig * gain * left * 1.414
    buf[i : i + len(sig), 1] += sig * gain * right * 1.414


def saw(f, x):
    return 2 * ((f * x) % 1) - 1


# ---------- instruments ----------
def kick(gain=1.0):
    x = tt(0.45)
    f = 45 + 95 * np.exp(-x * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * np.exp(-x * 7) * gain + 0.3 * np.sin(ph * 2) * np.exp(-x * 40)


_noise_cache = {}


def noise(sec):
    key = round(sec, 4)
    if key not in _noise_cache:
        _noise_cache[key] = rng.uniform(-1, 1, int(sec * SR))
    return _noise_cache[key]


def hat(open_=False):
    n = noise(0.25 if open_ else 0.06)
    return highpass(highpass(n, 7000), 7000) * np.exp(-tt(len(n) / SR) * (14 if open_ else 70))


def clap():
    n = noise(0.3)
    x = tt(0.3)
    e = np.exp(-x * 18) + 0.6 * np.exp(-np.maximum(x - 0.012, 0) * 60) * (x > 0.012)
    return lowpass(lowpass(highpass(highpass(n, 900), 900), 5000), 5000) * e


def pluck(note, sec=0.6, bright=1.0):
    x = tt(sec)
    f = midi(note)
    sig = sum(np.sin(2 * np.pi * f * k * x) * np.exp(-x * (5 + 4 * k)) * (bright / k) for k in range(1, 6))
    return sig * np.minimum(1, x / 0.003)


def bell(note, sec=1.6):
    x = tt(sec)
    f = midi(note)
    ratios = [(1, 1, 2.2), (2.76, 0.5, 4), (5.4, 0.25, 7), (8.9, 0.1, 10)]
    return sum(a * np.sin(2 * np.pi * f * r * x) * np.exp(-x * d) for r, a, d in ratios) * np.minimum(1, x / 0.002)


def pad_chord(notes, sec, cutoff=1400):
    x = tt(sec)
    sig = np.zeros((len(x), 2))
    for n in notes:
        for det, ch in ((-0.09, 0), (0.09, 1), (0.0, 0), (0.0, 1)):
            sig[:, ch] += saw(midi(n + det), x + rng.uniform(0, 1))
    sig = lowpass(sig, cutoff) / (len(notes) * 2)
    fade = np.minimum(1, np.minimum(x / 0.25, (sec - x) / 0.35))[:, None]
    return sig * fade


def bass_note(note, sec):
    x = tt(sec)
    f = midi(note)
    s = np.sin(2 * np.pi * f * x) + 0.35 * lowpass(saw(f, x), 600)
    return s * env(len(x), 0.004, 0.18, 0.35) * np.minimum(1, (sec - x) / 0.02)


def place_stereo(buf, t, sig, gain=1.0):
    i = int(t * SR)
    sig = sig[: len(buf) - i]
    buf[i : i + len(sig)] += sig * gain
