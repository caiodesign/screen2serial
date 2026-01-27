from dataclasses import dataclass
from typing import Literal
import time

# =========================
# STATE TYPES
# =========================
StateName = Literal["warmup", "searching", "collecting", "dropping"]

WARMUP: StateName = "warmup"
SEARCHING: StateName = "searching"
COLLECTING: StateName = "collecting"
DROPPING: StateName = "dropping"

ALL_STATES = (WARMUP, SEARCHING, COLLECTING, DROPPING)


@dataclass(frozen=True)
class AppState:
    """Immutable application state."""
    name: StateName
    since: float
    last_scan: float  # Last time we scanned during collecting


@dataclass(frozen=True)
class Stats:
    """Immutable stats container."""
    clicks: int
    drops: int
    resources_collected: int
    state_time: dict[StateName, float]


def make_initial_state() -> AppState:
    """Create initial application state."""
    return AppState(name=WARMUP, since=time.time(), last_scan=0.0)


def make_initial_stats() -> Stats:
    """Create initial stats."""
    return Stats(
        clicks=0,
        drops=0,
        resources_collected=0,
        state_time={s: 0.0 for s in ALL_STATES},
    )


def transition_state(
    state: AppState,
    now: float,
    to: StateName,
    last_scan: float | None = None,
) -> AppState:
    """Pure function to transition to a new state."""
    return AppState(
        name=to,
        since=now,
        last_scan=last_scan if last_scan is not None else state.last_scan,
    )


def accumulate_state_time(stats: Stats, state_name: StateName, delta: float) -> Stats:
    """Pure function to add time to a state's accumulator."""
    new_time = {**stats.state_time}
    new_time[state_name] = new_time[state_name] + delta
    return Stats(
        clicks=stats.clicks,
        drops=stats.drops,
        resources_collected=stats.resources_collected,
        state_time=new_time,
    )


def increment_clicks(stats: Stats) -> Stats:
    """Pure function to increment click count."""
    return Stats(
        clicks=stats.clicks + 1,
        drops=stats.drops,
        resources_collected=stats.resources_collected,
        state_time=stats.state_time,
    )


def increment_drops(stats: Stats, count: int = 1) -> Stats:
    """Pure function to increment drop count."""
    return Stats(
        clicks=stats.clicks,
        drops=stats.drops + count,
        resources_collected=stats.resources_collected,
        state_time=stats.state_time,
    )


def increment_resources(stats: Stats) -> Stats:
    """Pure function to increment resources collected count."""
    return Stats(
        clicks=stats.clicks,
        drops=stats.drops,
        resources_collected=stats.resources_collected + 1,
        state_time=stats.state_time,
    )
