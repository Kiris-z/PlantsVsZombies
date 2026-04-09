#!/usr/bin/env python3
"""Deep integration test — simulates real gameplay and reports all issues found."""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))

from src.engine.game import Game
from src.scenes.menu import MenuScene
from src.scenes.gameplay import GameplayScene
from src.scenes.level_select import LevelSelectScene
from src.systems.grid import LawnGrid
from src.config import GRID_ROWS, GRID_COLS, CELL_WIDTH, CELL_HEIGHT, GRID_X_START, GRID_Y_START

issues = []

def report(category, msg):
    issues.append(f"[{category}] {msg}")
    print(f"  ⚠️  [{category}] {msg}")

def tick(game, n=1, dt=1/60):
    for _ in range(n):
        for event in pygame.event.get():
            game.scene_mgr.handle_event(event)
        game.scene_mgr.update(dt)
        game.scene_mgr.draw(game.screen)
        pygame.display.flip()

def inject_click(game, pos):
    ev = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=pos)
    game.scene_mgr.handle_event(ev)
    ev2 = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=pos)
    game.scene_mgr.handle_event(ev2)

def inject_drag(game, start, end):
    ev1 = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=start)
    game.scene_mgr.handle_event(ev1)
    # Simulate motion
    ev2 = pygame.event.Event(pygame.MOUSEMOTION, pos=end, rel=(end[0]-start[0], end[1]-start[1]), buttons=(1,0,0))
    game.scene_mgr.handle_event(ev2)
    ev3 = pygame.event.Event(pygame.MOUSEBUTTONUP, button=1, pos=end)
    game.scene_mgr.handle_event(ev3)

game = Game()

# ═══════════════════════════════════════════════════════════════════════
print("=" * 60)
print("TEST 1: Menu Scene")
print("=" * 60)
game.scene_mgr.switch(MenuScene(game))
tick(game, 5)

scene = game.scene_mgr.current
if not hasattr(scene, '_btn_rect'):
    report("MENU", "No start button rect found")
else:
    btn = scene._btn_rect
    print(f"  Start button at: {btn}")
    if btn.width < 10 or btn.height < 10:
        report("MENU", f"Start button too small: {btn.size}")
    if btn.right > 800 or btn.bottom > 600 or btn.left < 0 or btn.top < 0:
        report("MENU", f"Start button out of screen: {btn}")

# Click start
inject_click(game, scene._btn_rect.center)
tick(game, 3)
new_scene = game.scene_mgr.current
scene_type = type(new_scene).__name__
print(f"  After click start: scene = {scene_type}")
if scene_type not in ("LevelSelectScene", "GameplayScene"):
    report("MENU", f"Clicking start went to {scene_type} instead of LevelSelect/Gameplay")

# ═══════════════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 2: Level Select")
print("=" * 60)
if scene_type != "LevelSelectScene":
    game.scene_mgr.switch(LevelSelectScene(game))
    tick(game, 5)

ls = game.scene_mgr.current
if hasattr(ls, '_buttons'):
    print(f"  Level buttons: {len(ls._buttons)}")
    unlocked = [b for b in ls._buttons if b.unlocked]
    print(f"  Unlocked: {[b.level_id for b in unlocked]}")
    if not unlocked:
        report("LEVEL_SELECT", "No levels unlocked!")
    for b in ls._buttons:
        if b.unlocked and not b.level_file:
            report("LEVEL_SELECT", f"Level {b.level_id} unlocked but no level file!")
else:
    report("LEVEL_SELECT", "No _buttons attribute!")

# Click first unlocked level
if unlocked:
    btn = unlocked[0]
    inject_click(game, btn.rect.center)
    tick(game, 3)
    gp_type = type(game.scene_mgr.current).__name__
    print(f"  After clicking {btn.level_id}: scene = {gp_type}")
    if gp_type != "GameplayScene":
        report("LEVEL_SELECT", f"Clicking level went to {gp_type}")

# ═══════════════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 3: Gameplay Scene - Initial State")
print("=" * 60)
game.scene_mgr.switch(GameplayScene(game))
tick(game, 5)
gp = game.scene_mgr.current

# Check sun
sun = gp._sun_mgr.sun_count
print(f"  Initial sun count: {sun}")
if sun <= 0:
    report("GAMEPLAY", f"Initial sun is {sun}, should be > 0")

# Check cards
print(f"  Cards: {len(gp._cards)}")
for i, c in enumerate(gp._cards):
    print(f"    Card {i}: {c.name} cost={c.cost} rect={c.rect} can_plant={c.can_plant(sun)}")
    if c.rect.right > 800 or c.rect.bottom > 600:
        report("CARDS", f"Card {c.name} out of screen: {c.rect}")
    if c.rect.width < 5:
        report("CARDS", f"Card {c.name} too narrow: {c.rect.width}")

# Check grid
print(f"  Grid: x_start={GRID_X_START} y_start={GRID_Y_START} cell={CELL_WIDTH}x{CELL_HEIGHT}")
grid_right = GRID_X_START + GRID_COLS * CELL_WIDTH
grid_bottom = GRID_Y_START + GRID_ROWS * CELL_HEIGHT
print(f"  Grid area: ({GRID_X_START},{GRID_Y_START}) to ({grid_right},{grid_bottom})")
if grid_right > 800:
    report("GRID", f"Grid extends past screen right: {grid_right}")
