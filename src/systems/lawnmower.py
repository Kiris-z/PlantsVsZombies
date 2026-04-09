"""Lawn mower — last line of defense. One per row, triggers when a zombie reaches it."""

from __future__ import annotations

import pygame
from src.engine.resource import ResourceManager
from src.systems.grid import LawnGrid
from src.config import GRID_ROWS, GRID_X_START, CELL_WIDTH, CELL_HEIGHT, SCREEN_WIDTH


class LawnMower:
    """A single lawn mower that sits at the left of a row.
    
    When a zombie reaches it, it activates and drives rightward,
    killing all zombies in the row.
    """

    SPEED = 400  # pixels per second when activated

    def __init__(self, row: int):
        self.row = row
        self.alive = True
        self.activated = False
        
        rm = ResourceManager()
        self.image = rm.load_image("Screen/car.png")
        
        # Position at the left of the row
        _, cy = LawnGrid.cell_to_pixel(row, 0)
        self.x = float(GRID_X_START - 30)
        self.y = float(cy)
        self.rect = self.image.get_rect(center=(int(self.x), int(self.y)))

    def activate(self):
        """Start the mower driving rightward."""
        if not self.alive or self.activated:
            return
        self.activated = True

    def update(self, dt: float, zombie_mgr=None):
        if not self.alive:
            return
        if not self.activated:
            return
            
        # Drive rightward
        self.x += self.SPEED * dt
        self.rect.center = (int(self.x), int(self.y))
        
        # Kill all zombies we touch
        if zombie_mgr:
            for z in zombie_mgr.get_by_row(self.row):
                if z.alive and abs(z.x - self.x) < 60:
                    z.take_damage(9999)
        
        # Off screen? Remove
        if self.x > SCREEN_WIDTH + 50:
            self.alive = False

    def draw(self, surface: pygame.Surface):
        if self.alive:
            surface.blit(self.image, self.rect)


class LawnMowerManager:
    """Manages lawn mowers for all 5 rows."""

    def __init__(self):
        self.mowers: list[LawnMower] = []
        for row in range(GRID_ROWS):
            self.mowers.append(LawnMower(row))

    def check_zombie_reach(self, zombie_mgr) -> bool:
        """Check if any zombie has reached the mower line. 
        
        Returns True if a zombie reached the house (mower already used).
        """
        for mower in self.mowers:
            if not mower.alive:
                continue
            if mower.activated:
                continue
            # Check if any zombie in this row has reached the mower
            for z in zombie_mgr.get_by_row(mower.row):
                if z.alive and z.x <= GRID_X_START:
                    mower.activate()
                    break
        
        # Check for actual game over: zombie past the mower line AND no mower available
        for z in zombie_mgr.all_alive():
            if z.x < GRID_X_START - 60:
                # Is there a mower for this row?
                row_mower = None
                for m in self.mowers:
                    if m.row == z.row:
                        row_mower = m
                        break
                if row_mower is None or not row_mower.alive:
                    return True  # Game over!
        return False

    def update(self, dt: float, zombie_mgr=None):
        for mower in self.mowers:
            mower.update(dt, zombie_mgr)

    def draw(self, surface: pygame.Surface):
        for mower in self.mowers:
            mower.draw(surface)
