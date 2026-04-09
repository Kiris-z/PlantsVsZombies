"""Plant entities — Peashooter, SunFlower, WallNut."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from src.engine.sprite import AnimatedSprite
from src.engine.resource import ResourceManager
from src.systems.grid import LawnGrid
from src.config import PLANT_DEFS, CELL_WIDTH

if TYPE_CHECKING:
    from src.entities.bullet import BulletManager


class Plant:
    """Base plant placed on the lawn grid.

    Subclasses override :meth:`plant_update` for behaviour (shooting, producing sun, etc.).
    """

    def __init__(self, name: str, row: int, col: int):
        self.name = name
        self.row = row
        self.col = col
        pdef = PLANT_DEFS[name]
        self.hp: int = pdef["hp"]
        self.max_hp: int = pdef["hp"]
        self.alive: bool = True

        rm = ResourceManager()
        frames = rm.load_sequence(pdef["anim_folder"])
        cx, cy = LawnGrid.cell_to_pixel(row, col)
        self.sprite = AnimatedSprite(frames, fps=pdef["anim_fps"], loop=True, position=(cx, cy))
        self.rect: pygame.Rect = self.sprite.rect

    def update(self, dt: float, **kwargs):
        if not self.alive:
            return
        self.sprite.update(dt)
        self.rect = self.sprite.rect
        self.plant_update(dt, **kwargs)

    def plant_update(self, dt: float, **kwargs):
        """Override in subclasses for per-frame logic."""

    def draw(self, surface: pygame.Surface):
        if self.alive:
            surface.blit(self.sprite.image, self.sprite.rect)

    def take_damage(self, amount: float):
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False

    def kill(self):
        self.alive = False


# ═══════════════════════════════════════════════════════════════════════
# Peashooter
# ═══════════════════════════════════════════════════════════════════════

class Peashooter(Plant):
    """Fires a pea every 1.4 s if there is at least one zombie in the same row."""

    SHOOT_INTERVAL = 1.4  # seconds

    def __init__(self, row: int, col: int):
        super().__init__("Peashooter", row, col)
        self._shoot_timer: float = self.SHOOT_INTERVAL  # first shot after full interval

    def plant_update(self, dt: float, **kwargs):
        bullet_mgr: BulletManager | None = kwargs.get("bullet_mgr")
        zombies_in_row: bool = kwargs.get("zombies_in_row", False)

        if not zombies_in_row or bullet_mgr is None:
            # reset timer so first shot has full delay when zombie appears
            return

        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = self.SHOOT_INTERVAL
            self._fire(bullet_mgr)

    def _fire(self, bullet_mgr: BulletManager):
        from src.entities.bullet import PeaBullet
        # Spawn bullet slightly right of plant centre
        bx = float(self.sprite.rect.centerx + 20)
        by = float(self.sprite.rect.centery - 10)
        bullet_mgr.add(PeaBullet(self.row, bx, by))


# ═══════════════════════════════════════════════════════════════════════
# SunFlower
# ═══════════════════════════════════════════════════════════════════════

class SunFlower(Plant):
    """Produces 25 sun every 24 s."""

    SUN_INTERVAL = 24.0

    def __init__(self, row: int, col: int):
        super().__init__("SunFlower", row, col)
        # first sun comes sooner (like the real game, ~7-12 s after planting)
        self._sun_timer: float = 12.0

    def plant_update(self, dt: float, **kwargs):
        sun_mgr = kwargs.get("sun_mgr")
        if sun_mgr is None:
            return
        self._sun_timer -= dt
        if self._sun_timer <= 0:
            self._sun_timer = self.SUN_INTERVAL
            self._produce_sun(sun_mgr)

    def _produce_sun(self, sun_mgr):
        """Spawn a collectible sun at this plant's position."""
        from src.systems.economy import Sun
        from src.engine.sprite import AnimatedSprite
        from src.engine.resource import ResourceManager

        rm = ResourceManager()
        frames = rm.load_sequence("Plants/Sun")
        x = float(self.sprite.rect.centerx)
        y = float(self.sprite.rect.centery)
        y_target = y + 40  # drift slightly below
        anim = AnimatedSprite(frames, fps=10, loop=True, position=(int(x), int(y)))
        sun = Sun(x, y, y_target, anim)
        sun.falling = True
        sun_mgr._suns.append(sun)


# ═══════════════════════════════════════════════════════════════════════
# WallNut
# ═══════════════════════════════════════════════════════════════════════

class WallNut(Plant):
    """High-HP wall with three visual damage stages."""

    STAGE_THRESHOLDS = (2.0 / 3.0, 1.0 / 3.0)  # fraction of max_hp

    def __init__(self, row: int, col: int):
        super().__init__("WallNut", row, col)
        self._stage: int = 0  # 0=healthy, 1=cracked1, 2=cracked2
        rm = ResourceManager()
        cx, cy = LawnGrid.cell_to_pixel(row, col)
        self._stage_sprites: list[AnimatedSprite] = [
            self.sprite,  # stage 0 — already created by super()
            AnimatedSprite(
                rm.load_sequence("Plants/WallNut/WallNut_cracked1"),
                fps=12, loop=True, position=(cx, cy),
            ),
            AnimatedSprite(
                rm.load_sequence("Plants/WallNut/WallNut_cracked2"),
                fps=12, loop=True, position=(cx, cy),
            ),
        ]

    def plant_update(self, dt: float, **kwargs):
        frac = self.hp / self.max_hp
        if frac <= self.STAGE_THRESHOLDS[1] and self._stage < 2:
            self._switch_stage(2)
        elif frac <= self.STAGE_THRESHOLDS[0] and self._stage < 1:
            self._switch_stage(1)

    def _switch_stage(self, stage: int):
        self._stage = stage
        new_sprite = self._stage_sprites[stage]
        # preserve position
        new_sprite.rect.center = self.sprite.rect.center
        self.sprite = new_sprite
        self.rect = self.sprite.rect


# ═══════════════════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════════════════

def create_plant(name: str, row: int, col: int) -> Plant:
    """Factory function to create a plant by name."""
    _MAP = {
        "Peashooter": Peashooter,
        "SunFlower": SunFlower,
        "WallNut": WallNut,
    }
    cls = _MAP.get(name)
    if cls is None:
        raise ValueError(f"Unknown plant type: {name}")
    return cls(row, col)


class PlantManager:
    """Manages all living plants on the lawn."""

    def __init__(self):
        self.plants: list[Plant] = []

    def add(self, plant: Plant):
        self.plants.append(plant)

    def get_at(self, row: int, col: int) -> Plant | None:
        for p in self.plants:
            if p.row == row and p.col == col and p.alive:
                return p
        return None

    def get_by_row(self, row: int) -> list[Plant]:
        return [p for p in self.plants if p.row == row and p.alive]

    def all_alive(self) -> list[Plant]:
        return [p for p in self.plants if p.alive]

    def update(self, dt: float, **kwargs):
        for p in self.plants:
            if p.alive:
                p.update(dt, **kwargs)
        # Remove dead plants
        self.plants = [p for p in self.plants if p.alive]

    def draw(self, surface: pygame.Surface):
        for p in self.plants:
            p.draw(surface)

    def clear(self):
        self.plants.clear()
