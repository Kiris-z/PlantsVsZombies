"""Bullet entities — projectiles fired by plants."""

from __future__ import annotations

import pygame
from src.engine.sprite import AnimatedSprite
from src.engine.resource import ResourceManager
from src.systems.grid import LawnGrid
from src.config import CELL_WIDTH, SCREEN_WIDTH


class PeaBullet:
    """A pea projectile that travels rightward along a row.

    Attributes
    ----------
    row : int        – grid row (0-4)
    x, y : float     – pixel position
    damage : int     – HP removed on hit
    alive : bool
    """

    SPEED = 3.5  # grid cells per second
    DAMAGE = 20

    def __init__(self, row: int, x: float, y: float):
        self.row = row
        self.x = x
        self.y = y
        self.damage = self.DAMAGE
        self.alive = True

        rm = ResourceManager()
        frames = rm.load_sequence("Bullets/PeaNormal")
        # PeaNormal has only 1 frame; that's fine
        self.sprite = AnimatedSprite(frames, fps=1, loop=True, position=(int(x), int(y)))
        self.rect = self.sprite.rect

    def update(self, dt: float):
        if not self.alive:
            return
        self.x += self.SPEED * CELL_WIDTH * dt
        self.sprite.rect.centerx = int(self.x)
        self.sprite.rect.centery = int(self.y)
        self.rect = self.sprite.rect
        # remove when off-screen
        if self.x > SCREEN_WIDTH + 50:
            self.alive = False

    def draw(self, surface: pygame.Surface):
        if self.alive:
            surface.blit(self.sprite.image, self.sprite.rect)

    def kill(self):
        self.alive = False


class PeaExplode:
    """One-shot pea explosion animation played at the hit position."""

    def __init__(self, x: float, y: float):
        rm = ResourceManager()
        frames = rm.load_sequence("Bullets/PeaNormalExplode")
        # If only 1 frame, duplicate for a short flash
        if len(frames) == 1:
            frames = frames * 3
        self.sprite = AnimatedSprite(frames, fps=12, loop=False, position=(int(x), int(y)))
        self.alive = True

    def update(self, dt: float):
        if not self.alive:
            return
        self.sprite.update(dt)
        if self.sprite.finished:
            self.alive = False

    def draw(self, surface: pygame.Surface):
        if self.alive:
            surface.blit(self.sprite.image, self.sprite.rect)


class BulletManager:
    """Manages all active bullets and explosion effects."""

    def __init__(self):
        self.bullets: list[PeaBullet] = []
        self._effects: list[PeaExplode] = []

    def add(self, bullet: PeaBullet):
        self.bullets.append(bullet)

    def spawn_explosion(self, x: float, y: float):
        self._effects.append(PeaExplode(x, y))

    def update(self, dt: float):
        for b in self.bullets:
            b.update(dt)
        self.bullets = [b for b in self.bullets if b.alive]

        for e in self._effects:
            e.update(dt)
        self._effects = [e for e in self._effects if e.alive]

    def draw(self, surface: pygame.Surface):
        for b in self.bullets:
            b.draw(surface)
        for e in self._effects:
            e.draw(surface)

    def get_by_row(self, row: int) -> list[PeaBullet]:
        return [b for b in self.bullets if b.row == row and b.alive]

    def clear(self):
        self.bullets.clear()
        self._effects.clear()
