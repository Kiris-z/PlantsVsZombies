#!/usr/bin/env python3
"""Headless QA test for PVZ Level 1-1 — improved bot + detailed diagnostics.

Sets SDL_VIDEODRIVER=dummy, SDL_AUDIODRIVER=dummy via os.environ before importing pygame.
"""

import os, sys, time, traceback

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))

from src.config import (
    GRID_ROWS, GRID_COLS, CELL_WIDTH, CELL_HEIGHT,
    GRID_X_START, GRID_Y_START, SCREEN_WIDTH, SCREEN_HEIGHT,
    PLANT_DEFS,
)
from src.systems.grid import LawnGrid
from src.systems.economy import SunManager
from src.systems.wave import WaveSystem
from src.systems.combat import CombatSystem
from src.systems.lawnmower import LawnMowerManager
from src.entities.plant import (
    PlantManager, create_plant,
    Peashooter, SunFlower, SnowPea, RepeaterPea, ScaredyShroom,
)
from src.entities.zombie import ZombieManager
from src.entities.bullet import BulletManager


class SmartBot:
    """Better bot: alternates SF+PS placements, prioritizes defense rows with zombies."""

    def __init__(self, plant_mgr, sun_mgr):
        self.plant_mgr = plant_mgr
        self.sun_mgr = sun_mgr
        self._cooldowns = {"SunFlower": 0.0, "Peashooter": 0.0}
        # Phase 1: 2 sunflowers in rows with zombies, then peashooters
        # Level 1-1: zombies come in rows 1, 2, 3
        self._plan = [
            ("SunFlower", 2, 0),   # row 2 gets zombies first
            ("Peashooter", 2, 1),  # defend row 2 immediately
            ("SunFlower", 1, 0),
            ("Peashooter", 1, 1),
            ("SunFlower", 3, 0),
            ("Peashooter", 3, 1),
            # Prioritize second peashooters on attacked rows before economy
            ("Peashooter", 3, 2),  # row 3 needs 2 PS to survive wave 5
            ("Peashooter", 2, 2),
            ("Peashooter", 1, 2),
            # Extra economy if sun allows
            ("SunFlower", 0, 0),
            ("SunFlower", 4, 0),
        ]
        self._idx = 0

    def update(self, dt):
        for k in self._cooldowns:
            self._cooldowns[k] = max(0.0, self._cooldowns[k] - dt)

        if self._idx >= len(self._plan):
            return

        name, row, col = self._plan[self._idx]
        cost = PLANT_DEFS[name]["cost"]
        cd = PLANT_DEFS[name]["cooldown"]

        if self.sun_mgr.sun_count >= cost and self._cooldowns[name] <= 0:
            if self.plant_mgr.get_at(row, col) is None:
                plant = create_plant(name, row, col)
                self.plant_mgr.add(plant)
                self.sun_mgr.sun_count -= cost
                self._cooldowns[name] = cd
            self._idx += 1


def auto_collect_suns(sun_mgr):
    """Simulate clicking on every available sun."""
    collected = 0
    for s in sun_mgr._suns:
        if s.alive and not s.collecting and not s.falling:
            s.collecting = True
            s.falling = False
            collected += 1
    return collected


