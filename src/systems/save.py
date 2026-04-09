"""Save system — JSON-based save/load for player progress."""

from __future__ import annotations

import json
import os
from typing import Any

from src.config import PLANT_UNLOCK_TABLE, LEVEL_LIST

SAVE_PATH = os.path.expanduser("~/.pvz_save.json")

# Default save state — Level 1-1 is always unlocked
_DEFAULT_SAVE: dict[str, Any] = {
    "unlocked_levels": ["1-1"],
    "completed_levels": [],
    "unlocked_plants": ["Peashooter", "SunFlower"],
    "high_scores": {},  # level_id -> int
}


class SaveManager:
    """Manages reading and writing the player save file."""

    _instance: SaveManager | None = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._data = None
        return cls._instance

    # ── Data access ───────────────────────────────────────────────────

    @property
    def data(self) -> dict[str, Any]:
        if self._data is None:
            self.load()
        return self._data

    @property
    def unlocked_levels(self) -> list[str]:
        return self.data.get("unlocked_levels", ["1-1"])

    @property
    def completed_levels(self) -> list[str]:
        return self.data.get("completed_levels", [])

    @property
    def unlocked_plants(self) -> list[str]:
        return self.data.get("unlocked_plants", ["Peashooter", "SunFlower"])

    @property
    def high_scores(self) -> dict[str, int]:
        return self.data.get("high_scores", {})

    # ── Load / Save ───────────────────────────────────────────────────

    def load(self):
        """Load save from disk, or create default."""
        if os.path.exists(SAVE_PATH):
            try:
                with open(SAVE_PATH, "r") as f:
                    self._data = json.load(f)
                # Ensure all keys exist
                for key, default in _DEFAULT_SAVE.items():
                    if key not in self._data:
                        self._data[key] = default
            except (json.JSONDecodeError, IOError):
                self._data = dict(_DEFAULT_SAVE)
        else:
            self._data = dict(_DEFAULT_SAVE)

    def save(self):
        """Persist current data to disk."""
        try:
            with open(SAVE_PATH, "w") as f:
                json.dump(self._data, f, indent=2)
        except IOError:
            pass  # silently fail (e.g. read-only FS)

    # ── Game actions ──────────────────────────────────────────────────

    def complete_level(self, level_id: str, score: int = 0):
        """Mark a level as completed, unlock the next level and new plants."""
        d = self.data

        # Mark completed
        if level_id not in d["completed_levels"]:
            d["completed_levels"].append(level_id)

        # Update high score
        prev = d["high_scores"].get(level_id, 0)
        if score > prev:
            d["high_scores"][level_id] = score

        # Unlock plants from this level
        plants = PLANT_UNLOCK_TABLE.get(level_id, [])
        for p in plants:
            if p not in d["unlocked_plants"]:
                d["unlocked_plants"].append(p)

        # Unlock the next level
        level_ids = [lv["id"] for lv in LEVEL_LIST]
        if level_id in level_ids:
            idx = level_ids.index(level_id)
            if idx + 1 < len(level_ids):
                next_id = level_ids[idx + 1]
                if next_id not in d["unlocked_levels"]:
                    d["unlocked_levels"].append(next_id)

        self.save()

    def is_level_unlocked(self, level_id: str) -> bool:
        return level_id in self.unlocked_levels

    def is_level_completed(self, level_id: str) -> bool:
        return level_id in self.completed_levels

    def reset(self):
        """Reset save to defaults."""
        self._data = dict(_DEFAULT_SAVE)
        # Deep copy lists
        self._data["unlocked_levels"] = list(_DEFAULT_SAVE["unlocked_levels"])
        self._data["completed_levels"] = list(_DEFAULT_SAVE["completed_levels"])
        self._data["unlocked_plants"] = list(_DEFAULT_SAVE["unlocked_plants"])
        self._data["high_scores"] = dict(_DEFAULT_SAVE["high_scores"])
        self.save()
