import faulthandler
import sys

import pytest

from app.eeg import autorun


def test_the_xdf_is_closed_only_after_it_stops_growing() -> None:
    # (seconds, bytes): LabRecorder still writing during block 3, then Stop at t=40.
    growing = [(0, 100), (10, 200), (20, 300), (30, 400), (40, 500)]
    assert not autorun.settled(growing, quiet_s=15)
    stopped = growing + [(50, 500), (54, 500)]
    assert not autorun.settled(stopped, quiet_s=15)   # quiet for 14 s only
    assert autorun.settled(stopped + [(56, 500)], quiet_s=15)


def test_a_missing_or_empty_xdf_is_never_closed() -> None:
    assert not autorun.settled([], quiet_s=15)
    assert not autorun.settled([(0, 0), (30, 0)], quiet_s=15)


async def _nothing(*_a, **_k):
    return None


@pytest.mark.asyncio
async def test_sync_runs_before_epochs_because_epochs_needs_the_offset(monkeypatch) -> None:
    from app.eeg import epochs, lsl_reader, sync

    calls = []

    def step(name, result):
        async def fill(_sid):
            calls.append(name)
            return result
        return fill

    async def new_session(_after):
        return "sid", "x.xdf"

    monkeypatch.setattr(autorun, "wait_new_session", new_session)
    monkeypatch.setattr(autorun, "wait_completed", _nothing)
    monkeypatch.setattr(autorun, "wait_xdf_closed", _nothing)
    monkeypatch.setattr(autorun, "start_child", lambda *_a, **_k: (None, None))
    monkeypatch.setattr(lsl_reader, "fill_from_xdf", step("lsl_reader", []))
    monkeypatch.setattr(sync, "fill_from_xdf", step("sync", (47.0, 17.0, {"reason": None})))
    monkeypatch.setattr(epochs, "fill_from_xdf", step("epochs", []))
    assert await autorun.main() == 0
    assert calls == ["lsl_reader", "sync", "epochs"]


def test_the_log_gets_this_process_and_the_child_output(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "stdout", sys.stdout)
    monkeypatch.setattr(sys, "stderr", sys.stderr)
    log = autorun.open_log(tmp_path)
    try:
        print("parent line")
        child, relay = autorun.start_child([sys.executable, "-c", "print('alpha ratio ≥ 1.2')"])
        child.wait()
        relay.join(5)
    finally:
        faulthandler.enable(file=sys.__stderr__)
        log.close()
    text = next(tmp_path.glob("autorun-*.log")).read_text(encoding="utf-8")
    assert "log: " in text and "parent line" in text and "alpha ratio ≥ 1.2" in text


def test_the_log_gets_the_line_even_when_the_console_fails(tmp_path) -> None:
    class Broken:
        def write(self, _s):
            raise OSError("console gone")

        def flush(self):
            pass

    with open(tmp_path / "x.log", "w", encoding="utf-8") as log:
        with pytest.raises(OSError):
            autorun._Tee(Broken(), log).write("last words\n")
    assert (tmp_path / "x.log").read_text(encoding="utf-8") == "last words\n"


@pytest.mark.asyncio
async def test_live_runs_next_to_baseline_and_stops_when_the_session_completes(monkeypatch) -> None:  # X1b
    from app.eeg import epochs, lsl_reader, sync

    started, stopped = [], []

    class Child:
        def __init__(self, args):
            self.name = args[-2]
        def poll(self):
            return None
        def terminate(self):
            stopped.append(self.name)

    async def new_session(_after):
        return "sid", "x.xdf"

    async def ok(_sid):
        return []

    def child(args):
        started.append(args[-2])
        return Child(args), None

    monkeypatch.setattr(autorun, "wait_new_session", new_session)
    monkeypatch.setattr(autorun, "wait_completed", _nothing)
    monkeypatch.setattr(autorun, "wait_xdf_closed", _nothing)
    monkeypatch.setattr(autorun, "start_child", child)
    monkeypatch.setattr(lsl_reader, "fill_from_xdf", ok)
    monkeypatch.setattr(sync, "fill_from_xdf", lambda _s: _async((1.0, 1.0, {"reason": None})))
    monkeypatch.setattr(epochs, "fill_from_xdf", ok)
    assert await autorun.main() == 0
    assert started == ["app.eeg.baseline", "app.eeg.live"] and stopped == ["app.eeg.live"]


