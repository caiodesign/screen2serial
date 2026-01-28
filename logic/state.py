"""
Shared state infrastructure for screen2serial macros.

This module provides generic building blocks that all macros can use.
Each macro defines its own states and uses these helpers.
"""

from dataclasses import dataclass, field
from typing import Any
import time


# =========================
# SHARED STATE: WARMUP
# =========================
# All macros share the WARMUP state - waiting for user to start
WARMUP = "warmup"


@dataclass(frozen=True)
class AppState:
    """
    Generic immutable application state.
    
    Each macro defines its own state names and can store
    macro-specific data in the `data` dict.
    """
    name: str
    since: float
    data: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Stats:
    """
    Generic immutable stats container.
    
    - clicks: Number of clicks performed
    - actions: Number of main actions completed (drops, kills, enchants, etc.)
    - cycles: Number of full cycles completed (tree->drop, enemy->loot, etc.)
    - state_time: Time spent in each state
    - extra: Macro-specific stats
    """
    clicks: int
    actions: int
    cycles: int
    state_time: dict[str, float]
    extra: dict[str, Any] = field(default_factory=dict)


def make_initial_state(initial_name: str = WARMUP) -> AppState:
    """Create initial application state."""
    return AppState(name=initial_name, since=time.time(), data={})


def make_initial_stats(all_states: tuple[str, ...]) -> Stats:
    """Create initial stats with time tracking for given states."""
    return Stats(
        clicks=0,
        actions=0,
        cycles=0,
        state_time={s: 0.0 for s in all_states},
        extra={},
    )


def transition_state(
    state: AppState,
    now: float,
    to: str,
    **data_updates,
) -> AppState:
    """
    Pure function to transition to a new state.
    
    Args:
        state: Current state
        now: Current timestamp
        to: Name of the new state
        **data_updates: Key-value pairs to update in state.data
        
    Returns:
        New AppState with updated name, timestamp, and data
    """
    new_data = {**state.data, **data_updates}
    return AppState(name=to, since=now, data=new_data)


def update_state_data(state: AppState, **data_updates) -> AppState:
    """Pure function to update state data without changing state name."""
    new_data = {**state.data, **data_updates}
    return AppState(name=state.name, since=state.since, data=new_data)


def accumulate_state_time(stats: Stats, state_name: str, delta: float) -> Stats:
    """Pure function to add time to a state's accumulator."""
    new_time = {**stats.state_time}
    if state_name in new_time:
        new_time[state_name] = new_time[state_name] + delta
    else:
        new_time[state_name] = delta
    return Stats(
        clicks=stats.clicks,
        actions=stats.actions,
        cycles=stats.cycles,
        state_time=new_time,
        extra=stats.extra,
    )


def increment_clicks(stats: Stats) -> Stats:
    """Pure function to increment click count."""
    return Stats(
        clicks=stats.clicks + 1,
        actions=stats.actions,
        cycles=stats.cycles,
        state_time=stats.state_time,
        extra=stats.extra,
    )


def increment_actions(stats: Stats, count: int = 1) -> Stats:
    """Pure function to increment action count (drops, kills, enchants, etc.)."""
    return Stats(
        clicks=stats.clicks,
        actions=stats.actions + count,
        cycles=stats.cycles,
        state_time=stats.state_time,
        extra=stats.extra,
    )


def increment_cycles(stats: Stats) -> Stats:
    """Pure function to increment cycle count."""
    return Stats(
        clicks=stats.clicks,
        actions=stats.actions,
        cycles=stats.cycles + 1,
        state_time=stats.state_time,
        extra=stats.extra,
    )


def update_extra(stats: Stats, **extra_updates) -> Stats:
    """Pure function to update extra stats."""
    new_extra = {**stats.extra, **extra_updates}
    return Stats(
        clicks=stats.clicks,
        actions=stats.actions,
        cycles=stats.cycles,
        state_time=stats.state_time,
        extra=new_extra,
    )
