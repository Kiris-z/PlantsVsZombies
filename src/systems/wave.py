"""Wave system — timed zombie spawning driven by level data."""

from __future__ import annotations

import json
import os
import random
from typing import TYPE_CHECKING

from src.config import BASE_DIR, GRID_ROWS
from src.entities.zombie import create_zombie

if TYPE_CHECKING:
    from src.entities.zombie import ZombieManager


class WaveSystem:
    """Reads a level JSON file and spawns zombies according to the wave timeline.

    Level JSON format
    -----------------
    {
      "name": "Level 1-1",
      "initial_sun": 50,
      "available_plants": ["Peashooter", "SunFlower", "WallNut"],
      "waves": [
        {
          "wait": 30,
          "flag": false,
          "spawns": [
            {"type": "Normal", "row": 3, "delay": 0},
            ...
          ]
        },
        ...
      ]
    }

    ``row`` may be ``-1`` for "random row".
    ``delay`` is seconds *within* the wave after the wave starts.
    """

    def __init__(self, level_path: str, zombie_mgr: ZombieManager):
        self._zombie_mgr = zombie_mgr
        self._data = self._load(level_path)
        self._waves: list[dict] = self._data["waves"]
        self._current_wave: int = 0
        self._wave_timer: float = 0.0
        self._wave_active: bool = False
        self._spawn_queue: list[dict] = []
        self._all_spawned: bool = False
        self._total_zombies_spawned: int = 0

        # Start the countdown to the first wave
        if self._waves:
            self._wave_timer = self._waves[0]["wait"]

    @staticmethod
    def _load(path: str) -> dict:
        full = os.path.join(BASE_DIR, path)
        with open(full, "r") as f:
            return json.load(f)

    # ── public queries ────────────────────────────────────────────────

    @property
    def current_wave_index(self) -> int:
        return self._current_wave

    @property
    def total_waves(self) -> int:
        return len(self._waves)

    @property
    def all_waves_done(self) -> bool:
        return self._all_spawned

    @property
    def is_flag_wave(self) -> bool:
        if 0 <= self._current_wave < len(self._waves):
            return self._waves[self._current_wave].get("flag", False)
        return False

    @property
    def level_name(self) -> str:
        return self._data.get("name", "Unknown")

    @property
    def initial_sun(self) -> int:
        return self._data.get("initial_sun", 50)

    @property
    def available_plants(self) -> list[str]:
        return self._data.get("available_plants", [])

    # ── update ────────────────────────────────────────────────────────

    def update(self, dt: float):
        if self._all_spawned:
            return

        # Process spawn queue (delayed spawns within current wave)
        remaining = []
        for entry in self._spawn_queue:
            entry["_timer"] -= dt
            if entry["_timer"] <= 0:
                self._do_spawn(entry)
            else:
                remaining.append(entry)
        self._spawn_queue = remaining

        # If wave is active but all spawns have been emitted, advance
        if self._wave_active and not self._spawn_queue:
            self._wave_active = False
            self._current_wave += 1
            if self._current_wave >= len(self._waves):
                self._all_spawned = True
            else:
                self._wave_timer = self._waves[self._current_wave]["wait"]

        # Waiting between waves
        if not self._wave_active and not self._all_spawned:
            self._wave_timer -= dt
            if self._wave_timer <= 0:
                self._start_wave(self._current_wave)

    def _start_wave(self, index: int):
        if index >= len(self._waves):
            self._all_spawned = True
            return
        wave = self._waves[index]
        self._wave_active = True
        for spawn_def in wave.get("spawns", []):
            entry = dict(spawn_def)
            entry["_timer"] = entry.get("delay", 0.0)
            self._spawn_queue.append(entry)

    def _do_spawn(self, entry: dict):
        row = entry.get("row", -1)
        if row < 0 or row >= GRID_ROWS:
            row = random.randint(0, GRID_ROWS - 1)
        z_type = entry.get("type", "Normal")
        zombie = create_zombie(z_type, row)
        self._zombie_mgr.add(zombie)
        self._total_zombies_spawned += 1
