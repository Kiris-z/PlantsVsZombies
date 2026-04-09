"""Main menu scene — MainMenu.png background + StartButton."""

import pygame
from src.engine.scene import Scene
from src.engine.resource import ResourceManager
from src.config import SCREEN_WIDTH, SCREEN_HEIGHT


class MenuScene(Scene):

    def enter(self):
        rm = ResourceManager()
        self._bg = rm.load_image("Screen/MainMenu.png", alpha=False)
        self._bg = pygame.transform.scale(self._bg, (SCREEN_WIDTH, SCREEN_HEIGHT))
        self._btn = rm.load_image("Screen/StartButton.png")
        self._btn_rect = self._btn.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 70))

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self._btn_rect.collidepoint(event.pos):
                from src.scenes.gameplay import GameplayScene
                self.game.scene_mgr.switch(GameplayScene(self.game))

    def draw(self, surface: pygame.Surface):
        surface.blit(self._bg, (0, 0))
        surface.blit(self._btn, self._btn_rect)
