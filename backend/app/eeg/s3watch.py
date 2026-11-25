"""
Warnings for the operator before S4 (AU3, D-F6-244), printed in autorun's console by live.py. It only warns;
it changes nothing in the rule or the session.
  - each SYNC_TAP: clear or not, on raw Cz as sync.py judges it after the session, and the clear count so far
    (D-F6-197: not the next tap without the peak; under 3 clear taps the session has no offset, D-F6-176);
    a tap outside S3 → warning (D-F6-217: none in S9);
  - from S2 to the end of S3, every 10 s: a channel with > 20 % of its last 30 s over 100 µV (D-F6-216's
    measure, on the filtered signal as epochs.py, leaving out ±1 s around each SYNC_TAP) → fix it before S4 (D-F6-213); Fp1 gets D-F6-240 (2)'s line;
  - in S3, a HEAD_AWAY open for more than 10 s (from S2 or S3) → re-seat the headset and repeat the taps before S4 (D-F6-249 (2)).
From S4 on it prints nothing: nothing is touched from S4 to S8 (D-F6-153).
"""

import numpy as np

from app.eeg import preprocess, sync
from app.eeg.epochs import TAP_GUARD_S  # the taps on Cz's housing: not a bad channel (T02, 18 Nov; D-F6-224)

S2, S3, S4 = "S2_VR_TUTORIAL", "S3_SYSTEM_VALIDATION", "S4_EEG_BASELINE"
BAD_UV, BAD_SHARE, SPAN_S, EVERY_S, PAD_S = 100.0, 0.20, 30.0, 10.0, 5.0
TAPS = 5
AWAY_S = 10.0  # D-F6-249 (2)


class S3Watch:
    def __init__(self, montage: dict):
        order = sorted(montage, key=lambda k: int(k[2:]))
        self.names = [montage[k] for k in order]
        self.cz = self.names.index("Cz")
        self.taps_seen: set[float] = set()
        self.clear = 0
        self.bad: set[str] = set()
        self.next_check: float | None = None
        self.closed = False
        self.away_warned: set = set()

    def lines(self, x: list, ts: list, markers: list[tuple[float, dict]], srate: float) -> list[str]:
        if self.closed or len(ts) == 0:
            return []
        entered = {m.get("state"): t for t, m in markers if m.get("event") == "STATE_ENTERED"}
        now, out = ts[-1], []
        for t, m in markers:
            if m.get("event") != "SYNC_TAP" or t in self.taps_seen or now < t + sync.WINDOW_S + 0.1:
                continue
            self.taps_seen.add(t)
            if m.get("phase") != "S3":
                out.append(f"WARNING: tap in {m.get('phase')}, outside S3: no taps after S3 (D-F6-217)")
                continue
            arr = np.asarray(x, dtype=float)
            d = sync._tap(arr[:, self.cz], np.asarray(ts, dtype=float), t)
            n = len([1 for tt, mm in markers if mm.get("event") == "SYNC_TAP" and mm.get("phase") == "S3"
                     and tt in self.taps_seen])
            if d["valid"]:
                self.clear += 1
                out.append(f"tap {n}/{TAPS}: clear (peak {d['peak_uv']:.0f} uV) - {self.clear} clear so far")
            else:
                out.append(f"tap {n}/{TAPS}: NOT clear ({d['why']}) - {self.clear} clear so far; "
                           f"check the peak in AURA before the next tap (D-F6-197)")
        if S3 in entered and S4 not in entered:
            out += self._away(markers, now)
        if S4 in entered:
            out.append(f"S3 taps: {self.clear}/{TAPS} clear"
                       + ("" if self.clear >= sync.MIN_TAPS else
                          f" - WARNING: under {sync.MIN_TAPS}, the session gets no sync correction (D-F6-176)"))
            if self.bad:
                out.append(f"WARNING: S4 starts with {', '.join(sorted(self.bad))} bad (D-F6-213)")
            self.closed = True
            return out
        if S2 in entered and (self.next_check is None or now >= self.next_check):
            self.next_check = now + EVERY_S
            taps = [t for t, m in markers if m.get("event") == "SYNC_TAP"]
            out += self._channels(x, ts, srate, taps)
        return out

    def _away(self, markers: list[tuple[float, dict]], now: float) -> list[str]:
        """Each HEAD_AWAY episode still open AWAY_S after its onset (as epochs.excluded_intervals times it), once."""
        open_ = {}
        for t, m in markers:
            if m.get("event") == "HEAD_AWAY":
                open_[m.get("episode")] = (t + m.get("onset_offset_ms", 0) / 1000, m.get("state"))
            elif m.get("event") == "HEAD_RETURNED":
                open_.pop(m.get("episode"), None)
        out = []
        for episode, (start, state) in open_.items():
            if now - start > AWAY_S and episode not in self.away_warned:
                self.away_warned.add(episode)
                out.append(f"WARNING: HEAD_AWAY open since {state} - re-seat the headset before S4 (D-F6-249)")
        return out

    def _channels(self, x: list, ts: list, srate: float, taps: list[float] = ()) -> list[str]:
        if ts[-1] - ts[0] < SPAN_S + PAD_S:
            return []
        n = int((SPAN_S + PAD_S) * srate)
        y = preprocess.filter_eeg(np.asarray(x[-n:], dtype=float), srate)[-int(SPAN_S * srate):]
        t = np.asarray(ts[-len(y):], dtype=float)
        keep = np.ones(len(y), bool)
        for tap in taps:
            keep &= np.abs(t - tap) > TAP_GUARD_S
        if not keep.any():
            return []
        share = (np.abs(y[keep]) > BAD_UV).mean(axis=0)
        out = []
        for name, s in zip(self.names, share):
            if s > BAD_SHARE and name not in self.bad:
                self.bad.add(name)
                fix = ("re-seat Fp1 and the visor foam before S4 (D-F6-240 (2))" if name == "Fp1"
                       else "fix it before S4 (D-F6-213)")
                out.append(f"WARNING: {name} looks bad ({s:.0%} of the last 30 s over 100 uV): {fix}")
            elif s <= BAD_SHARE and name in self.bad:
                self.bad.discard(name)
                out.append(f"{name} ok again ({s:.0%} over 100 uV)")
        return out
