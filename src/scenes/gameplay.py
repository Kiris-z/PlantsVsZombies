"""Gameplay scene — lawn + card bar + drag-to-plant + falling sun + zombies + combat."""

from __future__ import annotations

import pygame

from src.engine.scene import Scene
from src.engine.resource import ResourceManager
from src.engine.sprite import AnimatedSprite
from src.entities.plant import PlantManager, create_plant, Peashooter, SunFlower
from src.entities.zombie import ZombieManager
from src.entities.bullet import BulletManager
from src.systems.grid import LawnGrid
from src.systems.economy import SunManager
from src.systems.combat import CombatSystem
from src.systems.wave import WaveSystem
from src.config import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    GRID_X_START, GRID_Y_START,
    CELL_WIDTH, CELL_HEIGHT,
    GRID_ROWS, GRID_COLS,
    CARD_BAR_X, CARD_BAR_Y,
    CARD_WIDTH, CARD_HEIGHT, CARD_GAP,
    SUN_COUNTER_X, SUN_COUNTER_Y,
    CARD_ORDER, PLANT_DEFS,
    WHITE, BLACK, YELLOW, CD_OVERLAY_COLOR,
)


class CardSlot:
    """One card in the top bar."""

    def __init__(self, plant_name: str, index: int):
        rm = ResourceManager()
        pdef = PLANT_DEFS[plant_name]
        self.name = plant_name
        self.cost = pdef["cost"]
        self.cooldown_max = pdef["cooldown"]
        self.cooldown_remaining: float = 0.0
        self.card_img = rm.load_image(pdef["card_image"])
        self.card_img = pygame.transform.scale(self.card_img, (CARD_WIDTH, CARD_HEIGHT))
        # greyed-out version
        self.card_gray = self.card_img.copy()
        gray_overlay = pygame.Surface((CARD_WIDTH, CARD_HEIGHT), pygame.SRCALPHA)
        gray_overlay.fill((80, 80, 80, 160))
        self.card_gray.blit(gray_overlay, (0, 0))
        # rect
        x = CARD_BAR_X + 68 + index * (CARD_WIDTH + CARD_GAP)
        y = CARD_BAR_Y + 8
        self.rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)

    def update(self, dt: float):
        if self.cooldown_remaining > 0:
            self.cooldown_remaining -= dt
            if self.cooldown_remaining < 0:
                self.cooldown_remaining = 0.0

    def can_plant(self, sun_count: int) -> bool:
        return sun_count >= self.cost and self.cooldown_remaining <= 0

    def draw(self, surface: pygame.Surface, sun_count: int):
        if self.can_plant(sun_count):
            surface.blit(self.card_img, self.rect)
        else:
            surface.blit(self.card_gray, self.rect)
        # CD overlay (shrinking from top)
        if self.cooldown_remaining > 0:
            frac = self.cooldown_remaining / self.cooldown_max
            h = int(self.rect.height * frac)
            if h > 0:
                overlay = pygame.Surface((self.rect.width, h), pygame.SRCALPHA)
                overlay.fill(CD_OVERLAY_COLOR)
                surface.blit(overlay, (self.rect.x, self.rect.y))


# ═══════════════════════════════════════════════════════════════════════
# Game end states
# ═══════════════════════════════════════════════════════════════════════

class _EndState:
    PLAYING = 0
    VICTORY = 1
    GAME_OVER = 2


