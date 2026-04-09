"""Zombie entities — NormalZombie, ConeheadZombie, BucketheadZombie, FlagZombie."""

from __future__ import annotations

from enum import Enum, auto
from typing import TYPE_CHECKING

import pygame

from src.engine.sprite import AnimatedSprite
from src.engine.resource import ResourceManager
from src.systems.grid import LawnGrid
from src.config import (
    CELL_WIDTH, CELL_HEIGHT,
    GRID_X_START, GRID_Y_START,
    GRID_COLS, SCREEN_WIDTH,
)

if TYPE_CHECKING:
    from src.entities.plant import Plant


class ZombieState(Enum):
    WALK = auto()
    ATTACK = auto()
    LOST_HEAD = auto()
    LOST_HEAD_ATTACK = auto()
    DIE = auto()
    DEAD = auto()


class Zombie:
    """Base zombie that walks left, attacks plants, and eventually dies.

    Attributes
    ----------
    row : int              – lawn row (0-4)
    x : float              – pixel x position (centre)
    y : float              – pixel y position (centre)
    hp : int               – current hit-points (body only, excludes armour)
    armour_hp : int        – armour (cone/bucket) HP; 0 for normals
    speed : float          – grid-cells per second
    attack_dps : float     – damage per second to plants
    state : ZombieState
    alive : bool
    """

    BODY_HP = 200
    ARMOUR_HP = 0
    SPEED = 0.5  # cells/sec
    ATTACK_DPS = 100.0
    LOST_HEAD_THRESHOLD = 70  # body hp below this → lose head

    # Subclasses set this to the folder prefix under resources/Zombies/
    RESOURCE_ROOT = "Zombies/NormalZombie"
    # Animation sub-folder names (relative to RESOURCE_ROOT)
    ANIM_WALK = "Zombie"
    ANIM_ATTACK = "ZombieAttack"
    ANIM_LOST_HEAD = "ZombieLostHead"
    ANIM_LOST_HEAD_ATTACK = "ZombieLostHeadAttack"
    ANIM_DIE = "ZombieDie"
    ANIM_HEAD = "ZombieHead"
    ANIM_BOOM_DIE = "BoomDie"

    def __init__(self, row: int, col_offset: float = 0.0):
        self.row = row
        self.hp: int = self.BODY_HP
        self.armour_hp: int = self.ARMOUR_HP
        self.speed: float = self.SPEED
        self.attack_dps: float = self.ATTACK_DPS
        self.alive: bool = True
        self.state: ZombieState = ZombieState.WALK
        self._target_plant: Plant | None = None

        # pixel position: start off-screen right
        start_col = GRID_COLS + 0.5 + col_offset
        cx, cy = LawnGrid.cell_to_pixel(row, 0)
        self.x: float = float(GRID_X_START + start_col * CELL_WIDTH + CELL_WIDTH // 2)
        self.y: float = float(cy)

        # load animations
        rm = ResourceManager()
        self._anims: dict[str, AnimatedSprite] = {}
        self._load_anims(rm)
        self._current_anim_key: str = self.ANIM_WALK
        self.sprite: AnimatedSprite = self._anims[self.ANIM_WALK]
        self.sprite.rect.center = (int(self.x), int(self.y))
        self.rect: pygame.Rect = self.sprite.rect

        # dying flag to play death anim before removal
        self._dying_timer: float = 0.0

    def _load_anims(self, rm: ResourceManager):
        """Load all animation sets for this zombie type."""
        for key in (
            self.ANIM_WALK,
            self.ANIM_ATTACK,
            self.ANIM_LOST_HEAD,
            self.ANIM_LOST_HEAD_ATTACK,
            self.ANIM_DIE,
        ):
            folder = f"{self.RESOURCE_ROOT}/{key}"
            try:
                frames = rm.load_sequence(folder)
                loop = key not in (self.ANIM_DIE,)
                self._anims[key] = AnimatedSprite(frames, fps=12, loop=loop, position=(0, 0))
            except FileNotFoundError:
                pass  # some zombie types don't have every anim

    def _switch_anim(self, key: str):
        if key == self._current_anim_key:
            return
        if key not in self._anims:
            return
        self._current_anim_key = key
        old_center = self.sprite.rect.center
        self.sprite = self._anims[key]
        self.sprite.reset()
        self.sprite.rect.center = old_center

    # ── total HP helpers ──────────────────────────────────────────────

    @property
    def total_hp(self) -> int:
        return self.hp + self.armour_hp

    def take_damage(self, amount: int):
        """Apply damage: armour absorbs first, then body."""
        if self.armour_hp > 0:
            absorbed = min(self.armour_hp, amount)
            self.armour_hp -= absorbed
            amount -= absorbed
            if self.armour_hp <= 0:
                self._on_armour_break()
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self._start_dying()
        elif self.hp < self.LOST_HEAD_THRESHOLD and self.state not in (
            ZombieState.LOST_HEAD,
            ZombieState.LOST_HEAD_ATTACK,
            ZombieState.DIE,
            ZombieState.DEAD,
        ):
            self._lose_head()

    def _on_armour_break(self):
        """Called when armour HP reaches 0. Subclasses can switch to normal walk anim."""
        pass

    def _lose_head(self):
        if self._target_plant and self._target_plant.alive:
            self.state = ZombieState.LOST_HEAD_ATTACK
            self._switch_anim(self.ANIM_LOST_HEAD_ATTACK)
        else:
            self.state = ZombieState.LOST_HEAD
            self._switch_anim(self.ANIM_LOST_HEAD)

    def _start_dying(self):
        self.state = ZombieState.DIE
        self._switch_anim(self.ANIM_DIE)
        self._dying_timer = 1.5  # seconds for death animation
        self._target_plant = None

    # ── update ────────────────────────────────────────────────────────

    def update(self, dt: float, plants_in_row: list[Plant] | None = None):
        if not self.alive:
            return

        self.sprite.update(dt)

        if self.state == ZombieState.DIE:
            self._dying_timer -= dt
            if self._dying_timer <= 0 or self.sprite.finished:
                self.state = ZombieState.DEAD
                self.alive = False
            self._sync_position()
            return

        if self.state == ZombieState.DEAD:
            self.alive = False
            return

        plants = plants_in_row or []

        # Check if we should be attacking
        if self.state in (ZombieState.WALK, ZombieState.LOST_HEAD):
            target = self._find_plant_to_attack(plants)
            if target is not None:
                self._target_plant = target
                if self.state == ZombieState.LOST_HEAD:
                    self.state = ZombieState.LOST_HEAD_ATTACK
                    self._switch_anim(self.ANIM_LOST_HEAD_ATTACK)
                else:
                    self.state = ZombieState.ATTACK
                    self._switch_anim(self.ANIM_ATTACK)

        # Attack logic
        if self.state in (ZombieState.ATTACK, ZombieState.LOST_HEAD_ATTACK):
            if self._target_plant is None or not self._target_plant.alive:
                self._target_plant = self._find_plant_to_attack(plants)
                if self._target_plant is None:
                    # resume walking
                    if self.state == ZombieState.LOST_HEAD_ATTACK:
                        self.state = ZombieState.LOST_HEAD
                        self._switch_anim(self.ANIM_LOST_HEAD)
                    else:
                        self.state = ZombieState.WALK
                        self._switch_anim(self.ANIM_WALK)
            else:
                # deal damage
                self._target_plant.take_damage(self.attack_dps * dt)

        # Move
        if self.state in (ZombieState.WALK, ZombieState.LOST_HEAD):
            self.x -= self.speed * CELL_WIDTH * dt
            # Speed up lost head zombies slightly
            if self.state == ZombieState.LOST_HEAD:
                self.x -= 0.2 * CELL_WIDTH * dt

        self._sync_position()

    def _sync_position(self):
        self.sprite.rect.center = (int(self.x), int(self.y))
        self.rect = self.sprite.rect

    def _find_plant_to_attack(self, plants: list[Plant]) -> Plant | None:
        """Return the closest plant that this zombie has reached (overlaps)."""
        my_left = self.x - 20  # zombie's "mouth" area
        for p in plants:
            if not p.alive:
                continue
            plant_right = p.sprite.rect.right
            plant_left = p.sprite.rect.left
            if my_left <= plant_right and self.x >= plant_left:
                return p
        return None

    def draw(self, surface: pygame.Surface):
        if self.alive:
            surface.blit(self.sprite.image, self.sprite.rect)

    def kill(self):
        self.alive = False

    @property
    def reached_house(self) -> bool:
        """True if zombie walked past the left edge of the lawn."""
        return self.x < GRID_X_START - 30


# ═══════════════════════════════════════════════════════════════════════
# ConeheadZombie
# ═══════════════════════════════════════════════════════════════════════

class ConeheadZombie(Zombie):
    BODY_HP = 200
    ARMOUR_HP = 370
    RESOURCE_ROOT = "Zombies/ConeheadZombie"
    ANIM_WALK = "ConeheadZombie"
    ANIM_ATTACK = "ConeheadZombieAttack"
    # Use normal zombie anims when cone breaks
    ANIM_LOST_HEAD = "ZombieLostHead"
    ANIM_LOST_HEAD_ATTACK = "ZombieLostHeadAttack"
    ANIM_DIE = "ZombieDie"

    def _load_anims(self, rm: ResourceManager):
        """Load cone-specific anims + fallback normal-zombie anims."""
        # Cone anims
        for key in (self.ANIM_WALK, self.ANIM_ATTACK):
            folder = f"{self.RESOURCE_ROOT}/{key}"
            try:
                frames = rm.load_sequence(folder)
                self._anims[key] = AnimatedSprite(frames, fps=12, loop=True, position=(0, 0))
            except FileNotFoundError:
                pass
        # Normal zombie fallback anims for when cone breaks
        normal_root = "Zombies/NormalZombie"
        for key in ("Zombie", "ZombieAttack", "ZombieLostHead", "ZombieLostHeadAttack", "ZombieDie"):
            folder = f"{normal_root}/{key}"
            try:
                frames = rm.load_sequence(folder)
                loop = key != "ZombieDie"
                self._anims[key] = AnimatedSprite(frames, fps=12, loop=loop, position=(0, 0))
            except FileNotFoundError:
                pass

    def _on_armour_break(self):
        """Cone broken → switch to normal zombie walk animation."""
        if self.state in (ZombieState.WALK,):
            self._current_anim_key = ""  # force switch
            self._switch_anim("Zombie")
        elif self.state in (ZombieState.ATTACK,):
            self._current_anim_key = ""
            self._switch_anim("ZombieAttack")
        # Update anim keys to normal zombie keys
        self.ANIM_WALK = "Zombie"
        self.ANIM_ATTACK = "ZombieAttack"


# ═══════════════════════════════════════════════════════════════════════
# BucketheadZombie
# ═══════════════════════════════════════════════════════════════════════

class BucketheadZombie(Zombie):
    BODY_HP = 200
    ARMOUR_HP = 1100
    RESOURCE_ROOT = "Zombies/BucketheadZombie"
    ANIM_WALK = "BucketheadZombie"
    ANIM_ATTACK = "BucketheadZombieAttack"
    ANIM_LOST_HEAD = "ZombieLostHead"
    ANIM_LOST_HEAD_ATTACK = "ZombieLostHeadAttack"
    ANIM_DIE = "ZombieDie"

    def _load_anims(self, rm: ResourceManager):
        """Load bucket-specific anims + fallback normal-zombie anims."""
        for key in (self.ANIM_WALK, self.ANIM_ATTACK):
            folder = f"{self.RESOURCE_ROOT}/{key}"
            try:
                frames = rm.load_sequence(folder)
                self._anims[key] = AnimatedSprite(frames, fps=12, loop=True, position=(0, 0))
            except FileNotFoundError:
                pass
        normal_root = "Zombies/NormalZombie"
        for key in ("Zombie", "ZombieAttack", "ZombieLostHead", "ZombieLostHeadAttack", "ZombieDie"):
            folder = f"{normal_root}/{key}"
            try:
                frames = rm.load_sequence(folder)
                loop = key != "ZombieDie"
                self._anims[key] = AnimatedSprite(frames, fps=12, loop=loop, position=(0, 0))
            except FileNotFoundError:
                pass

    def _on_armour_break(self):
        if self.state in (ZombieState.WALK,):
            self._current_anim_key = ""
            self._switch_anim("Zombie")
        elif self.state in (ZombieState.ATTACK,):
            self._current_anim_key = ""
            self._switch_anim("ZombieAttack")
        self.ANIM_WALK = "Zombie"
        self.ANIM_ATTACK = "ZombieAttack"


# ═══════════════════════════════════════════════════════════════════════
# FlagZombie
# ═══════════════════════════════════════════════════════════════════════

class FlagZombie(Zombie):
    """Flag zombie — slightly faster normal zombie that signals a huge wave."""
    BODY_HP = 200
    ARMOUR_HP = 0
    SPEED = 0.7  # faster than normal
    RESOURCE_ROOT = "Zombies/FlagZombie"
    ANIM_WALK = "FlagZombie"
    ANIM_ATTACK = "FlagZombieAttack"
    ANIM_LOST_HEAD = "FlagZombieLostHead"
    ANIM_LOST_HEAD_ATTACK = "FlagZombieLostHeadAttack"
    ANIM_DIE = "ZombieDie"

    def _load_anims(self, rm: ResourceManager):
        for key in (self.ANIM_WALK, self.ANIM_ATTACK, self.ANIM_LOST_HEAD, self.ANIM_LOST_HEAD_ATTACK):
            folder = f"{self.RESOURCE_ROOT}/{key}"
            try:
                frames = rm.load_sequence(folder)
                self._anims[key] = AnimatedSprite(frames, fps=12, loop=True, position=(0, 0))
            except FileNotFoundError:
                pass
        # die anim from normal zombie
        try:
            frames = rm.load_sequence("Zombies/NormalZombie/ZombieDie")
            self._anims["ZombieDie"] = AnimatedSprite(frames, fps=12, loop=False, position=(0, 0))
        except FileNotFoundError:
            pass


# ═══════════════════════════════════════════════════════════════════════
# ZombieManager
# ═══════════════════════════════════════════════════════════════════════

class ZombieManager:
    """Manages all active zombies."""

    def __init__(self):
        self.zombies: list[Zombie] = []

    def add(self, zombie: Zombie):
        self.zombies.append(zombie)

    def get_by_row(self, row: int) -> list[Zombie]:
        return [z for z in self.zombies if z.row == row and z.alive]

    def all_alive(self) -> list[Zombie]:
        return [z for z in self.zombies if z.alive]

    def update(self, dt: float, plant_mgr):
        for z in self.zombies:
            if z.alive:
                plants_in_row = plant_mgr.get_by_row(z.row)
                z.update(dt, plants_in_row=plants_in_row)
        # Reap dead zombies
        self.zombies = [z for z in self.zombies if z.alive]

    def draw(self, surface: pygame.Surface):
        # Draw back-to-front (higher y first would be wrong; sort by x descending for depth)
        for z in sorted(self.zombies, key=lambda z: z.y):
            z.draw(surface)

    def any_reached_house(self) -> bool:
        return any(z.reached_house for z in self.zombies if z.alive)

    def clear(self):
        self.zombies.clear()

    @property
    def total_spawned_alive(self) -> int:
        return len([z for z in self.zombies if z.alive])


def create_zombie(zombie_type: str, row: int, col_offset: float = 0.0) -> Zombie:
    """Factory function to create a zombie by type string."""
    _MAP = {
        "Normal": Zombie,
        "NormalZombie": Zombie,
        "Conehead": ConeheadZombie,
        "ConeheadZombie": ConeheadZombie,
        "Buckethead": BucketheadZombie,
        "BucketheadZombie": BucketheadZombie,
        "Flag": FlagZombie,
        "FlagZombie": FlagZombie,
    }
    cls = _MAP.get(zombie_type)
    if cls is None:
        raise ValueError(f"Unknown zombie type: {zombie_type}")
    return cls(row, col_offset)
