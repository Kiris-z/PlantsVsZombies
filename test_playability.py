#!/usr/bin/env python3
"""Playability test — simulates a full level 1-1 game."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))

from src.engine.game import Game
from src.scenes.gameplay import GameplayScene

game = Game()
game.scene_mgr.switch(GameplayScene(game))

gp = game.scene_mgr.current

# Check 1: Does the sun counter display properly?
print(f"Initial sun: {gp._sun_mgr.sun_count}")
print(f"Sun counter position: ({game.screen.get_width()}) — text at (21, 57)")

# Check 2: Can I only plant SunFlower at start (50 sun, peashooter=100)?
for c in gp._cards:
    print(f"  {c.name}: cost={c.cost}, can_plant(50)={c.can_plant(50)}")

# Check 3: Simulate 4 minutes of gameplay
print("\n--- Simulating full game (4 min) ---")
frames = 0
max_frames = 60 * 240  # 4 minutes

# Automated strategy: plant sunflowers first, then peashooters
import random
from src.systems.grid import LawnGrid
from src.entities.plant import create_plant

planted_cells = set()

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
    return True

sunflower_targets = [(r, 0) for r in range(5)]
peashooter_targets = [(r, c) for r in range(5) for c in range(1, 6)]

victory = False
game_over = False
stats = {"suns_collected": 0, "plants_placed": 0, "zombies_killed": 0}

while frames < max_frames:
    for event in pygame.event.get():
        game.scene_mgr.handle_event(event)
    
    # Auto collect suns
    for s in list(gp._sun_mgr._suns):
        if not s.collecting and not s.falling:
            s.collecting = True
            stats["suns_collected"] += 1
    
    # Auto plant
    sun = gp._sun_mgr.sun_count
    # Priority: sunflowers first
    for r, c in sunflower_targets:
        if (r, c) not in planted_cells and sun >= 50:
            if auto_plant(gp, "SunFlower", r, c):
                stats["plants_placed"] += 1
                break
    # Then peashooters
    sun = gp._sun_mgr.sun_count
    for r, c in peashooter_targets:
        if (r, c) not in planted_cells and sun >= 100:
            if auto_plant(gp, "Peashooter", r, c):
                stats["plants_placed"] += 1
                break
    
    game.scene_mgr.update(1/60)
    game.scene_mgr.draw(screen)
    
    frames += 1
    
    # Check end state
    if hasattr(gp, '_end_state'):
        from src.scenes.gameplay import _EndState
        if gp._end_state == _EndState.VICTORY:
            victory = True
            break
        elif gp._end_state == _EndState.GAME_OVER:
            game_over = True
            break
    
    # Print progress every 30s
    if frames % (60 * 30) == 0:
        elapsed = frames / 60
        alive_z = len(gp._zombie_mgr.all_alive())
        alive_p = len(gp._plant_mgr.all_alive())
        wave = gp._wave_sys.current_wave_index
        print(f"  {elapsed:.0f}s: wave={wave}/{gp._wave_sys.total_waves} zombies={alive_z} plants={alive_p} sun={gp._sun_mgr.sun_count}")

elapsed = frames / 60
print(f"\n--- Result after {elapsed:.0f}s ---")
print(f"  Victory: {victory}")
print(f"  Game Over: {game_over}")
print(f"  Waves completed: {gp._wave_sys.current_wave_index}/{gp._wave_sys.total_waves}")
print(f"  All waves done: {gp._wave_sys.all_waves_done}")
print(f"  Plants alive: {len(gp._plant_mgr.all_alive())}")
print(f"  Zombies alive: {len(gp._zombie_mgr.all_alive())}")
print(f"  Stats: {stats}")

# Final screenshot
pygame.image.save(screen, "/Users/maosen/.openclaw/workspace/pvz_endgame.png")
print("  Endgame screenshot saved")

pygame.quit()
