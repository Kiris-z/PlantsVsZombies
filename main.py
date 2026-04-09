#!/usr/bin/env python3
"""Plants vs Zombies — entry point."""

from src.engine.game import Game
from src.scenes.menu import MenuScene


def main():
    game = Game()
    game.scene_mgr.switch(MenuScene(game))
    game.run()


if __name__ == "__main__":
    main()
