#!/usr/bin/env python3
"""Cron QA test v3: headless Level 1-1 with diagnostics."""
import sys, os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))

from src.engine.game import Game
from src.scenes.gameplay import GameplayScene, _EndState
from src.entities.plant import create_plant

game = Game()
game.scene_mgr.switch(GameplayScene(game))
gp = game.scene_mgr.current

planted_cells = set()  # (row, col) -> plant name
planted_names = {}
zombies_killed = 0
mower_activations = []
game_over_reason = ""

def auto_plant(gp, name, row, col):
    if (row, col) in planted_cells:
        return False
    card = None
    for c in gp._cards:
        if c.name == name and c.can_plant(gp._sun_mgr.sun_count):
            card = c
            break
    if card is None:
        return False
    plant = create_plant(name, row, col)
    gp._plant_mgr.add(plant)
    gp._sun_mgr.sun_count -= card.cost
    card.cooldown_remaining = card.cooldown_max
    planted_cells.add((row, col))
    planted_names[(row, col)] = name
    return True

print("=== PVZ QA Cron Test v3: Level 1-1 ===\n")
print(f"Initial sun: {gp._sun_mgr.sun_count}")

# Check level config
print(f"Level waves: {gp._wave_sys.total_waves}")
print(f"Available cards: {[c.name for c in gp._cards]}")

frames = 0
max_frames = 60 * 300  # 5 minutes
DT = 1.0 / 60.0

# Track mower states
prev_mower_states = {m.row: (m.alive, m.activated) for m in gp._lawnmowers.mowers}

