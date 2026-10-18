from __future__ import annotations

import asyncio

import pytest

from scripts.evaluate_narrator_models import _CallPacer


@pytest.mark.parametrize("oversleep", [0.025, 0.5, 2.0])
def test_oversleep_does_not_shorten_the_next_call_interval(oversleep: float) -> None:
    elapsed = 0.0
    starts: list[float] = []
    waits: list[float] = []

    async def sleep(seconds: float) -> None:
        nonlocal elapsed
        waits.append(seconds)
        elapsed += seconds + (oversleep if len(waits) == 1 else 0.0)

    pacer = _CallPacer(60.0, _clock=lambda: elapsed, _sleeper=sleep)

    async def exercise() -> None:
        nonlocal elapsed
        for index in range(3):
            await pacer.before_call(f"call {index}")
            starts.append(elapsed)
            elapsed += 2.0

    asyncio.run(exercise())

    assert starts == pytest.approx([0.0, 60.0 + oversleep, 120.0 + oversleep])
    assert all(second - first >= 60.0 for first, second in zip(starts, starts[1:]))
    assert waits == pytest.approx([58.0, 58.0])


@pytest.mark.parametrize("early_return", [0.025, 0.5, 30.0])
def test_early_sleep_return_waits_for_the_remaining_time(early_return: float) -> None:
    elapsed = 1.0
    waits: list[float] = []

    async def sleep(seconds: float) -> None:
        nonlocal elapsed
        waits.append(seconds)
        elapsed += seconds - (early_return if len(waits) == 1 else 0.0)

    pacer = _CallPacer(
        60.0, _last_call_started_at=0.0, _clock=lambda: elapsed, _sleeper=sleep
    )
    asyncio.run(pacer.before_call("next call"))

    assert elapsed >= 60.0
    assert waits == pytest.approx([59.0, early_return])
    assert pacer._last_call_started_at == pytest.approx(elapsed)


def test_cancelled_wait_does_not_mark_a_call_or_advance_the_anchor(capsys) -> None:
    elapsed = 1.0
    waits: list[float] = []

    async def sleep(seconds: float) -> None:
        nonlocal elapsed
        waits.append(seconds)
        if len(waits) == 1:
            elapsed += 20.0
            raise asyncio.CancelledError
        elapsed += seconds

    pacer = _CallPacer(
        60.0, _last_call_started_at=0.0, _clock=lambda: elapsed, _sleeper=sleep
    )

    async def exercise() -> None:
        with pytest.raises(asyncio.CancelledError):
            await pacer.before_call("cancelled call")
        assert pacer._last_call_started_at == 0.0
        await pacer.before_call("next call")

    asyncio.run(exercise())

    assert waits == [59.0, 39.0]
    assert elapsed == 60.0
    assert pacer._last_call_started_at == 60.0
    output = capsys.readouterr().out
    assert "Calling provider: cancelled call" not in output
    assert output.count("Calling provider:") == 1


@pytest.mark.parametrize("interval, elapsed", [(0.0, 0.0), (60.0, 75.0)])
def test_elapsed_or_zero_interval_does_not_sleep(interval: float, elapsed: float) -> None:
    async def unexpected_sleep(seconds: float) -> None:
        pytest.fail(f"Unexpected pacing wait: {seconds}")

    pacer = _CallPacer(
        interval, _last_call_started_at=0.0, _clock=lambda: elapsed,
        _sleeper=unexpected_sleep,
    )
    asyncio.run(pacer.before_call("ready call"))

    assert pacer._last_call_started_at == elapsed
