"""ResourceManager — singleton that auto-discovers PNG frame sequences under resources/."""

import os
import re
import pygame
from src.config import RESOURCES_DIR


class ResourceManager:
    """Loads and caches images.  Frame sequences are detected automatically."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._cache = {}        # path -> Surface
            cls._instance._sequences = {}    # folder_key -> [Surface, ...]
        return cls._instance

    # ── public API ────────────────────────────────────────────────────

    def load_image(self, rel_path: str, alpha: bool = True) -> pygame.Surface:
        """Load a single image by relative path under resources/."""
        if rel_path in self._cache:
            return self._cache[rel_path]
        full = os.path.join(RESOURCES_DIR, rel_path)
        img = pygame.image.load(full)
        img = img.convert_alpha() if alpha else img.convert()
        self._cache[rel_path] = img
        return img

    def load_sequence(self, folder_rel: str, alpha: bool = True) -> list[pygame.Surface]:
        """Load a numbered PNG sequence from *folder_rel* (relative to resources/).

        Files must match ``<Name>_<N>.png``.  Returned list is ordered by N.
        """
        if folder_rel in self._sequences:
            return self._sequences[folder_rel]

        full_dir = os.path.join(RESOURCES_DIR, folder_rel)
        if not os.path.isdir(full_dir):
            raise FileNotFoundError(f"Sequence directory not found: {full_dir}")

        pattern = re.compile(r"^(.+)_(\d+)\.png$", re.IGNORECASE)
        entries: list[tuple[int, str]] = []
        for fname in os.listdir(full_dir):
            m = pattern.match(fname)
            if m:
                entries.append((int(m.group(2)), fname))
        entries.sort(key=lambda t: t[0])

        frames: list[pygame.Surface] = []
        for _, fname in entries:
            full = os.path.join(full_dir, fname)
            img = pygame.image.load(full)
            img = img.convert_alpha() if alpha else img.convert()
            frames.append(img)

        if not frames:
            raise FileNotFoundError(f"No frames found in {full_dir}")

        self._sequences[folder_rel] = frames
        return frames

    def clear(self):
        """Drop all cached data (e.g. on scene teardown)."""
        self._cache.clear()
        self._sequences.clear()