while frames < max_frames:
    for event in pygame.event.get():
        game.scene_mgr.handle_event(event)

    # Aggressive sun collection
    for s in list(gp._sun_mgr._suns):
        if not s.collecting:
            s.collecting = True

    sun = gp._sun_mgr.sun_count
    elapsed_s = frames / 60.0

    # Strategy: prioritize defense coverage
    # 1. First 2 sunflowers in col 0 (rows 1,3 - middle rows)
    # 2. Peashooters in EVERY row col 2 (main defense line)
    # 3. More sunflowers
    # 4. More peashooters
    # 5. WallNuts col 6 for tank rows

    sf_count = sum(1 for rc in planted_cells if planted_names.get(rc) == "SunFlower")
    ps_count = sum(1 for rc in planted_cells if planted_names.get(rc) == "Peashooter")
    wn_count = sum(1 for rc in planted_cells if planted_names.get(rc) == "WallNut")
    rows_with_ps = set(r for (r, c) in planted_cells if planted_names.get((r, c)) == "Peashooter")
    ps_per_row = {}
    for (r, c) in planted_cells:
        if planted_names.get((r, c)) == "Peashooter":
            ps_per_row[r] = ps_per_row.get(r, 0) + 1

    # Level 1-1 waves: Normal zombies in rows 2,2,1+3,2+1,2+1+3
    # Row 2 is hit HARDEST (waves 1,2,4,5). Rows 1,3 hit in waves 3,4,5.
    # Rows 0,4 are NEVER attacked. So focus defense on rows 1,2,3 only.
    # Normal zombie: 200hp, 0.5 cells/s. Peashooter: 20dmg/1.4s = ~14.3 dps
    # Time for 1 PS to kill Normal: 14s. Zombie cross time: ~19s. BARELY enough.
    # Need 2 PS in row 2 (hit every wave) to handle back-to-back zombies.

    # Phase 1: First sunflower (economy start)
    if sf_count < 1 and sun >= 50:
        auto_plant(gp, "SunFlower", 2, 0)
        sun = gp._sun_mgr.sun_count

    # Phase 2: First peashooter in row 2 ASAP (first wave targets row 2!)
    if sf_count >= 1 and ps_count < 1 and sun >= 100:
        auto_plant(gp, "Peashooter", 2, 3)
        sun = gp._sun_mgr.sun_count

    # Phase 3: Second sunflower for economy
    if ps_count >= 1 and sf_count < 2 and sun >= 50:
        auto_plant(gp, "SunFlower", 1, 0)
        sun = gp._sun_mgr.sun_count

    # Phase 4: SECOND peashooter in row 2 (this row gets hit every other wave!)
    if sf_count >= 2 and ps_per_row.get(2, 0) < 2 and sun >= 100:
        auto_plant(gp, "Peashooter", 2, 2)
        sun = gp._sun_mgr.sun_count

    # Phase 5: Peashooters in rows 1 and 3 (hit in wave 3)
    if ps_per_row.get(2, 0) >= 2 and sun >= 100:
        for r in [1, 3]:
            if r not in rows_with_ps:
                if auto_plant(gp, "Peashooter", r, 3):
                    sun = gp._sun_mgr.sun_count
                    break

    # Phase 6: Third sunflower
    if len(rows_with_ps) >= 3 and sf_count < 3 and sun >= 50:
        auto_plant(gp, "SunFlower", 3, 0)
        sun = gp._sun_mgr.sun_count

    # Phase 7: Second peashooter in rows 1,3
    if len(rows_with_ps) >= 3 and sun >= 100:
        for r in [1, 3]:
            if ps_per_row.get(r, 0) < 2:
                if auto_plant(gp, "Peashooter", r, 2):
                    sun = gp._sun_mgr.sun_count
                    break

    # Phase 8: More sunflowers in unused rows
    if ps_count >= 5 and sf_count < 5 and sun >= 50:
        for r in [0, 4]:
            if (r, 0) not in planted_cells:
                if auto_plant(gp, "SunFlower", r, 0):
                    sun = gp._sun_mgr.sun_count
                    break

    # Phase 9: WallNuts for row 2 (takes most hits)
    if ps_count >= 6 and sun >= 50:
        for r in [2, 1, 3]:
            if (r, 5) not in planted_cells:
                if auto_plant(gp, "WallNut", r, 5):
                    sun = gp._sun_mgr.sun_count
                    break

    # Phase 10: Third peashooter per attacked row
    if ps_count >= 6 and sun >= 100:
        for r in [2, 1, 3]:
            if ps_per_row.get(r, 0) < 3:
                for c in [4, 1]:
                    if (r, c) not in planted_cells:
                        if auto_plant(gp, "Peashooter", r, c):
                            sun = gp._sun_mgr.sun_count
                            break
                break

    # Track zombie changes
    prev_zombie_ids = set(id(z) for z in gp._zombie_mgr.zombies)
    
    game.scene_mgr.update(DT)
    game.scene_mgr.draw(screen)

    curr_zombie_ids = set(id(z) for z in gp._zombie_mgr.zombies)
    removed = prev_zombie_ids - curr_zombie_ids
    zombies_killed += len(removed)

    # Check mower state changes
    for m in gp._lawnmowers.mowers:
        prev = prev_mower_states.get(m.row, (True, False))
        if m.activated and not prev[1]:
            elapsed = frames / 60
            mower_activations.append((elapsed, m.row))
            print(f"  ⚠️ [{elapsed:.0f}s] Mower activated in row {m.row}!")
        if not m.alive and prev[0]:
            elapsed = frames / 60
            print(f"  🚗 [{elapsed:.0f}s] Mower used up in row {m.row}")
    prev_mower_states = {m.row: (m.alive, m.activated) for m in gp._lawnmowers.mowers}

    frames += 1

    if hasattr(gp, '_end_state'):
        if gp._end_state == _EndState.VICTORY:
            break
        elif gp._end_state == _EndState.GAME_OVER:
            # Log diagnostic info
            elapsed = frames / 60
            for z in gp._zombie_mgr.all_alive():
                print(f"  💀 Zombie row={z.row} x={z.x:.0f} hp={z.hp} alive={z.alive}")
            for m in gp._lawnmowers.mowers:
                print(f"  🚗 Mower row={m.row} alive={m.alive} activated={m.activated}")
            # Which rows have peashooters?
            for r in range(5):
                row_plants = [(c, planted_names.get((r, c), "?")) for c in range(9) if (r, c) in planted_cells]
                print(f"  🌱 Row {r}: {row_plants}")
            break

    if frames % (60 * 10) == 0:
        elapsed = frames / 60
        alive_z = len(gp._zombie_mgr.all_alive())
        alive_p = len(gp._plant_mgr.all_alive())
        wave = gp._wave_sys.current_wave_index
        bullets = len(gp._bullet_mgr.bullets)
        z_detail = [(z.row, f"x={z.x:.0f}", f"hp={z.hp}") for z in gp._zombie_mgr.all_alive()[:5]]
        print(f"  [{elapsed:.0f}s] w={wave}/{gp._wave_sys.total_waves} "
              f"z={alive_z} p={alive_p} sun={sun} planted={len(planted_cells)} "
              f"sf={sf_count} ps={ps_count}")
        if z_detail:
            print(f"    zombies: {z_detail}")

elapsed = frames / 60
end = "PLAYING"
if gp._end_state == _EndState.VICTORY:
    end = "VICTORY ✅"
elif gp._end_state == _EndState.GAME_OVER:
    end = "GAME_OVER ❌"

print(f"\n{'='*50}")
print(f"Result: {end} at {elapsed:.0f}s ({frames} frames)")
print(f"  Waves: {gp._wave_sys.current_wave_index}/{gp._wave_sys.total_waves}")
print(f"  Plants placed: {len(planted_cells)}")
print(f"  Plants alive: {len(gp._plant_mgr.all_alive())}")
print(f"  Zombies killed: {zombies_killed}")
print(f"  Zombies remaining: {len(gp._zombie_mgr.all_alive())}")
print(f"  Mower activations: {mower_activations}")

# System health checks
print(f"\n--- System Health ---")
sun_ok = gp._sun_mgr.sun_count >= 0
print(f"  {'✅' if sun_ok else '❌'} Sun economy: {gp._sun_mgr.sun_count}")
print(f"  ✅ No crash")

if gp._end_state == _EndState.VICTORY:
    if gp._wave_sys.all_waves_done and len(gp._zombie_mgr.all_alive()) == 0:
        print(f"  ✅ Victory condition correct")
    else:
        print(f"  ❌ Victory triggered incorrectly!")

pygame.quit()
sys.exit(0 if gp._end_state == _EndState.VICTORY else 1)
