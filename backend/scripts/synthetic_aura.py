"""
A synthetic AURA stream for checks without the cap (D-F6-132): 8 channels at 250 Hz, named
and typed like the real one (`AURA` / `EEG`), with a 10 Hz sine of 20 uV on every channel.
On top (12 Nov, J1): a slow drift of the sine's amplitude (+-8 uV, 60 s period) and seeded Gaussian noise
(SD 5 uV, per channel), so epochs differ, the S6 reference has SD > 0 and z exists. Peaks stay under the
blink (75 uV) and amplitude (100 uV) rules of epochs.py.
S4 (12 Nov, J1 again): it listens to UnityMarkers and, between EYES_CLOSED_START and EYES_CLOSED_END,
multiplies the 10 Hz sine by 1.6 (alpha power x2.6), so baseline.py's test (>= 1.2) passes as with a real cap.

    python scripts/synthetic_aura.py [seconds]      # default: until Ctrl+C

Never during a real session: LabRecorder would show two AURA streams on this PC.
"""

import json
import math
import random
import sys
import time

import pylsl

RATE, CHANNELS = 250, 8
NOISE_UV, DRIFT_UV, DRIFT_S = 5.0, 8.0, 60.0
ALPHA_CLOSED = 1.6

info = pylsl.StreamInfo("AURA", "EEG", CHANNELS, RATE, "float32", "synthetic-aura")
outlet = pylsl.StreamOutlet(info)
seconds = float(sys.argv[1]) if len(sys.argv) > 1 else math.inf
start, sent = time.perf_counter(), 0
rng = random.Random(1812)
resolver = pylsl.ContinuousResolver(prop="name", value="UnityMarkers")   # never blocks the samples
inlets, closed, looked = {}, False, 0.0   # every UnityMarkers on the PC: an old Play's can linger, silent
print(f"synthetic AURA: {CHANNELS} ch, {RATE} Hz")
while time.perf_counter() - start < seconds:
    now = time.perf_counter()
    if now - looked > 1.0:
        looked = now
        for found in resolver.results():
            if found.uid() not in inlets:
                inlets[found.uid()] = pylsl.StreamInlet(found)
    for uid, inlet in list(inlets.items()):
        try:
            for v in inlet.pull_chunk(timeout=0.0)[0]:
                event = json.loads(v[0]).get("event")
                if event in ("EYES_CLOSED_START", "EYES_CLOSED_END"):
                    closed = event == "EYES_CLOSED_START"
                    print(f"synthetic AURA: {event}, alpha x{ALPHA_CLOSED if closed else 1}", flush=True)
        except (RuntimeError, ValueError):   # pylsl.util.LostError is a RuntimeError: that Play ended
            del inlets[uid]
    due = int((time.perf_counter() - start) * RATE)
    while sent < due:
        t = sent / RATE
        gain = ALPHA_CLOSED if closed else 1.0
        v = gain * (20.0 + DRIFT_UV * math.sin(2 * math.pi * t / DRIFT_S)) * math.sin(2 * math.pi * 10 * t)
        outlet.push_sample([v + rng.gauss(0.0, NOISE_UV) for _ in range(CHANNELS)])
        sent += 1
    time.sleep(0.004)
