"""
A synthetic AURA stream for checks without the cap (D-F6-132): 8 channels at 250 Hz, named
and typed like the real one (`AURA` / `EEG`), with a 10 Hz sine of 20 uV on every channel.
On top (12 Nov, J1): a slow drift of the sine's amplitude (+-8 uV, 60 s period) and seeded Gaussian noise
(SD 5 uV, per channel), so epochs differ, the S6 reference has SD > 0 and z exists. Peaks stay under the
blink (75 uV) and amplitude (100 uV) rules of epochs.py.

    python scripts/synthetic_aura.py [seconds]      # default: until Ctrl+C

Never during a real session: LabRecorder would show two AURA streams on this PC.
"""

import math
import random
import sys
import time

import pylsl

RATE, CHANNELS = 250, 8
NOISE_UV, DRIFT_UV, DRIFT_S = 5.0, 8.0, 60.0

info = pylsl.StreamInfo("AURA", "EEG", CHANNELS, RATE, "float32", "synthetic-aura")
outlet = pylsl.StreamOutlet(info)
seconds = float(sys.argv[1]) if len(sys.argv) > 1 else math.inf
start, sent = time.perf_counter(), 0
rng = random.Random(1812)
print(f"synthetic AURA: {CHANNELS} ch, {RATE} Hz")
while time.perf_counter() - start < seconds:
    due = int((time.perf_counter() - start) * RATE)
    while sent < due:
        t = sent / RATE
        v = (20.0 + DRIFT_UV * math.sin(2 * math.pi * t / DRIFT_S)) * math.sin(2 * math.pi * 10 * t)
        outlet.push_sample([v + rng.gauss(0.0, NOISE_UV) for _ in range(CHANNELS)])
        sent += 1
    time.sleep(0.004)
