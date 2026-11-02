"""
LabRecorder by its remote control socket (P9 of D-F6-127): every session gets one
XDF with a unique name, sub-<participant>_ses-<session>_task-<condition>_run-<n>.

Only `filename`, `start` and `stop` are sent, never `select all`: on the lab network
other machines publish LSL streams too, so the operator ticks AURA and UnityMarkers
(P9 start order: AURA with LSL Stream Out, then LabRecorder with both streams, then
the session). `{run:}` is not used: LabRecorder's README marks it "not working?", so
the run goes into the template itself.

A failure here never stops the session: it is logged, and the operator falls back to
typing the name (the box in the S3 checklist).
"""

import logging
import re
import socket
import uuid

logger = logging.getLogger(__name__)


def _label(value: str) -> str:
    """BIDS labels are alphanumeric only."""
    return re.sub(r"[^A-Za-z0-9]", "", value)


def xdf_relpath(participant_code: str, session_id: uuid.UUID | str, condition: str, run: int = 1) -> str:
    """The XDF path under LabRecorder's root, BIDS layout as on 29 Oct."""
    # shortcut: run is always 1; the session id already makes the name unique, and LabRecorder
    # renames an existing file to *_oldN instead of overwriting it. Count runs if a session
    # is ever recorded twice on purpose.
    p, s, t = _label(participant_code), str(session_id)[:8], _label(condition)
    return f"sub-{p}/ses-{s}/eeg/sub-{p}_ses-{s}_task-{t}_run-{run}_eeg.xdf"


def start_commands(root: str, relpath: str) -> list[str]:
    return [f"filename {{root:{root}}} {{template:{relpath}}}", "start"]


def send(host: str, port: int, commands: list[str], timeout: float = 2.0) -> bool:
    """Sends the commands, one per line. False (and a log line) if LabRecorder is not there."""
    try:
        with socket.create_connection((host, port), timeout=timeout) as s:
            s.sendall("".join(c + "\n" for c in commands).encode("utf-8"))
        return True
    except OSError as exc:
        logger.warning("LabRecorder at %s:%s not reached (%s); the operator names the XDF by hand",
                       host, port, exc)
        return False
