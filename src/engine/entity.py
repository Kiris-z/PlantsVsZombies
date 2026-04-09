"""Entity and EntityManager — lightweight game-object layer."""

from __future__ import annotations
import pygame
from src.engine.sprite import AnimatedSprite


class Entity:
    """Base game entity that wraps an :class:`AnimatedSprite`.

    Attributes
    ----------
    name : str        – e.g. ``"Peashooter"``
    row : int         – grid row (0-4), or -1 for non-grid entities
    col : int         – grid column (0-8), or -1
    hp : int          – hit-points
    sprite : AnimatedSprite
    alive : bool
    """

    def __init__(
        self,
        name: str,
        sprite: AnimatedSprite,
        row: int = -1,
        col: int = -1,
        hp: int = 300,
    ):
        self.name = name
        self.sprite = sprite
        self.row = row
        self.col = col
        self.hp = hp
        self.alive = True

    def update(self, dt: float):
        if self.alive:
            self.sprite.update(dt)

    def draw(self, surface: pygame.Surface):
        if self.alive:
            surface.blit(self.sprite.image, self.sprite.rect)

    def kill(self):
        self.alive = False
        self.sprite.kill()


class EntityManager:
    """Maintains a flat list of :class:`Entity` objects with row-based queries."""

    def __init__(self):
        self._entities: list[Entity] = []

    def add(self, entity: Entity):
        self._entities.append(entity)

    def remove(self, entity: Entity):
        entity.kill()
        self._entities.remove(entity)

    def get_by_row(self, row: int) -> list[Entity]:
        return [e for e in self._entities if e.row == row and e.alive]

    def get_at(self, row: int, col: int) -> Entity | None:
        for e in self._entities:
            if e.row == row and e.col == col and e.alive:
                return e
        return None

    def all(self) -> list[Entity]:
        return [e for e in self._entities if e.alive]

    def update(self, dt: float):
        for e in list(self._entities):
            if e.alive:
                e.update(dt)
            else:
                self._entities.remove(e)

    def draw(self, surface: pygame.Surface):
        for e in self._entities:
            if e.alive:
                e.draw(surface)

    def clear(self):
        for e in self._entities:
            e.kill()
        self._entities.clear()
