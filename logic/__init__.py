"""
Logic package for screen2serial bot.

Contains core modules:
- state: State management (AppState, Stats, transitions)
- actions: Mouse/keyboard actions via Arduino
- vision: Computer vision and template matching
- capture: Screen capture utilities
- serial_io: Serial communication with Arduino
- debug: Debugging utilities
"""

from .state import (
    AppState,
    Stats,
    WARMUP,
    make_initial_state,
    make_initial_stats,
    transition_state,
    update_state_data,
    accumulate_state_time,
    increment_clicks,
    increment_actions,
    increment_cycles,
    update_extra,
)

from .serial_io import (
    open_serial,
    send_move,
    send_click,
    send_right_click,
    send_shift_click,
    send_shift_hold,
    send_shift_release,
    send_key,
    compute_hesitation,
)

from .capture import (
    load_template,
    crop_template,
    create_screen_capturer,
    grab_region,
    preprocess_crop,
    match_template,
    MatchResult,
    validate_template_size,
    show_live_windows,
)

from .vision import (
    Region,
    Point,
    find_all_templates,
    sort_by_position,
    get_last_item_bottom_right,
    find_template,
    template_exists,
    count_template,
)

from .vision_debug import (
    find_template as find_template_debug,
    find_all_templates as find_all_templates_debug,
    template_exists as template_exists_debug,
    count_template as count_template_debug,
    find_closest_template_debug,
    cleanup_debug_windows,
)

from .actions import (
    get_mouse_position,
    is_mouse_at_target,
    wait_for_mouse_arrival,
    random_delay,
    click_at,
    click_point,
    click_at_right,
    drop_items,
    move_to,
    move_to_point,
    press_key,
    open_combat_tab,
    open_skills_tab,
    open_quests_tab,
    open_inventory,
    open_equipment_tab,
    open_prayer_tab,
    open_magic_tab,
    open_settings,
)

__all__ = [
    # State
    "AppState",
    "Stats",
    "WARMUP",
    "make_initial_state",
    "make_initial_stats",
    "transition_state",
    "update_state_data",
    "accumulate_state_time",
    "increment_clicks",
    "increment_actions",
    "increment_cycles",
    "update_extra",
    # Serial
    "open_serial",
    "send_move",
    "send_click",
    "send_right_click",
    "send_shift_click",
    "send_shift_hold",
    "send_shift_release",
    "send_key",
    "compute_hesitation",
    # Capture
    "load_template",
    "crop_template",
    "create_screen_capturer",
    "grab_region",
    "preprocess_crop",
    "match_template",
    "MatchResult",
    "validate_template_size",
    "show_live_windows",
    # Vision
    "Region",
    "Point",
    "find_all_templates",
    "sort_by_position",
    "get_last_item_bottom_right",
    "find_template",
    "template_exists",
    "count_template",
    # Vision Debug (proxy functions with visualization)
    "find_template_debug",
    "find_all_templates_debug",
    "template_exists_debug",
    "count_template_debug",
    "find_closest_template_debug",
    "cleanup_debug_windows",
    # Actions
    "get_mouse_position",
    "is_mouse_at_target",
    "wait_for_mouse_arrival",
    "random_delay",
    "click_at",
    "click_point",
    "click_at_right",
    "drop_items",
    "move_to",
    "move_to_point",
    "press_key",
    "open_combat_tab",
    "open_skills_tab",
    "open_quests_tab",
    "open_inventory",
    "open_equipment_tab",
    "open_prayer_tab",
    "open_magic_tab",
    "open_settings",
]
