"""Gameplay scene — lawn + card bar + drag-to-plant + falling sun."""

from __future__ import annotations

import pygame

from src.engine.scene import Scene
from src.engine.resource import ResourceManager
from src.engine.sprite import AnimatedSprite
from src.engine.entity import Entity, EntityManager
from src.systems.grid import LawnGrid
from src.systems.economy import SunManager
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

        # ── Entity manager ────────────────────────────────────────────
        self._entities = EntityManager()

        # ── Sun manager ───────────────────────────────────────────────
        self._sun_mgr = SunManager()

        # ── Drag state ────────────────────────────────────────────────
        self._dragging: CardSlot | None = None
        self._drag_img: pygame.Surface | None = None
        self._drag_pos: tuple[int, int] = (0, 0)

        # ── Font ──────────────────────────────────────────────────────
        self._font = pygame.font.SysFont("Arial", 18, bold=True)

    # ── events ────────────────────────────────────────────────────────

    def handle_event(self, event: pygame.event.Event):
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
                    if self._entities.get_at(row, col) is None:
                        self._plant(self._dragging, row, col)
                self._dragging = None
                self._drag_img = None

    # ── planting ──────────────────────────────────────────────────────

    def _plant(self, card: CardSlot, row: int, col: int):
        rm = ResourceManager()
        pdef = PLANT_DEFS[card.name]
        frames = rm.load_sequence(pdef["anim_folder"])
        cx, cy = LawnGrid.cell_to_pixel(row, col)
        anim = AnimatedSprite(frames, fps=pdef["anim_fps"], loop=True, position=(cx, cy))
        entity = Entity(card.name, anim, row=row, col=col, hp=pdef["hp"])
        self._entities.add(entity)
        self._sun_mgr.sun_count -= card.cost
        card.cooldown_remaining = card.cooldown_max

    # ── update ────────────────────────────────────────────────────────

    def update(self, dt: float):
        for card in self._cards:
            card.update(dt)
        self._sun_mgr.update(dt)
        self._entities.update(dt)

    # ── draw ──────────────────────────────────────────────────────────

    def draw(self, surface: pygame.Surface):
        # background
        surface.blit(self._bg, (0, 0))

        # grid overlay (subtle)
        self._draw_grid(surface)

        # entities (plants)
        self._entities.draw(surface)

        # suns
        self._sun_mgr.draw(surface)

        # card bar
        surface.blit(self._panel_bg, (CARD_BAR_X, CARD_BAR_Y))
        for card in self._cards:
            card.draw(surface, self._sun_mgr.sun_count)

        # sun counter text
        sun_text = self._font.render(str(self._sun_mgr.sun_count), True, BLACK)
        surface.blit(sun_text, (SUN_COUNTER_X + 8, SUN_COUNTER_Y))

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

    def _draw_grid(self, surface: pygame.Surface):
        """Draw a subtle grid overlay so the player can see cells."""
        for row in range(GRID_ROWS):
            for col in range(GRID_COLS):
                x, y = LawnGrid.cell_topleft(row, col)
                rect = pygame.Rect(x, y, CELL_WIDTH, CELL_HEIGHT)
                pygame.draw.rect(surface, (255, 255, 255, 30), rect, 1)
