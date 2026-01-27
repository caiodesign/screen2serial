from dataclasses import dataclass
from typing import Literal
import time

# =========================
# STATE TYPES
# =========================
StateName = Literal["waiting", "verify", "starting", "collecting", "cooldown"]

WAITING: StateName = "waiting"
VERIFY: StateName = "verify"
STARTING: StateName = "starting"
COLLECTING: StateName = "collecting"
COOLDOWN: StateName = "cooldown"

ALL_STATES = (WAITING, VERIFY, STARTING, COLLECTING, COOLDOWN)


@dataclass(frozen=True)
class AppState:
    """Immutable application state."""
    name: StateName
    since: float
    verify_count: int


@dataclass(frozen=True)
class Stats:
    """Immutable stats container."""
    clicks: int
    verify_fail: int
    resets: int
    state_time: dict[StateName, float]


def make_initial_state() -> AppState:
    """Create initial application state."""
    return AppState(name=WAITING, since=time.time(), verify_count=0)


def make_initial_stats() -> Stats:
    """Create initial stats."""
    return Stats(
        clicks=0,
        verify_fail=0,
        resets=0,
        state_time={s: 0.0 for s in ALL_STATES},
    )


def transition_state(
    state: AppState,
    now: float,
    to: StateName,
    verify_count: int | None = None,
) -> AppState:
    """Pure function to transition to a new state."""
    return AppState(
        name=to,
        since=now,
        verify_count=verify_count if verify_count is not None else state.verify_count,
    )


def accumulate_state_time(stats: Stats, state_name: StateName, delta: float) -> Stats:
    """Pure function to add time to a state's accumulator."""
    new_time = {**stats.state_time}
    new_time[state_name] = new_time[state_name] + delta
    return Stats(
        clicks=stats.clicks,
        verify_fail=stats.verify_fail,
        resets=stats.resets,
        state_time=new_time,
    )


def increment_clicks(stats: Stats) -> Stats:
    """Pure function to increment click count."""
    return Stats(
        clicks=stats.clicks + 1,
        verify_fail=stats.verify_fail,
        resets=stats.resets,
        state_time=stats.state_time,
    )


def increment_verify_fail(stats: Stats) -> Stats:
    """Pure function to increment verify fail count."""
    return Stats(
        clicks=stats.clicks,
        verify_fail=stats.verify_fail + 1,
        resets=stats.resets,
        state_time=stats.state_time,
    )


def increment_resets(stats: Stats) -> Stats:
    """Pure function to increment reset count."""
    return Stats(
        clicks=stats.clicks,
        verify_fail=stats.verify_fail,
        resets=stats.resets + 1,
        state_time=stats.state_time,
    )