if grid_bottom > 600:
    report("GRID", f"Grid extends past screen bottom: {grid_bottom}")

# ═══════════════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 4: Sun Collection")
print("=" * 60)
# Fast forward to get a sky sun
tick(game, 60 * 12)  # ~12 seconds
suns = gp._sun_mgr._suns
print(f"  Suns on screen after 12s: {len(suns)}")
if not suns:
    report("SUN", "No suns appeared after 12 seconds! Check spawn timer")
else:
    for s in suns:
        print(f"    Sun at ({s.x:.0f}, {s.y:.0f}) falling={s.falling} collecting={s.collecting}")

# Try clicking a sun
sun_before = gp._sun_mgr.sun_count
if suns:
    s = suns[0]
    inject_click(game, (int(s.x), int(s.y)))
    tick(game, 60)  # let it fly
    sun_after = gp._sun_mgr.sun_count
    print(f"  Sun before click: {sun_before}, after: {sun_after}")
    if sun_after <= sun_before:
        report("SUN", "Clicking sun didn't increase sun count!")

# ═══════════════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 5: Plant Placement via Drag")
print("=" * 60)
# Make sure we have enough sun
gp._sun_mgr.sun_count = 500

# Find a card that we can plant
plantable = [c for c in gp._cards if c.can_plant(500)]
print(f"  Plantable cards: {[c.name for c in plantable]}")

if plantable:
    card = plantable[0]
    # Drag from card to grid center (row 2, col 4)
    target_row, target_col = 2, 4
    target_px = LawnGrid.cell_to_pixel(target_row, target_col)
    print(f"  Dragging {card.name} from {card.rect.center} to grid ({target_row},{target_col}) px={target_px}")
    
    plants_before = len(gp._plant_mgr.plants)
    inject_drag(game, card.rect.center, target_px)
    tick(game, 5)
    plants_after = len(gp._plant_mgr.plants)
    print(f"  Plants before: {plants_before}, after: {plants_after}")
    
    if plants_after <= plants_before:
        report("PLANT", "Drag to plant didn't create a plant!")
    else:
        p = gp._plant_mgr.plants[-1]
        print(f"  Placed: {p.name} at row={p.row} col={p.col} alive={p.alive}")
        print(f"  Plant sprite rect: {p.sprite.rect}")
        if p.sprite.rect.width < 5 or p.sprite.rect.height < 5:
            report("PLANT", f"Plant sprite too small: {p.sprite.rect.size}")
else:
    report("PLANT", "No plantable cards!")

# ═══════════════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 6: Wave System & Zombie Spawning")
print("=" * 60)
ws = gp._wave_sys
print(f"  Total waves: {ws.total_waves}")
print(f"  Current wave: {ws.current_wave_index}")
print(f"  All done: {ws.all_waves_done}")
print(f"  Available plants: {ws.available_plants}")

# Fast forward to first wave
print(f"  Fast forwarding to first wave spawn...")
for i in range(60 * 35):  # ~35 seconds
    gp._wave_sys.update(1/60)
    gp._zombie_mgr.update(1/60, gp._plant_mgr)

zombies = gp._zombie_mgr.all_alive()
print(f"  Zombies alive after 35s: {len(zombies)}")
if not zombies:
    report("WAVE", "No zombies spawned after 35 seconds!")
else:
    for z in zombies:
        print(f"    Zombie type={type(z).__name__} row={z.row} x={z.x:.0f} hp={z.hp} state={z.state}")

# ═══════════════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 7: Combat - Bullet hits Zombie")
print("=" * 60)
# Place a peashooter in row with zombie
if zombies:
    z = zombies[0]
    from src.entities.plant import Peashooter
    ps = Peashooter(z.row, 1)
    gp._plant_mgr.add(ps)
    print(f"  Placed Peashooter at row={z.row} col=1")
    
    # Run 120 frames (~2s) to let it shoot
    bullets_before = len(gp._bullet_mgr.bullets)
    for i in range(120):
        tick(game, 1)
    bullets_after = len(gp._bullet_mgr.bullets)
    print(f"  Bullets on screen: before={bullets_before} after={bullets_after}")
    total_bullets_ever = bullets_after  # some may have already hit
    if bullets_after == 0 and bullets_before == 0:
        report("COMBAT", "Peashooter didn't fire any bullets in 2 seconds!")

# ═══════════════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("TEST 8: Lawn Mower / House reached detection")
print("=" * 60)
house_check = gp._zombie_mgr.any_reached_house()
print(f"  Any zombie reached house: {house_check}")

# ═══════════════════════════════════════════════════════════════════════
print()
print("=" * 60)
print("SUMMARY")
print("=" * 60)
if issues:
    print(f"\n  Found {len(issues)} issues:")
    for issue in issues:
        print(f"    ❌ {issue}")
else:
    print("  ✅ All tests passed — no issues found!")

pygame.quit()
