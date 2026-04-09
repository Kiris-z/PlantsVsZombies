"""Combat system — bullet-zombie collisions and damage application."""

from __future__ import annotations

from src.config import GRID_ROWS
from src.entities.bullet import BulletManager, IcePeaBullet
from src.entities.zombie import ZombieManager


class CombatSystem:
    """Per-frame collision detection between bullets and zombies (row-based AABB)."""

    def __init__(self, bullet_mgr: BulletManager, zombie_mgr: ZombieManager):
        self._bullet_mgr = bullet_mgr
        self._zombie_mgr = zombie_mgr

    def update(self, dt: float):
        """Run collision checks for every row."""
        for row in range(GRID_ROWS):
            bullets = self._bullet_mgr.get_by_row(row)
            if not bullets:
                continue
            zombies = self._zombie_mgr.get_by_row(row)
            if not zombies:
                continue
            self._check_row(bullets, zombies)

    def _check_row(self, bullets, zombies):
        for bullet in bullets:
            if not bullet.alive:
                continue
            for zombie in zombies:
                if not zombie.alive:
                    continue
                # AABB collision
                if bullet.rect.colliderect(zombie.rect):
                    # Apply damage
                    zombie.take_damage(bullet.damage)
                    # Apply slow effect for ice bullets
                    if bullet.is_ice:
                        zombie.apply_slow(
                            IcePeaBullet.SLOW_FACTOR,
                            IcePeaBullet.SLOW_DURATION,
                        )
                    # Spawn explosion effect
                    self._bullet_mgr.spawn_explosion(
                        bullet.rect.centerx,
                        bullet.rect.centery,
                    )
                    # Kill bullet
                    bullet.kill()
                    break  # bullet is gone, move to next bullet
