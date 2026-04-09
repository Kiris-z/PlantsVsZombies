"""Scene base class and SceneManager."""

from __future__ import annotations
from typing import TYPE_CHECKING
import pygame

if TYPE_CHECKING:
    from src.engine.game import Game


class Scene:
    """Abstract scene.  Subclasses override the lifecycle hooks."""

    def __init__(self, game: Game):
        self.game = game

    def enter(self):
        """Called when the scene becomes active."""

    def exit(self):
        """Called when the scene is replaced."""

    def handle_event(self, event: pygame.event.Event):
        """Process a single pygame event."""

    def update(self, dt: float):
        """Advance state by *dt* seconds."""

    def draw(self, surface: pygame.Surface):
        """Render the scene onto *surface*."""


class SceneManager:
    """Stack-free scene switcher (one active scene at a time)."""

    def __init__(self, game: Game):
        self.game = game
        self._current: Scene | None = None

    @property
    def current(self) -> Scene | None:
        return self._current

    def switch(self, scene: Scene):
        if self._current is not None:
            self._current.exit()
        self._current = scene
        self._current.enter()

    def handle_event(self, event: pygame.event.Event):
        if self._current:
            self._current.handle_event(event)

    def update(self, dt: float):
        if self._current:
            self._current.update(dt)

    def draw(self, surface: pygame.Surface):
        if self._current:
            self._current.draw(surface)
