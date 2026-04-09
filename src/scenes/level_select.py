"""Level select scene — 2×5 grid of level buttons with lock/star states."""

from __future__ import annotations

import pygame
from src.engine.scene import Scene
from src.systems.save import SaveManager
from src.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, LEVEL_LIST,
    WHITE, BLACK, GRAY, YELLOW,
)


# Button layout constants
COLS = 5
ROWS = 3
BTN_W = 110
BTN_H = 70
GAP_X = 20
GAP_Y = 30
GRID_W = COLS * BTN_W + (COLS - 1) * GAP_X
GRID_H = ROWS * BTN_H + (ROWS - 1) * GAP_Y
START_X = (SCREEN_WIDTH - GRID_W) // 2
START_Y = (SCREEN_HEIGHT - GRID_H) // 2 + 20


class _LevelButton:
    def __init__(self, level_def: dict, grid_row: int, grid_col: int):
        self.level_id: str = level_def["id"]
        self.level_file: str = level_def["file"]
        self.name: str = level_def["name"]
        x = START_X + grid_col * (BTN_W + GAP_X)
        y = START_Y + grid_row * (BTN_H + GAP_Y)
        self.rect = pygame.Rect(x, y, BTN_W, BTN_H)
        self.unlocked: bool = False
        self.completed: bool = False

    def refresh(self, save: SaveManager):
        self.unlocked = save.is_level_unlocked(self.level_id)
        self.completed = save.is_level_completed(self.level_id)


class LevelSelectScene(Scene):

    def enter(self):
        self._font = pygame.font.SysFont("Arial", 22, bold=True)
        self._title_font = pygame.font.SysFont("Arial", 36, bold=True)
        self._star_font = pygame.font.SysFont("Arial", 16, bold=True)
        self._small_font = pygame.font.SysFont("Arial", 14)

        self._save = SaveManager()
        self._save.load()

        # Build buttons
        self._buttons: list[_LevelButton] = []
        for i, ldef in enumerate(LEVEL_LIST):
            row = i // COLS
            col = i % COLS
            btn = _LevelButton(ldef, row, col)
            btn.refresh(self._save)
            self._buttons.append(btn)

    def handle_event(self, event: pygame.event.Event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            from src.scenes.menu import MenuScene
            self.game.scene_mgr.switch(MenuScene(self.game))
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self._buttons:
                if btn.rect.collidepoint(event.pos) and btn.unlocked and btn.level_file:
                    from src.scenes.gameplay import GameplayScene
                    scene = GameplayScene(self.game, level_file=btn.level_file,
                                          level_id=btn.level_id)
                    self.game.scene_mgr.switch(scene)
                    return

    def draw(self, surface: pygame.Surface):
        # Background
        surface.fill((34, 85, 34))

        # Title
        title = self._title_font.render("Adventure Mode", True, WHITE)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, START_Y - 60))
        surface.blit(title, title_rect)

        # Subtitle
        sub = self._small_font.render("Select a level to play", True, (200, 200, 200))
        sub_rect = sub.get_rect(center=(SCREEN_WIDTH // 2, START_Y - 30))
        surface.blit(sub, sub_rect)

        # Buttons
        for btn in self._buttons:
            self._draw_button(surface, btn)

        # Back hint
        hint = self._small_font.render("Press ESC to return to menu", True, (160, 160, 160))
        surface.blit(hint, (10, SCREEN_HEIGHT - 25))

    def _draw_button(self, surface: pygame.Surface, btn: _LevelButton):
        if btn.unlocked:
            if btn.completed:
                # Completed — green bg
                bg_color = (40, 140, 40)
                border_color = (80, 220, 80)
            else:
                # Unlocked but not completed — brown bg
                bg_color = (120, 80, 40)
                border_color = (200, 160, 80)
        else:
            # Locked — dark gray
            bg_color = (60, 60, 60)
            border_color = (90, 90, 90)

        # Draw rounded rect
        pygame.draw.rect(surface, bg_color, btn.rect, border_radius=8)
        pygame.draw.rect(surface, border_color, btn.rect, 2, border_radius=8)

        # Level name
        if btn.unlocked:
            text_color = WHITE
        else:
            text_color = (120, 120, 120)
        label = self._font.render(btn.level_id, True, text_color)
        label_rect = label.get_rect(center=(btn.rect.centerx, btn.rect.centery - 5))
        surface.blit(label, label_rect)

        if btn.completed:
            # Draw star
            star = self._star_font.render("★", True, YELLOW)
            star_rect = star.get_rect(center=(btn.rect.centerx, btn.rect.centery + 20))
            surface.blit(star, star_rect)
        elif not btn.unlocked:
            # Draw lock icon
            lock = self._star_font.render("🔒", True, (120, 120, 120))
            lock_rect = lock.get_rect(center=(btn.rect.centerx, btn.rect.centery + 20))
            surface.blit(lock, lock_rect)

    def update(self, dt: float):
        pass