async def _async(value):
    return value


@pytest.mark.asyncio
async def test_two_local_aura_keep_the_live_epochs_and_say_so(monkeypatch, capsys) -> None:  # G2, D-F6-206
    from app.eeg import epochs, lsl_reader, sync

    async def new_session(_after):
        return "sid", "x.xdf"

    async def ambiguous(_sid):
        raise lsl_reader.AmbiguousStream("x.xdf: 2 streams named 'AURA' from ThisPC; not filled, live epochs kept")

    async def must_not_run(_sid):
        raise AssertionError("nothing is filled")

    monkeypatch.setattr(autorun, "wait_new_session", new_session)
    monkeypatch.setattr(autorun, "wait_completed", _nothing)
    monkeypatch.setattr(autorun, "wait_xdf_closed", _nothing)
    monkeypatch.setattr(autorun, "start_child", lambda *_a, **_k: (None, None))
    monkeypatch.setattr(lsl_reader, "fill_from_xdf", ambiguous)
    monkeypatch.setattr(sync, "fill_from_xdf", must_not_run)
    monkeypatch.setattr(epochs, "fill_from_xdf", must_not_run)
    assert await autorun.main() == 1
    assert "not filled, live epochs kept" in capsys.readouterr().out


@pytest.fixture(autouse=True)
def _no_pc(monkeypatch):
    """No LSL, no network query and no LabRecorderCLI in these tests: manual path unless a test says otherwise."""
    monkeypatch.setattr(autorun, "start_recording", lambda sid, path: (None, "MANUAL: (test)"))
    monkeypatch.setattr(autorun, "network_up", lambda: [])


class FakeRec:
    def __init__(self, alive=True):
        self._alive, self.stops, self.started = alive, 0, 0.0
        self.proc = type("P", (), {"returncode": 2})()
        self.log_path = "cli.txt"

    def alive(self):
        return self._alive

    def stop(self):
        self.stops += 1
        self._alive = False
        return 0


def _wire(monkeypatch, rec, completed=_nothing):
    from app.eeg import epochs, lsl_reader, sync

    async def new_session(_after):
        return "sid", "x.xdf"

    monkeypatch.setattr(autorun, "wait_new_session", new_session)
    monkeypatch.setattr(autorun, "wait_completed", completed)
    monkeypatch.setattr(autorun, "wait_xdf_closed", _nothing)
    monkeypatch.setattr(autorun, "start_child", lambda *_a, **_k: (None, None))
    monkeypatch.setattr(autorun, "start_recording", lambda sid, path: (rec, "RECORDING (automatic): test"))
    monkeypatch.setattr(lsl_reader, "fill_from_xdf", lambda _s: _async([]))
    monkeypatch.setattr(sync, "fill_from_xdf", lambda _s: _async((1.0, 1.0, {"reason": None})))
    monkeypatch.setattr(epochs, "fill_from_xdf", lambda _s: _async([]))


@pytest.mark.asyncio
async def test_the_automatic_recording_is_stopped_at_completed(monkeypatch, capsys) -> None:  # AU2
    rec = FakeRec()
    _wire(monkeypatch, rec)
    assert await autorun.main() == 0
    out = capsys.readouterr().out
    assert rec.stops == 1 and "recording: automatic" in out and "recording stopped" in out


@pytest.mark.asyncio
async def test_autorun_dying_still_closes_the_file(monkeypatch) -> None:  # AU2: Enter in finally
    rec = FakeRec()

    async def dies(*_a, **_k):
        raise KeyboardInterrupt

    _wire(monkeypatch, rec, completed=dies)
    with pytest.raises(KeyboardInterrupt):
        await autorun.main()
    assert rec.stops == 1


def test_a_recording_lost_mid_session_keeps_its_part_and_sends_to_the_gui(tmp_path, capsys) -> None:
    path = tmp_path / "sub-t02_ses-1234abcd_task-x_run-1_eeg.xdf"
    path.write_text("part")
    autorun.recording_lost(FakeRec(alive=False), str(path))
    out = capsys.readouterr().out
    assert "RECORDING STOPPED" in out and "MANUAL" in out and "ses-1234abcd" in out
    assert not path.exists() and (tmp_path / "sub-t02_ses-1234abcd_task-x_run-1_eeg_partial.xdf").read_text() == "part"
