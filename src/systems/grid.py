"""5-row × 9-column lawn grid with pixel ↔ cell conversion."""

from src.config import (
    GRID_ROWS, GRID_COLS,
    GRID_X_START, GRID_Y_START,
    CELL_WIDTH, CELL_HEIGHT,
)


class LawnGrid:
    """Utility for mapping between grid cells and pixel coordinates."""

    rows = GRID_ROWS
    cols = GRID_COLS

    @staticmethod
    def cell_to_pixel(row: int, col: int) -> tuple[int, int]:
        """Return the *centre* pixel position of the given cell."""
        x = GRID_X_START + col * CELL_WIDTH + CELL_WIDTH // 2
        y = GRID_Y_START + row * CELL_HEIGHT + CELL_HEIGHT // 2
        return x, y

    @staticmethod
    def cell_topleft(row: int, col: int) -> tuple[int, int]:
        """Return the top-left pixel of the cell."""
        x = GRID_X_START + col * CELL_WIDTH
        y = GRID_Y_START + row * CELL_HEIGHT
        return x, y

    @staticmethod
    def pixel_to_cell(px: int, py: int) -> tuple[int, int] | None:
        """Convert pixel position to (row, col) or *None* if outside the grid."""
        col = (px - GRID_X_START) // CELL_WIDTH
        row = (py - GRID_Y_START) // CELL_HEIGHT
        if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
            return row, col
        return None

    @staticmethod
    def is_valid(row: int, col: int) -> bool:
        return 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS
