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
    monkeypatch.setattr(autorun.subprocess, "Popen", lambda *_a, **_k: None)
    monkeypatch.setattr(lsl_reader, "fill_from_xdf", step("lsl_reader", []))
    monkeypatch.setattr(sync, "fill_from_xdf", step("sync", (47.0, 17.0, {"reason": None})))
    monkeypatch.setattr(epochs, "fill_from_xdf", step("epochs", []))
    assert await autorun.main() == 0
    assert calls == ["lsl_reader", "sync", "epochs"]
