"""Level select scene — placeholder that auto-advances to gameplay for Sprint 1."""

import pygame
from src.engine.scene import Scene
from src.config import SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, BLACK


class LevelSelectScene(Scene):

    def enter(self):
        self._font = pygame.font.SysFont("Arial", 36)
        self._label = self._font.render("Level 1 - Day", True, BLACK)
        self._timer = 1.5  # seconds before auto-advancing

    def update(self, dt: float):
        self._timer -= dt
        if self._timer <= 0:
            from src.scenes.gameplay import GameplayScene
            self.game.scene_mgr.switch(GameplayScene(self.game))

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            from src.scenes.gameplay import GameplayScene
            self.game.scene_mgr.switch(GameplayScene(self.game))

    def draw(self, surface: pygame.Surface):
        surface.fill(WHITE)
        rect = self._label.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
        surface.blit(self._label, rect)