class GameplayScene(Scene):

    def enter(self):
        rm = ResourceManager()

        # ── Background ────────────────────────────────────────────────
        self._bg = rm.load_image("Items/Background/Background_0.jpg", alpha=False)
        self._bg = pygame.transform.scale(self._bg, (SCREEN_WIDTH, SCREEN_HEIGHT))

        # ── Card bar background ───────────────────────────────────────
        self._panel_bg = rm.load_image("Screen/ChooserBackground.png")

        # ── Cards ─────────────────────────────────────────────────────
        self._cards: list[CardSlot] = []
        for i, name in enumerate(CARD_ORDER):
            self._cards.append(CardSlot(name, i))

        # ── Plant manager (replaces old EntityManager) ────────────────
        self._plant_mgr = PlantManager()

        # ── Zombie manager ────────────────────────────────────────────
        self._zombie_mgr = ZombieManager()

        # ── Bullet manager ────────────────────────────────────────────
        self._bullet_mgr = BulletManager()

        # ── Combat system ─────────────────────────────────────────────
        self._combat = CombatSystem(self._bullet_mgr, self._zombie_mgr)

        # ── Wave system ───────────────────────────────────────────────
        self._wave_sys = WaveSystem(
            "src/data/levels/level_1_1.json",
            self._zombie_mgr,
        )

        # ── Sun manager ───────────────────────────────────────────────
        self._sun_mgr = SunManager()
        self._sun_mgr.sun_count = self._wave_sys.initial_sun

        # ── Drag state ────────────────────────────────────────────────
        self._dragging: CardSlot | None = None
        self._drag_img: pygame.Surface | None = None
        self._drag_pos: tuple[int, int] = (0, 0)

        # ── End-game state ────────────────────────────────────────────
        self._end_state: int = _EndState.PLAYING
        self._end_image: pygame.Surface | None = None
        self._end_timer: float = 0.0

        # ── Font ──────────────────────────────────────────────────────
        self._font = pygame.font.SysFont("Arial", 18, bold=True)
        self._wave_font = pygame.font.SysFont("Arial", 14, bold=True)
        self._big_font = pygame.font.SysFont("Arial", 28, bold=True)

        # ── Flag wave warning ─────────────────────────────────────────
        self._flag_warning_timer: float = 0.0
        self._last_flag_wave: int = -1

    # ── events ────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event):
        if self._end_state != _EndState.PLAYING:
            # Click to return to menu
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self._end_timer <= 0:
                    from src.scenes.menu import MenuScene
                    self.game.scene_mgr.switch(MenuScene(self.game))
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            pos = event.pos
            # try collecting sun first
            if self._sun_mgr.handle_click(pos):
                return
            # try picking up a card
            for card in self._cards:
                if card.rect.collidepoint(pos) and card.can_plant(self._sun_mgr.sun_count):
                    self._dragging = card
                    self._drag_img = card.card_img.copy()
                    self._drag_img.set_alpha(180)
                    self._drag_pos = pos
                    return

        elif event.type == pygame.MOUSEMOTION:
            if self._dragging:
                self._drag_pos = event.pos

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self._dragging:
                cell = LawnGrid.pixel_to_cell(*event.pos)
                if cell is not None:
                    row, col = cell
                    if self._plant_mgr.get_at(row, col) is None:
                        self._plant(self._dragging, row, col)
                self._dragging = None
                self._drag_img = None

    # ── planting ──────────────────────────────────────────────────────

    def _plant(self, card: CardSlot, row: int, col: int):
        plant = create_plant(card.name, row, col)
        self._plant_mgr.add(plant)
        self._sun_mgr.sun_count -= card.cost
        card.cooldown_remaining = card.cooldown_max

    # ── update ────────────────────────────────────────────────────────

    def update(self, dt: float):
        if self._end_state != _EndState.PLAYING:
            self._end_timer -= dt
            return

        # Cards
        for card in self._cards:
            card.update(dt)

        # Sun
        self._sun_mgr.update(dt)

        # Waves
        self._wave_sys.update(dt)

        # Flag wave warning
        if self._wave_sys.is_flag_wave and self._wave_sys.current_wave_index != self._last_flag_wave:
            self._last_flag_wave = self._wave_sys.current_wave_index
            self._flag_warning_timer = 3.0
        if self._flag_warning_timer > 0:
            self._flag_warning_timer -= dt

        # Plants — pass bullet_mgr and sun_mgr, plus per-row zombie info
        for plant in self._plant_mgr.all_alive():
            kwargs = {"sun_mgr": self._sun_mgr, "bullet_mgr": self._bullet_mgr}
            # Check if any zombie is alive in this row
            if isinstance(plant, Peashooter):
                zombies_in_row = len(self._zombie_mgr.get_by_row(plant.row)) > 0
                kwargs["zombies_in_row"] = zombies_in_row
            plant.update(dt, **kwargs)

        # Bullets
        self._bullet_mgr.update(dt)

        # Zombies
        self._zombie_mgr.update(dt, self._plant_mgr)

        # Combat
        self._combat.update(dt)

        # ── Win/Lose checks ───────────────────────────────────────────
        # Lose: zombie reached the house
        if self._zombie_mgr.any_reached_house():
            self._trigger_game_over()

        # Win: all waves done and no zombies alive
        if (
            self._wave_sys.all_waves_done
            and self._zombie_mgr.total_spawned_alive == 0
        ):
            self._trigger_victory()

    # ── end-game triggers ─────────────────────────────────────────────

    def _trigger_victory(self):
        rm = ResourceManager()
        self._end_state = _EndState.VICTORY
        self._end_image = rm.load_image("Screen/GameVictory.png")
        self._end_timer = 1.0  # brief delay before click-to-continue

    def _trigger_game_over(self):
        rm = ResourceManager()
        self._end_state = _EndState.GAME_OVER
        self._end_image = rm.load_image("Screen/GameLoose.png")
        self._end_timer = 1.0

    # ── draw ──────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface):
        # background
        surface.blit(self._bg, (0, 0))

        # grid overlay (subtle)
        self._draw_grid(surface)

        # plants
        self._plant_mgr.draw(surface)

        # bullets & effects
        self._bullet_mgr.draw(surface)

        # zombies
        self._zombie_mgr.draw(surface)

        # suns
        self._sun_mgr.draw(surface)

        # card bar
        surface.blit(self._panel_bg, (CARD_BAR_X, CARD_BAR_Y))
        for card in self._cards:
            card.draw(surface, self._sun_mgr.sun_count)

        # sun counter text
        sun_text = self._font.render(str(self._sun_mgr.sun_count), True, BLACK)
        surface.blit(sun_text, (SUN_COUNTER_X + 8, SUN_COUNTER_Y))

        # wave progress
        self._draw_wave_progress(surface)

        # Flag wave warning
        if self._flag_warning_timer > 0:
            warn = self._big_font.render("A HUGE WAVE OF ZOMBIES IS APPROACHING!", True, (255, 0, 0))
            rect = warn.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50))
            # Background for readability
            bg = pygame.Surface((rect.width + 20, rect.height + 10), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 160))
            surface.blit(bg, (rect.x - 10, rect.y - 5))
            surface.blit(warn, rect)

        # drag ghost
        if self._dragging and self._drag_img:
            r = self._drag_img.get_rect(center=self._drag_pos)
            surface.blit(self._drag_img, r)
            # highlight cell under cursor
            cell = LawnGrid.pixel_to_cell(*self._drag_pos)
            if cell is not None:
                row, col = cell
                tx, ty = LawnGrid.cell_topleft(row, col)
                highlight = pygame.Surface((CELL_WIDTH, CELL_HEIGHT), pygame.SRCALPHA)
                highlight.fill((255, 255, 255, 50))
                surface.blit(highlight, (tx, ty))

        # ── End-game overlay ──────────────────────────────────────────
        if self._end_state != _EndState.PLAYING and self._end_image is not None:
            # Darken background
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            surface.blit(overlay, (0, 0))
            # Centre the end image
            rect = self._end_image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            surface.blit(self._end_image, rect)
            if self._end_timer <= 0:
                hint = self._font.render("Click to continue", True, WHITE)
                hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 120))
                surface.blit(hint, hint_rect)

    def _draw_grid(self, surface: pygame.Surface):
        """Draw a subtle grid overlay so the player can see cells."""
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x, y = LawnGrid.cell_topleft(row, col)
                rect = pygame.Rect(x, y, CELL_WIDTH, CELL_HEIGHT)
                pygame.draw.rect(surface, (255, 255, 255, 30), rect, 1)

    def _draw_wave_progress(self, surface: pygame.Surface):
        """Draw wave progress indicator at the bottom of the screen."""
        total = self._wave_sys.total_waves
        current = min(self._wave_sys.current_wave_index + 1, total)
        text = f"Wave {current}/{total}"
        if self._wave_sys.all_waves_done:
            text = "Final Wave!"
        label = self._wave_font.render(text, True, WHITE)
        # Draw a small progress bar
        bar_w = 120
        bar_h = 12
        bar_x = SCREEN_WIDTH - bar_w - 15
        bar_y = SCREEN_HEIGHT - bar_h - 10
        # background
        bg_rect = pygame.Rect(bar_x, bar_y, bar_w, bar_h)
        pygame.draw.rect(surface, (50, 50, 50), bg_rect)
        # fill
        frac = current / max(total, 1)
        fill_w = int(bar_w * frac)
        fill_rect = pygame.Rect(bar_x, bar_y, fill_w, bar_h)
        color = (255, 50, 50) if self._wave_sys.is_flag_wave else (50, 200, 50)
        pygame.draw.rect(surface, color, fill_rect)
        # border
        pygame.draw.rect(surface, WHITE, bg_rect, 1)
        # text
        surface.blit(label, (bar_x, bar_y - 18))
