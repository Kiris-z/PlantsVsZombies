"""Game — main loop (60 FPS) with a simple state machine."""

from __future__ import annotations

import sys
import pygame
from src.config import SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE
from src.engine.scene import SceneManager


class GameState:
    MENU = "MENU"
    PLAYING = "PLAYING"
    PAUSED = "PAUSED"
    GAME_OVER = "GAME_OVER"


class Game:
    """Top-level object that owns the display, clock, and scene manager."""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = GameState.MENU
        self.scene_mgr = SceneManager(self)

    # ── main loop ─────────────────────────────────────────────────────

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            self._process_events()
            self.scene_mgr.update(dt)
            self.scene_mgr.draw(self.screen)
            pygame.display.flip()
        pygame.quit()
        sys.exit()

    # ── internals ─────────────────────────────────────────────────────

    def _process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            else:
                self.scene_mgr.handle_event(event)

    def quit(self):
        self.running = False
