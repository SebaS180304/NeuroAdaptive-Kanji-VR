"""
A synthetic AURA stream for checks without the cap (D-F6-132): 8 channels at 250 Hz, named
and typed like the real one (`AURA` / `EEG`), with a 10 Hz sine of 20 uV on every channel.

    python scripts/synthetic_aura.py [seconds]      # default: until Ctrl+C

Never during a real session: LabRecorder would show two AURA streams on this PC.
"""

import math
import sys
import time

import pylsl

RATE, CHANNELS = 250, 8

info = pylsl.StreamInfo("AURA", "EEG", CHANNELS, RATE, "float32", "synthetic-aura")
outlet = pylsl.StreamOutlet(info)
seconds = float(sys.argv[1]) if len(sys.argv) > 1 else math.inf
start, sent = time.perf_counter(), 0
print(f"synthetic AURA: {CHANNELS} ch, {RATE} Hz")
while time.perf_counter() - start < seconds:
    due = int((time.perf_counter() - start) * RATE)
    while sent < due:
        v = 20.0 * math.sin(2 * math.pi * 10 * sent / RATE)
        outlet.push_sample([v] * CHANNELS)
        sent += 1
    time.sleep(0.004)
