#!/usr/bin/env python3
"""Unit-level checks for core game systems."""

import os, sys

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

import pygame
pygame.init()
screen = pygame.display.set_mode((800, 600))

from src.config import GRID_ROWS, CELL_WIDTH, GRID_X_START
from src.entities.plant import PlantManager, create_plant, Peashooter, SunFlower
from src.entities.zombie import ZombieManager, create_zombie
from src.entities.bullet import BulletManager, PeaBullet
from src.systems.economy import SunManager
from src.systems.combat import CombatSystem
from src.systems.wave import WaveSystem
from src.systems.lawnmower import LawnMowerManager

DT = 1.0 / 60.0
tests_passed = 0
tests_failed = 0
issues = []

def check(name, condition, detail=""):
    global tests_passed, tests_failed
    if condition:
        tests_passed += 1
        print(f"  ✅ {name}")
    else:
        tests_failed += 1
        msg = f"{name}: {detail}" if detail else name
        print(f"  ❌ {msg}")
        issues.append(msg)

# ── Test 1: Sun economy ──────────────────────────────────────────────
print("\n🌻 Test 1: Sun Economy")
sun_mgr = SunManager()
sun_mgr.sun_count = 100
check("Initial sun = 100", sun_mgr.sun_count == 100)

# Manually add and collect sun
sun_mgr.sun_count += 25
check("Sun addition works", sun_mgr.sun_count == 125)

sun_mgr.sun_count -= 50
check("Sun subtraction works", sun_mgr.sun_count == 75)
check("Sun never negative (manual)", sun_mgr.sun_count >= 0)

# Sky sun spawning after enough time
# Max initial interval is 25s, so wait ~50s to guarantee at least one spawn.
# Suns expire after landing (8s lifetime), so track if ANY sun was ever created.
sky_sun_ever_spawned = False
for _ in range(3000):  # ~50 seconds
    sun_mgr.update(DT)
    if len(sun_mgr._suns) > 0:
        sky_sun_ever_spawned = True
check("Sky suns spawn", sky_sun_ever_spawned, f"current suns={len(sun_mgr._suns)}")

# ── Test 2: Bullet-zombie collision ──────────────────────────────────
print("\n🔫 Test 2: Bullet-Zombie Collision")
zombie_mgr = ZombieManager()
bullet_mgr = BulletManager()
combat = CombatSystem(bullet_mgr, zombie_mgr)

z = create_zombie("Normal", 2)
z.x = 500.0
z.y = 340.0
z.rect.center = (int(z.x), int(z.y))
zombie_mgr.add(z)
initial_hp = z.total_hp

# Create bullet heading toward zombie
b = PeaBullet(2, 400.0, 340.0)
bullet_mgr.add(b)

for _ in range(300):
    bullet_mgr.update(DT)
    combat.update(DT)
    if not b.alive:
        break

check("Bullet hits zombie", not b.alive or z.total_hp < initial_hp,
      f"bullet.alive={b.alive}, zombie hp={z.total_hp}/{initial_hp}")
check("Zombie takes damage", z.total_hp < initial_hp,
      f"hp={z.total_hp}, expected < {initial_hp}")

# ── Test 3: Zombie death ─────────────────────────────────────────────
print("\n💀 Test 3: Zombie Death")
zombie_mgr2 = ZombieManager()
z2 = create_zombie("Normal", 1)
zombie_mgr2.add(z2)
z2.take_damage(9999)
check("Zombie dies from lethal damage", z2.state.name in ("DIE", "DEAD"),
      f"state={z2.state.name}")

# Let death anim play
plant_mgr_dummy = PlantManager()
for _ in range(200):
    zombie_mgr2.update(DT, plant_mgr_dummy)
check("Dead zombie removed", zombie_mgr2.total_spawned_alive == 0,
      f"alive={zombie_mgr2.total_spawned_alive}")

