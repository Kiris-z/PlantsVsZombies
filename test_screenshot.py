#!/usr/bin/env python3
"""Screenshot test: captures gameplay screen after setup."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))

from src.engine.game import Game
from src.scenes.gameplay import GameplayScene
from src.systems.grid import LawnGrid
from src.entities.plant import Peashooter, SunFlower, WallNut

game = Game()
game.scene_mgr.switch(GameplayScene(game))

# Simulate entering gameplay
for i in range(5):
    for event in pygame.event.get():
        game.scene_mgr.handle_event(event)
    game.scene_mgr.update(1/60)
    game.scene_mgr.draw(screen)

gp = game.scene_mgr.current
gp._sun_mgr.sun_count = 999

# Place some plants
for col in range(5):
    sf = SunFlower(0, col)
    gp._plant_mgr.add(sf)
for col in range(5):
    ps = Peashooter(2, col)
    gp._plant_mgr.add(ps)
wn = WallNut(2, 7)
gp._plant_mgr.add(wn)

# Spawn some zombies
from src.entities.zombie import Zombie, ConeheadZombie
for r in [1, 2, 3]:
    z = Zombie(r)
    z.x = 650
    gp._zombie_mgr.add(z)
cz = ConeheadZombie(2)
cz.x = 700
gp._zombie_mgr.add(cz)

# Spawn a sun
gp._sun_mgr._spawn_sky_sun()

# Render a few frames
for i in range(30):
    for event in pygame.event.get():
        game.scene_mgr.handle_event(event)
    game.scene_mgr.update(1/60)
    game.scene_mgr.draw(screen)
    pygame.display.flip()

# Save screenshot
pygame.image.save(screen, "/Users/maosen/.openclaw/workspace/pvz_gameplay.png")
print("Screenshot saved to pvz_gameplay.png")
pygame.quit()
