"""Sun economy — sky drops, collection, and the fly-to-counter animation."""

from __future__ import annotations

import random
import pygame

from src.config import (
    SCREEN_WIDTH,
    SUN_VALUE,
    SKY_SUN_MIN_INTERVAL,
    SKY_SUN_MAX_INTERVAL,
    SUN_FALL_SPEED,
    SUN_COLLECT_SPEED,
    SUN_LIFETIME,
    SUN_COUNTER_X,
    SUN_COUNTER_Y,
    INITIAL_SUN,
)
from src.engine.resource import ResourceManager
from src.engine.sprite import AnimatedSprite


class Sun:
    """A single sun that falls from the sky and can be collected."""

    def __init__(self, x: float, y_start: float, y_target: float, anim: AnimatedSprite):
        self.x = x
        self.y = y_start
        self.y_target = y_target
        self.anim = anim
        self.anim.rect.center = (int(x), int(y_start))
        self.falling = True
        self.collecting = False  # flying towards counter
        self.alive = True
        self.age = 0.0

    @property
    def rect(self) -> pygame.Rect:
        return self.anim.rect

    def update(self, dt: float):
        if not self.alive:
            return
        self.anim.update(dt)
        if self.collecting:
            # fly towards sun counter
            tx, ty = SUN_COUNTER_X + 20, SUN_COUNTER_Y + 10
            dx, dy = tx - self.x, ty - self.y
            dist = max((dx * dx + dy * dy) ** 0.5, 0.001)
            speed = SUN_COLLECT_SPEED
            if dist < speed * dt:
                self.alive = False
                return
            self.x += dx / dist * speed * dt
            self.y += dy / dist * speed * dt
            self.anim.rect.center = (int(self.x), int(self.y))
            return
        if self.falling:
            self.y += SUN_FALL_SPEED * dt
            if self.y >= self.y_target:
                self.y = self.y_target
                self.falling = False
            self.anim.rect.center = (int(self.x), int(self.y))
        # lifetime — only age when not falling and not being collected
        if not self.falling:
            self.age += dt
            if self.age > SUN_LIFETIME:
                self.alive = False

    def draw(self, surface: pygame.Surface):
        if self.alive:
            surface.blit(self.anim.image, self.anim.rect)

    def collidepoint(self, pos: tuple[int, int]) -> bool:
        return self.alive and self.anim.rect.collidepoint(pos)


class SunManager:
    """Manages sky-sun spawning, collection, and the sun counter."""

    def __init__(self):
        self.sun_count: int = INITIAL_SUN
        self._suns: list[Sun] = []
        self._timer: float = random.uniform(SKY_SUN_MIN_INTERVAL, SKY_SUN_MAX_INTERVAL)
        self._frames = None  # lazily loaded

    def _get_frames(self) -> list[pygame.Surface]:
        if self._frames is None:
            self._frames = ResourceManager().load_sequence("Plants/Sun")
        return self._frames

    def update(self, dt: float):
        # spawn timer
        self._timer -= dt
        if self._timer <= 0:
            self._spawn_sky_sun()
            self._timer = random.uniform(SKY_SUN_MIN_INTERVAL, SKY_SUN_MAX_INTERVAL)
        # update existing
        for s in self._suns:
            s.update(dt)
        # reap dead — add value for collected ones that reached the counter
        new_list = []
        for s in self._suns:
            if s.alive:
                new_list.append(s)
            else:
                # Sun died — if it was being collected (flew to counter), add value
                if s.collecting:
                    self.sun_count += SUN_VALUE
                # otherwise it just expired or was removed
        self._suns = new_list

    def draw(self, surface: pygame.Surface):
        for s in self._suns:
            s.draw(surface)

    def handle_click(self, pos: tuple[int, int]) -> bool:
        """Returns True if a sun was collected."""
        for s in self._suns:
            if s.collidepoint(pos) and not s.collecting:
                s.collecting = True
                s.falling = False
                return True
        return False

    def _spawn_sky_sun(self):
        frames = self._get_frames()
        x = random.randint(60, SCREEN_WIDTH - 60)
        y_target = random.randint(200, 500)
        anim = AnimatedSprite(frames, fps=10, loop=True, position=(x, -40))
        self._suns.append(Sun(x, -40, y_target, anim))
