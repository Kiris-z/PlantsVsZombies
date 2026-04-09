"""AnimatedSprite — frame-based animation with loop / one-shot / speed control."""

import pygame


class AnimatedSprite(pygame.sprite.Sprite):
    """A sprite that cycles through a list of :class:`pygame.Surface` frames.

    Parameters
    ----------
    frames : list[pygame.Surface]
        Ordered animation frames.
    fps : float
        Playback speed in frames per second.
    loop : bool
        Whether the animation loops (default ``True``).
    position : tuple[float, float]
        Initial centre position.
    """

    def __init__(
        self,
        frames: list[pygame.Surface],
        fps: float = 12.0,
        loop: bool = True,
        position: tuple[float, float] = (0, 0),
    ):
        super().__init__()
        self.frames = frames
        self.fps = fps
        self.loop = loop
        self._index: float = 0.0
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=position)
        self.finished = False

    # ── update ────────────────────────────────────────────────────────

    def update(self, dt: float):
        """Advance the animation by *dt* seconds."""
        if self.finished:
            return
        self._index += self.fps * dt
        max_idx = len(self.frames)
        if self.loop:
            self._index %= max_idx
        elif self._index >= max_idx:
            self._index = max_idx - 1
            self.finished = True
        self.image = self.frames[int(self._index)]

    # ── helpers ───────────────────────────────────────────────────────

    def reset(self):
        self._index = 0.0
        self.finished = False
        self.image = self.frames[0]

    @property
    def current_frame(self) -> int:
        return int(self._index) % len(self.frames)
