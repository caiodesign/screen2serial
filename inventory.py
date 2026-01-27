"""
Inventory scanning and dropping logic.

Scans the inventory region for resources using template matching,
finds all matching positions, and returns their center coordinates.
"""

import cv2
import numpy as np
from dataclasses import dataclass
from mss import mss

import config
from capture import load_template, grab_region, preprocess_crop


# Minimum distance (pixels) between two detections to consider them different items
MIN_ITEM_DISTANCE = 30


@dataclass(frozen=True)
class InventoryItem:
    """Represents a found item in the inventory."""
    x: int  # Absolute screen X coordinate (center of item)
    y: int  # Absolute screen Y coordinate (center of item)
    confidence: float


def find_resources_in_inventory(
    sct: mss,
    monitor: dict,
    template: np.ndarray,
    threshold: float = None,
) -> list[InventoryItem]:
    """
    Scan the inventory region and find all resources matching the template.
    
    Args:
        sct: mss screen capturer
        monitor: Monitor dict from mss
        template: Grayscale template image of the resource
        threshold: Match threshold (defaults to config.INVENTORY_RESOURCE_THRESHOLD)
    
    Returns:
        List of InventoryItem with absolute screen coordinates for each found resource
    """
    if threshold is None:
        threshold = config.INVENTORY_RESOURCE_THRESHOLD
    
    # Capture the inventory region
    frame = grab_region(
        sct, monitor,
        config.INVENTORY_X_START, config.INVENTORY_Y_START,
        config.INVENTORY_X_END, config.INVENTORY_Y_END,
    )
    gray = preprocess_crop(frame)
    
    # Template matching
    result = cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)
    
    # Find all matches above threshold
    locations = np.where(result >= threshold)
    
    # Get template dimensions for calculating center points
    template_h, template_w = template.shape[:2]
    
    # Get all detection points with their confidence
    points = list(zip(locations[1], locations[0]))  # (x, y) pairs
    
    if not points:
        return []
    
    # Get confidence values and create list of (x, y, confidence)
    detections = []
    for x, y in points:
        conf = result[y, x]
        # Calculate center point
        center_x = x + (template_w // 2)
        center_y = y + (template_h // 2)
        detections.append((center_x, center_y, conf))
    
    # Sort by confidence (highest first)
    detections.sort(key=lambda d: d[2], reverse=True)
    
    # Filter out duplicates using distance-based deduplication
    # Keep highest confidence detection, remove others within MIN_ITEM_DISTANCE
    unique_items = []
    
    for cx, cy, conf in detections:
        # Check if this detection is too close to an already picked item
        is_duplicate = False
        for item in unique_items:
            dist = ((cx - (item.x - config.INVENTORY_X_START))**2 + 
                    (cy - (item.y - config.INVENTORY_Y_START))**2) ** 0.5
            if dist < MIN_ITEM_DISTANCE:
                is_duplicate = True
                break
        
        if not is_duplicate:
            # Convert to absolute screen coordinates
            abs_x = config.INVENTORY_X_START + cx
            abs_y = config.INVENTORY_Y_START + cy
            unique_items.append(InventoryItem(x=abs_x, y=abs_y, confidence=conf))
    
    return unique_items


def get_drop_order(items: list[InventoryItem]) -> list[InventoryItem]:
    """
    Sort items for efficient dropping (top to bottom, left to right).
    
    Args:
        items: List of InventoryItem to sort
    
    Returns:
        Sorted list of items
    """
    # Sort by Y first (top to bottom), then by X (left to right)
    return sorted(items, key=lambda item: (item.y, item.x))