def run_test():
    print("=" * 60)
    print("PVZ Headless QA — Level 1-1")
    print("=" * 60)

    zombie_mgr = ZombieManager()
    wave_sys = WaveSystem("src/data/levels/level_1_1.json", zombie_mgr)
    plant_mgr = PlantManager()
    bullet_mgr = BulletManager()
    combat = CombatSystem(bullet_mgr, zombie_mgr)
    sun_mgr = SunManager()
    sun_mgr.sun_count = wave_sys.initial_sun
    lawnmowers = LawnMowerManager()
    bot = SmartBot(plant_mgr, sun_mgr)

    # Metrics
    total_suns_collected = 0
    total_bullets_fired = 0
    total_hits = 0
    total_zombies_spawned = 0
    total_zombies_killed = 0
    peak_sun = sun_mgr.sun_count
    plants_planted = 0
    game_result = "TIMEOUT"
    frames = 0
    game_time = 0.0
    errors = []
    mower_activations = 0

    # Diagnostic events log
    events_log = []

    DT = 1.0 / 60.0
    MAX_GAME_SECONDS = 600

    prev_bullet_count = 0
    prev_zombie_count = 0

    try:
        while game_time < MAX_GAME_SECONDS:
            frames += 1
            game_time += DT

            # Bot: auto-collect suns
            c = auto_collect_suns(sun_mgr)
            total_suns_collected += c

            # Bot: auto-plant
            old_count = len(plant_mgr.plants)
            bot.update(DT)
            new_plants = len(plant_mgr.plants) - old_count
            if new_plants > 0:
                plants_planted += new_plants
                newest = plant_mgr.plants[-1]
                events_log.append(f"  t={game_time:6.1f}s  Planted {newest.name} @ ({newest.row},{newest.col})  sun={sun_mgr.sun_count}")

            # Sun
            sun_mgr.update(DT)
            if sun_mgr.sun_count > peak_sun:
                peak_sun = sun_mgr.sun_count

            # Waves
            old_zombie_count = len(zombie_mgr.zombies)
            wave_sys.update(DT)
            spawned_now = len(zombie_mgr.zombies) - old_zombie_count
            if spawned_now > 0:
                total_zombies_spawned += spawned_now
                for z in zombie_mgr.zombies[-spawned_now:]:
                    events_log.append(f"  t={game_time:6.1f}s  Spawned {type(z).__name__} row={z.row} wave={wave_sys.current_wave_index}")

            # Plants — shoot, produce sun, etc.
            for plant in plant_mgr.all_alive():
                kwargs = {
                    "sun_mgr": sun_mgr,
                    "bullet_mgr": bullet_mgr,
                    "zombie_mgr": zombie_mgr,
                }
                if isinstance(plant, (Peashooter, SnowPea, RepeaterPea, ScaredyShroom)):
                    kwargs["zombies_in_row"] = len(zombie_mgr.get_by_row(plant.row)) > 0
                plant.update(DT, **kwargs)

            # Bullets count
            cur_bullets = len(bullet_mgr.bullets)
            new_bullets = cur_bullets - prev_bullet_count
            if new_bullets > 0:
                total_bullets_fired += new_bullets

            bullet_mgr.update(DT)

            # Zombies
            cur_alive = zombie_mgr.total_spawned_alive
            zombie_mgr.update(DT, plant_mgr)

            # Combat: track hits
            pre_hp = {id(z): z.total_hp for z in zombie_mgr.all_alive()}
            combat.update(DT)
            for z in zombie_mgr.all_alive():
                zid = id(z)
                if zid in pre_hp and z.total_hp < pre_hp[zid]:
                    total_hits += 1

            # Lawnmowers
            old_mower_states = [(m.row, m.activated) for m in lawnmowers.mowers]
            lawnmowers.update(DT, zombie_mgr)
            for i, m in enumerate(lawnmowers.mowers):
                if m.activated and not old_mower_states[i][1]:
                    mower_activations += 1
                    events_log.append(f"  t={game_time:6.1f}s  ⚠ Lawnmower activated row={m.row}")

            # Kill tracking
            new_alive = zombie_mgr.total_spawned_alive
            if new_alive < cur_alive:
                killed_now = cur_alive - new_alive
                total_zombies_killed += killed_now
                events_log.append(f"  t={game_time:6.1f}s  Killed {killed_now} zombie(s), {new_alive} remaining")

            prev_bullet_count = len(bullet_mgr.bullets)

            # Win/Lose
            if lawnmowers.check_zombie_reach(zombie_mgr):
                game_result = "GAME_OVER"
                events_log.append(f"  t={game_time:6.1f}s  💀 GAME OVER — zombie reached house")
                break

            if wave_sys.all_waves_done and zombie_mgr.total_spawned_alive == 0:
                game_result = "VICTORY"
                events_log.append(f"  t={game_time:6.1f}s  🏆 VICTORY")
                break

    except Exception as e:
        game_result = "CRASH"
        errors.append(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")

    # ── Report ────────────────────────────────────────────────────
    print()
    print(f"Result:            {game_result}")
    print(f"Game time:         {game_time:.1f}s ({frames} frames)")
    print(f"Waves:             {wave_sys.current_wave_index}/{wave_sys.total_waves} (all_done={wave_sys.all_waves_done})")
    print()
    print("── Economy ──")
    print(f"  Initial sun:     {wave_sys.initial_sun}")
    print(f"  Suns collected:  {total_suns_collected}")
    print(f"  Peak sun:        {peak_sun}")
    print(f"  Final sun:       {sun_mgr.sun_count}")
    print(f"  Plants planted:  {plants_planted}")
    print()
    print("── Combat ──")
    print(f"  Zombies spawned: {total_zombies_spawned}")
    print(f"  Zombies killed:  {total_zombies_killed}")
    print(f"  Bullets fired:   {total_bullets_fired}")
    print(f"  Hits registered: {total_hits}")
    hit_rate = (total_hits / total_bullets_fired * 100) if total_bullets_fired > 0 else 0
    print(f"  Hit rate:        {hit_rate:.1f}%")
    print(f"  Mower activations: {mower_activations}")
    print()
    print("── Plants alive ──")
    for p in plant_mgr.all_alive():
        print(f"  {p.name:15s} ({p.row},{p.col})  HP={p.hp}/{p.max_hp}")
    print()
    print("── Lawn mowers ──")
    for m in lawnmowers.mowers:
        status = "used" if m.activated else ("gone" if not m.alive else "ready")
        print(f"  Row {m.row}: {status}")
    print()
    print("── Event Log ──")
    for ev in events_log:
        print(ev)

    if errors:
        print()
        print("── ERRORS ──")
        for e in errors:
            print(e)

    print()
    print("=" * 60)

    # ── Assertions ────────────────────────────────────────────────
    issues = []

    if game_result == "CRASH":
        issues.append(f"CRASH: {errors[0] if errors else 'unknown'}")

    if game_result == "TIMEOUT":
        issues.append("Game did not end within 600s")

    if game_result == "GAME_OVER":
        issues.append("Bot lost Level 1-1")

    if total_suns_collected == 0 and game_time > 30:
        issues.append("Zero suns collected — sky sun spawning or collection broken")

    if total_bullets_fired == 0 and game_time > 60:
        issues.append("Zero bullets fired — Peashooters never shot (possible zombies_in_row detection issue)")

    if total_bullets_fired > 0 and total_hits == 0:
        issues.append("Bullets fired but zero hits — collision detection broken")

    if total_zombies_spawned == 0 and game_time > 40:
        issues.append("No zombies spawned — wave system broken")

    if game_result == "VICTORY" and total_zombies_killed == 0:
        issues.append("Victory but 0 kills — tracking broken")

    if issues:
        print("⚠️  ISSUES FOUND:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        return False
    else:
        print("✅ All checks passed")
        return True


if __name__ == "__main__":
    start = time.time()
    ok = run_test()
    elapsed = time.time() - start
    print(f"\nWall-clock time: {elapsed:.1f}s")
    pygame.quit()
    sys.exit(0 if ok else 1)