# ── Test 4: SunFlower produces sun ───────────────────────────────────
print("\n🌻 Test 4: SunFlower Production")
sun_mgr2 = SunManager()
sun_mgr2.sun_count = 0
sf = create_plant("SunFlower", 2, 1)
# Run for 15 simulated seconds (first sun at ~12s)
for _ in range(int(15 / DT)):
    sf.update(DT, sun_mgr=sun_mgr2, bullet_mgr=BulletManager(), zombie_mgr=ZombieManager())
    sun_mgr2.update(DT)
    # Auto-collect produced suns
    for s in list(sun_mgr2._suns):
        if s.alive and not s.collecting:
            s.collecting = True
            s.falling = False

check("SunFlower produces sun within 15s", sun_mgr2.sun_count > 0,
      f"sun_count={sun_mgr2.sun_count}")

# ── Test 5: Peashooter fires when zombie present ─────────────────────
print("\n🔫 Test 5: Peashooter Targeting")
bullet_mgr3 = BulletManager()
zombie_mgr3 = ZombieManager()
ps = create_plant("Peashooter", 2, 3)

# No zombies → should NOT fire
for _ in range(200):
    ps.update(DT, bullet_mgr=bullet_mgr3, zombie_mgr=zombie_mgr3, sun_mgr=SunManager(),
              zombies_in_row=False)
check("Peashooter doesn't fire without zombies", len(bullet_mgr3.bullets) == 0,
      f"bullets={len(bullet_mgr3.bullets)}")

# Add zombie → should fire
z3 = create_zombie("Normal", 2)
zombie_mgr3.add(z3)
for _ in range(200):  # ~3.3s, enough for 2 shots
    ps.update(DT, bullet_mgr=bullet_mgr3, zombie_mgr=zombie_mgr3, sun_mgr=SunManager(),
              zombies_in_row=True)
    bullet_mgr3.update(DT)
check("Peashooter fires with zombie in row", len(bullet_mgr3.bullets) > 0,
      f"bullets={len(bullet_mgr3.bullets)}")

# ── Test 6: Lawnmower activation ─────────────────────────────────────
print("\n🚗 Test 6: Lawnmower")
zombie_mgr4 = ZombieManager()
lm = LawnMowerManager()
z4 = create_zombie("Normal", 2)
z4.x = GRID_X_START - 5  # Just past the mower line
z4.rect.center = (int(z4.x), int(z4.y))
zombie_mgr4.add(z4)

# Should trigger mower, not game over
game_over = lm.check_zombie_reach(zombie_mgr4)
mower_row2 = lm.mowers[2]
check("Mower activates when zombie reaches line", mower_row2.activated,
      f"activated={mower_row2.activated}")
check("First mower activation is not game over", not game_over,
      f"game_over={game_over}")

# ── Test 7: Victory condition ─────────────────────────────────────────
print("\n🏆 Test 7: Victory Condition")
wave_sys = WaveSystem("src/data/levels/level_1_1.json", ZombieManager())
check("Level 1-1 has 5 waves", wave_sys.total_waves == 5, f"waves={wave_sys.total_waves}")
check("Initial sun is 150", wave_sys.initial_sun == 150, f"initial_sun={wave_sys.initial_sun}")
check("Available plants correct", set(wave_sys.available_plants) == {"Peashooter", "SunFlower", "WallNut"},
      f"plants={wave_sys.available_plants}")

# ── Test 8: All zombie types can be created ───────────────────────────
print("\n🧟 Test 8: Zombie Factory")
for ztype in ["Normal", "Conehead", "Buckethead", "Flag", "Newspaper"]:
    try:
        z = create_zombie(ztype, 0)
        check(f"Create {ztype}", z is not None and z.alive)
    except Exception as e:
        check(f"Create {ztype}", False, str(e))

# ── Test 9: All plant types can be created ────────────────────────────
print("\n🌱 Test 9: Plant Factory")
from src.config import PLANT_DEFS
for pname in PLANT_DEFS:
    try:
        p = create_plant(pname, 0, 0)
        check(f"Create {pname}", p is not None and p.alive)
    except Exception as e:
        check(f"Create {pname}", False, str(e))

# ── Summary ──────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"Results: {tests_passed} passed, {tests_failed} failed")
if issues:
    print("Issues:")
    for i in issues:
        print(f"  - {i}")
print("=" * 60)

sys.exit(1 if tests_failed > 0 else 0)
