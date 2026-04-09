"""Plant entities — Peashooter, SunFlower, WallNut, SnowPea, CherryBomb,
RepeaterPea, Chomper, PotatoMine, Spikeweed, Squash, Threepeater,
PuffShroom, ScaredyShroom, Jalapeno."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame

from src.engine.sprite import AnimatedSprite
from src.engine.resource import ResourceManager
from src.systems.grid import LawnGrid
from src.config import PLANT_DEFS, CELL_WIDTH, CELL_HEIGHT, GRID_ROWS, GRID_COLS, SCREEN_WIDTH

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

    @property
    def is_immune_to_eating(self) -> bool:
        """Return True if zombies cannot eat this plant (e.g. Spikeweed)."""
        return False

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
# SnowPea
# ═══════════════════════════════════════════════════════════════════════

class SnowPea(Plant):
    """Fires an ice pea every 1.4 s — 20 damage + 50% slow for 10 s."""

    SHOOT_INTERVAL = 1.4

    def __init__(self, row: int, col: int):
        super().__init__("SnowPea", row, col)
        self._shoot_timer: float = self.SHOOT_INTERVAL

    def plant_update(self, dt: float, **kwargs):
        bullet_mgr: BulletManager | None = kwargs.get("bullet_mgr")
        zombies_in_row: bool = kwargs.get("zombies_in_row", False)

        if not zombies_in_row or bullet_mgr is None:
            return

        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = self.SHOOT_INTERVAL
            self._fire(bullet_mgr)

    def _fire(self, bullet_mgr: BulletManager):
        from src.entities.bullet import IcePeaBullet
        bx = float(self.sprite.rect.centerx + 20)
        by = float(self.sprite.rect.centery - 10)
        bullet_mgr.add(IcePeaBullet(self.row, bx, by))


# ═══════════════════════════════════════════════════════════════════════
# CherryBomb
# ═══════════════════════════════════════════════════════════════════════

class CherryBomb(Plant):
    """Explodes in a 3×3 area for 1800 damage, one-shot plant.

    Plays the CherryBomb animation, then deals damage and removes itself.
    """

    EXPLOSION_DAMAGE = 1800
    FUSE_TIME = 1.0  # seconds before detonation (let anim play)

    def __init__(self, row: int, col: int):
        super().__init__("CherryBomb", row, col)
        self.sprite.loop = False  # one-shot animation
        self._fuse_timer: float = self.FUSE_TIME
        self._exploded: bool = False

    def plant_update(self, dt: float, **kwargs):
        zombie_mgr = kwargs.get("zombie_mgr")
        if self._exploded:
            return

        self._fuse_timer -= dt
        if self._fuse_timer <= 0 or self.sprite.finished:
            self._explode(zombie_mgr)

    def _explode(self, zombie_mgr):
        self._exploded = True
        if zombie_mgr is None:
            self.alive = False
            return

        # 3×3 area centred on this plant
        for dr in range(-1, 2):
            for dc in range(-1, 2):
                r = self.row + dr
                c = self.col + dc
                if 0 <= r < GRID_ROWS and 0 <= c < GRID_COLS:
                    for z in zombie_mgr.get_by_row(r):
                        # Check if zombie is within the column range (pixel based)
                        zcol_approx = (z.x - 35) / CELL_WIDTH
                        if c - 0.5 <= zcol_approx <= c + 1.5:
                            z.take_damage(self.EXPLOSION_DAMAGE)

        self.alive = False


# ═══════════════════════════════════════════════════════════════════════
# RepeaterPea
# ═══════════════════════════════════════════════════════════════════════

class RepeaterPea(Plant):
    """Fires two peas every 1.4 s (separated by 0.15 s)."""

    SHOOT_INTERVAL = 1.4
    BURST_DELAY = 0.15  # delay between the two peas in a burst

    def __init__(self, row: int, col: int):
        super().__init__("RepeaterPea", row, col)
        self._shoot_timer: float = self.SHOOT_INTERVAL
        self._burst_pending: bool = False
        self._burst_timer: float = 0.0

    def plant_update(self, dt: float, **kwargs):
        bullet_mgr: BulletManager | None = kwargs.get("bullet_mgr")
        zombies_in_row: bool = kwargs.get("zombies_in_row", False)

        # Handle pending second shot of burst
        if self._burst_pending and bullet_mgr is not None:
            self._burst_timer -= dt
            if self._burst_timer <= 0:
                self._fire(bullet_mgr)
                self._burst_pending = False

        if not zombies_in_row or bullet_mgr is None:
            return

        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = self.SHOOT_INTERVAL
            self._fire(bullet_mgr)
            # Queue second pea
            self._burst_pending = True
            self._burst_timer = self.BURST_DELAY

    def _fire(self, bullet_mgr: BulletManager):
        from src.entities.bullet import PeaBullet
        bx = float(self.sprite.rect.centerx + 20)
        by = float(self.sprite.rect.centery - 10)
        bullet_mgr.add(PeaBullet(self.row, bx, by))


# ═══════════════════════════════════════════════════════════════════════
# Chomper
# ═══════════════════════════════════════════════════════════════════════

class Chomper(Plant):
    """Instantly kills one zombie by swallowing it, then chews for 42 s.

    States: IDLE → ATTACK → DIGEST → IDLE
    """

    ATTACK_RANGE = CELL_WIDTH * 1.5  # pixels — how close a zombie must be
    DIGEST_TIME = 42.0

    def __init__(self, row: int, col: int):
        super().__init__("Chomper", row, col)
        self._state: str = "idle"  # idle / attack / digest
        self._digest_timer: float = 0.0
        self._attack_timer: float = 0.0

        rm = ResourceManager()
        cx, cy = LawnGrid.cell_to_pixel(row, col)
        self._anim_idle = self.sprite
        self._anim_attack = AnimatedSprite(
            rm.load_sequence("Plants/Chomper/ChomperAttack"),
            fps=14, loop=False, position=(cx, cy),
        )
        self._anim_digest = AnimatedSprite(
            rm.load_sequence("Plants/Chomper/ChomperDigest"),
            fps=12, loop=True, position=(cx, cy),
        )

    def plant_update(self, dt: float, **kwargs):
        zombie_mgr = kwargs.get("zombie_mgr")

        if self._state == "idle":
            if zombie_mgr is None:
                return
            # Look for a zombie in range
            zombies = zombie_mgr.get_by_row(self.row)
            for z in zombies:
                if z.alive and abs(z.x - self.sprite.rect.centerx) < self.ATTACK_RANGE:
                    # Chomp!
                    z.take_damage(z.total_hp + 9999)  # instant kill
                    self._switch_to("attack")
                    self._attack_timer = 0.7  # time to play attack anim
                    break

        elif self._state == "attack":
            self._attack_timer -= dt
            if self._attack_timer <= 0 or self._anim_attack.finished:
                self._switch_to("digest")
                self._digest_timer = self.DIGEST_TIME

        elif self._state == "digest":
            self._digest_timer -= dt
            if self._digest_timer <= 0:
                self._switch_to("idle")

    def _switch_to(self, state: str):
        self._state = state
        cx, cy = self.sprite.rect.center
        if state == "idle":
            self.sprite = self._anim_idle
            self._anim_idle.reset()
        elif state == "attack":
            self.sprite = self._anim_attack
            self._anim_attack.reset()
        elif state == "digest":
            self.sprite = self._anim_digest
            self._anim_digest.reset()
        self.sprite.rect.center = (cx, cy)
        self.rect = self.sprite.rect


# ═══════════════════════════════════════════════════════════════════════
# PotatoMine
# ═══════════════════════════════════════════════════════════════════════

class PotatoMine(Plant):
    """Underground for 14 s (init anim), then pops up. Explodes on contact for 1800 damage."""

    PREP_TIME = 14.0
    EXPLOSION_DAMAGE = 1800

    def __init__(self, row: int, col: int):
        super().__init__("PotatoMine", row, col)
        self._ready: bool = False
        self._prep_timer: float = self.PREP_TIME

        rm = ResourceManager()
        cx, cy = LawnGrid.cell_to_pixel(row, col)
        # Init sprite is already loaded by super() (PotatoMineInit)
        self._anim_init = self.sprite
        self._anim_ready = AnimatedSprite(
            rm.load_sequence("Plants/PotatoMine/PotatoMine"),
            fps=12, loop=True, position=(cx, cy),
        )
        # Explode is one-shot, but we just remove the plant
        try:
            self._anim_explode = AnimatedSprite(
                rm.load_sequence("Plants/PotatoMine/PotatoMineExplode"),
                fps=12, loop=False, position=(cx, cy),
            )
        except FileNotFoundError:
            self._anim_explode = None

    def plant_update(self, dt: float, **kwargs):
        zombie_mgr = kwargs.get("zombie_mgr")

        if not self._ready:
            self._prep_timer -= dt
            if self._prep_timer <= 0:
                self._ready = True
                cx, cy = self.sprite.rect.center
                self.sprite = self._anim_ready
                self.sprite.rect.center = (cx, cy)
                self.rect = self.sprite.rect
            return

        # Ready — check for zombie contact
        if zombie_mgr is None:
            return

        zombies = zombie_mgr.get_by_row(self.row)
        for z in zombies:
            if z.alive and abs(z.x - self.sprite.rect.centerx) < CELL_WIDTH * 0.7:
                # Explode!
                self._detonate(zombie_mgr)
                return

    def _detonate(self, zombie_mgr):
        """Deal 1800 damage to all zombies in the same cell area."""
        zombies = zombie_mgr.get_by_row(self.row)
        for z in zombies:
            if abs(z.x - self.sprite.rect.centerx) < CELL_WIDTH * 1.2:
                z.take_damage(self.EXPLOSION_DAMAGE)
        self.alive = False


# ═══════════════════════════════════════════════════════════════════════
# Spikeweed
# ═══════════════════════════════════════════════════════════════════════

class Spikeweed(Plant):
    """Ground spikes: zombies walking over deal 20 DPS, immune to eating."""

    DPS = 20.0

    def __init__(self, row: int, col: int):
        super().__init__("Spikeweed", row, col)

    @property
    def is_immune_to_eating(self) -> bool:
        return True

    def plant_update(self, dt: float, **kwargs):
        zombie_mgr = kwargs.get("zombie_mgr")
        if zombie_mgr is None:
            return
        cx = self.sprite.rect.centerx
        for z in zombie_mgr.get_by_row(self.row):
            if z.alive and abs(z.x - cx) < CELL_WIDTH:
                z.take_damage(self.DPS * dt)


# ═══════════════════════════════════════════════════════════════════════
# Squash
# ═══════════════════════════════════════════════════════════════════════

class Squash(Plant):
    """Detects a nearby zombie, aims, then squashes for 1800 damage. One-shot."""

    DETECT_RANGE = CELL_WIDTH * 1.5
    EXPLOSION_DAMAGE = 1800
    AIM_TIME = 0.6
    ATTACK_TIME = 0.5

    def __init__(self, row: int, col: int):
        super().__init__("Squash", row, col)
        self._state: str = "idle"  # idle / aim / attack
        self._state_timer: float = 0.0
        rm = ResourceManager()
        cx, cy = LawnGrid.cell_to_pixel(row, col)
        try:
            self._anim_aim = AnimatedSprite(
                rm.load_sequence("Plants/Squash/SquashAim"),
                fps=8, loop=False, position=(cx, cy),
            )
        except FileNotFoundError:
            self._anim_aim = self.sprite
        try:
            self._anim_attack = AnimatedSprite(
                rm.load_sequence("Plants/Squash/SquashAttack"),
                fps=8, loop=False, position=(cx, cy),
            )
        except FileNotFoundError:
            self._anim_attack = self.sprite

    def plant_update(self, dt: float, **kwargs):
        zombie_mgr = kwargs.get("zombie_mgr")

        if self._state == "idle":
            if zombie_mgr is None:
                return
            cx = self.sprite.rect.centerx
            for z in zombie_mgr.get_by_row(self.row):
                if z.alive and abs(z.x - cx) < self.DETECT_RANGE:
                    self._switch_state("aim")
                    break

        elif self._state == "aim":
            self._state_timer -= dt
            if self._state_timer <= 0 or self._anim_aim.finished:
                self._switch_state("attack")

        elif self._state == "attack":
            self._state_timer -= dt
            if self._state_timer <= 0 or self._anim_attack.finished:
                self._do_squash(zombie_mgr)

    def _switch_state(self, state: str):
        self._state = state
        cx, cy = self.sprite.rect.center
        if state == "aim":
            self.sprite = self._anim_aim
            self._anim_aim.reset()
            self._state_timer = self.AIM_TIME
        elif state == "attack":
            self.sprite = self._anim_attack
            self._anim_attack.reset()
            self._state_timer = self.ATTACK_TIME
        self.sprite.rect.center = (cx, cy)
        self.rect = self.sprite.rect

    def _do_squash(self, zombie_mgr):
        if zombie_mgr is not None:
            cx = self.sprite.rect.centerx
            for z in zombie_mgr.get_by_row(self.row):
                if z.alive and abs(z.x - cx) < CELL_WIDTH * 1.5:
                    z.take_damage(self.EXPLOSION_DAMAGE)
        self.alive = False


# ═══════════════════════════════════════════════════════════════════════
# Threepeater
# ═══════════════════════════════════════════════════════════════════════

class Threepeater(Plant):
    """Fires peas simultaneously in this row and the rows above and below."""

    SHOOT_INTERVAL = 1.4

    def __init__(self, row: int, col: int):
        super().__init__("Threepeater", row, col)
        self._shoot_timer: float = self.SHOOT_INTERVAL

    def plant_update(self, dt: float, **kwargs):
        bullet_mgr = kwargs.get("bullet_mgr")
        zombie_mgr = kwargs.get("zombie_mgr")
        if bullet_mgr is None or zombie_mgr is None:
            return

        # Fire if any of the 3 target rows has a zombie
        target_rows = [r for r in (self.row - 1, self.row, self.row + 1)
                       if 0 <= r < GRID_ROWS]
        if not any(zombie_mgr.get_by_row(r) for r in target_rows):
            return

        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = self.SHOOT_INTERVAL
            for r in target_rows:
                self._fire(bullet_mgr, r)

    def _fire(self, bullet_mgr, row: int):
        from src.entities.bullet import PeaBullet
        bx = float(self.sprite.rect.centerx + 20)
        # Use the target row's y position for bullet travel
        _, by = LawnGrid.cell_to_pixel(row, self.col)
        bullet_mgr.add(PeaBullet(row, bx, float(by)))


# ═══════════════════════════════════════════════════════════════════════
# PuffShroom
# ═══════════════════════════════════════════════════════════════════════

class PuffShroom(Plant):
    """Free mushroom (0 sun). Fires 20-damage spores but only within 3 cells."""

    SHOOT_INTERVAL = 1.4
    RANGE_CELLS = 3
    DAMAGE = 20

    def __init__(self, row: int, col: int):
        super().__init__("PuffShroom", row, col)
        self._shoot_timer: float = self.SHOOT_INTERVAL

    def plant_update(self, dt: float, **kwargs):
        bullet_mgr = kwargs.get("bullet_mgr")
        zombie_mgr = kwargs.get("zombie_mgr")
        if bullet_mgr is None or zombie_mgr is None:
            return

        cx = self.sprite.rect.centerx
        range_px = self.RANGE_CELLS * CELL_WIDTH
        in_range = any(
            z.alive and z.x > cx and (z.x - cx) <= range_px
            for z in zombie_mgr.get_by_row(self.row)
        )
        if not in_range:
            return

        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = self.SHOOT_INTERVAL
            self._fire(bullet_mgr)

    def _fire(self, bullet_mgr):
        from src.entities.bullet import PeaBullet
        bx = float(self.sprite.rect.centerx + 20)
        by = float(self.sprite.rect.centery - 10)
        b = PeaBullet(self.row, bx, by)
        b.damage = self.DAMAGE
        bullet_mgr.add(b)


# ═══════════════════════════════════════════════════════════════════════
# ScaredyShroom
# ═══════════════════════════════════════════════════════════════════════

class ScaredyShroom(Plant):
    """Long-range shooter that hides (stops firing) when a zombie is within 2 cells."""

    SHOOT_INTERVAL = 1.4
    SCARE_RANGE_CELLS = 2

    def __init__(self, row: int, col: int):
        super().__init__("ScaredyShroom", row, col)
        self._shoot_timer: float = self.SHOOT_INTERVAL
        self._hiding: bool = False
        self._anim_normal = self.sprite  # keep reference to idle anim
        rm = ResourceManager()
        cx, cy = LawnGrid.cell_to_pixel(row, col)
        try:
            self._anim_hide = AnimatedSprite(
                rm.load_sequence("Plants/ScaredyShroom/ScaredyShroomSleep"),
                fps=8, loop=True, position=(cx, cy),
            )
        except FileNotFoundError:
            self._anim_hide = self.sprite

    def plant_update(self, dt: float, **kwargs):
        bullet_mgr = kwargs.get("bullet_mgr")
        zombie_mgr = kwargs.get("zombie_mgr")
        if zombie_mgr is None:
            return

        zombies = zombie_mgr.get_by_row(self.row)
        cx = self.sprite.rect.center[0]
        scare_px = self.SCARE_RANGE_CELLS * CELL_WIDTH
        too_close = any(
            z.alive and z.x > cx and (z.x - cx) <= scare_px
            for z in zombies
        )

        # Toggle hiding state
        if too_close and not self._hiding:
            self._hiding = True
            old_center = self.sprite.rect.center
            self.sprite = self._anim_hide
            self._anim_hide.reset()
            self.sprite.rect.center = old_center
            self.rect = self.sprite.rect
        elif not too_close and self._hiding:
            self._hiding = False
            old_center = self.sprite.rect.center
            self.sprite = self._anim_normal
            self.sprite.rect.center = old_center
            self.rect = self.sprite.rect

        if self._hiding or not zombies or bullet_mgr is None:
            return

        self._shoot_timer -= dt
        if self._shoot_timer <= 0:
            self._shoot_timer = self.SHOOT_INTERVAL
            self._fire(bullet_mgr)

    def _fire(self, bullet_mgr):
        from src.entities.bullet import PeaBullet
        bx = float(self.sprite.rect.centerx + 20)
        by = float(self.sprite.rect.centery - 10)
        bullet_mgr.add(PeaBullet(self.row, bx, by))


# ═══════════════════════════════════════════════════════════════════════
# Jalapeno
# ═══════════════════════════════════════════════════════════════════════

class Jalapeno(Plant):
    """Sets the entire row on fire for 1800 damage. One-shot plant."""

    EXPLOSION_DAMAGE = 1800
    FUSE_TIME = 0.8

    def __init__(self, row: int, col: int):
        super().__init__("Jalapeno", row, col)
        self._fuse_timer: float = self.FUSE_TIME
        self._exploded: bool = False

        rm = ResourceManager()
        cx, cy = LawnGrid.cell_to_pixel(row, col)
        try:
            self._anim_explode = AnimatedSprite(
                rm.load_sequence("Plants/Jalapeno/JalapenoExplode"),
                fps=12, loop=False, position=(cx, cy),
            )
        except FileNotFoundError:
            self._anim_explode = None

    def plant_update(self, dt: float, **kwargs):
        zombie_mgr = kwargs.get("zombie_mgr")
        if self._exploded:
            return
        self._fuse_timer -= dt
        if self._fuse_timer <= 0:
            self._explode(zombie_mgr)

    def _explode(self, zombie_mgr):
        self._exploded = True
        if zombie_mgr is not None:
            for z in zombie_mgr.get_by_row(self.row):
                z.take_damage(self.EXPLOSION_DAMAGE)
        self.alive = False


# ═══════════════════════════════════════════════════════════════════════
# Factory
# ═══════════════════════════════════════════════════════════════════════

def create_plant(name: str, row: int, col: int) -> Plant:
    """Factory function to create a plant by name."""
    _MAP = {
        "Peashooter": Peashooter,
        "SunFlower": SunFlower,
        "WallNut": WallNut,
        "SnowPea": SnowPea,
        "CherryBomb": CherryBomb,
        "RepeaterPea": RepeaterPea,
        "Chomper": Chomper,
        "PotatoMine": PotatoMine,
        "Spikeweed": Spikeweed,
        "Squash": Squash,
        "Threepeater": Threepeater,
        "PuffShroom": PuffShroom,
        "ScaredyShroom": ScaredyShroom,
        "Jalapeno": Jalapeno,
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
