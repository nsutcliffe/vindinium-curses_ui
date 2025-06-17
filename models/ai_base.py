from abc import ABC, abstractmethod
from collections import deque
from enum import Enum

from game import Game


class MapElements(str, Enum):
    OWNED_MINE = 'O'
    HERO = '@'
    MINE = '$'
    ENEMY = 'H'
    TAVERN = 'T'


class Directions(str, Enum):
    NORTH = "North"
    SOUTH = "South"
    EAST = "East"
    WEST = "West"
    STAY = "Stay"

    @staticmethod
    def get_direction(start_pos, next):
        start_row, start_col = start_pos
        next_row, next_col = next

        dr = next_row - start_row
        dc = next_col - start_col

        if dr == -1 and dc == 0:
            return "North"
        elif dr == 1 and dc == 0:
            return "South"
        elif dr == 0 and dc == 1:
            return "East"
        elif dr == 0 and dc == -1:
            return "West"
        elif dr == 0 and dc == 0:
            return "Stay"
        else:
            # This handles diagonal moves or jumps of more than one cell
            return "Stay"


class Actions(str, Enum):
    NEAREST_TAVERN = "NEAREST_TAVERN"
    ENDGAME_TAVERN = "ENDGAME_TAVERN"
    TAKE_NEAREST_MINE = "TAKE_NEAREST_MINE"
    ATTACK_NEAREST = "ATTACK_NEAREST"
    ATTACK_RICHEST = "ATTACK_RICHEST"
    ATTACK_WEAKEST = "ATTACK_WEAKEST"
    SUICIDE = "SUICIDE"
    WAIT = "WAIT"
    DEFEND_MINE = "DEFEND_MINE"

class AIBase(ABC):
    def __init__(self, name: str = "UnknownAIName", key: str = "UnknownKey"):
        self.game: Game | None = None
        self.prev_life: int | None = None
        self.key = key  # Unique identifier for the AI instanceer for the AI instance
        self.name = name

    def clone_me(self):
        """Create a clone of the AI instance."""
        return self.__class__(name=self.name, key=self.key)

    def process(self, game: Game):
        self.game = game

    @abstractmethod
    def decide(self):
        """Decide the next move based on the current game state."""
        pass



    def mines(self):
        """Return a list of mine locations."""
        if self.game is None:
            return []
        return self.game.mines_locs

    def enemies(self):
        """Return a list of enemy heroes."""
        if self.game is None:
            return []
        me = self.game.hero
        return [h for h in self.game.heroes if h.bot_id != me.bot_id]

    def taverns(self):
        """Return a list of enemy heroes."""
        if self.game is None:
            return []
        return set(self.game.taverns_locs)

    def hero(self):
        """Return a list of enemy heroes."""
        if self.game is None:
            return None
        return self.game.hero



    def _package(self, path, action, decisions, hero_move):
        me = self.hero()
        taverns = self.taverns()
        mines = self.mines()
        enemies = self.enemies()
        print(f"{self.name}:  action: {action} hero_move: {hero_move}")
        nearest_enemy = (
            min(enemies, key=lambda e: abs(e.pos[0] - me.pos[0]) + abs(e.pos[1] - me.pos[1])).pos
            if enemies else me.pos
        )
        nearest_mine = (
            min(mines, key=lambda m: abs(m[0] - me.pos[0]) + abs(m[1] - me.pos[1])) if mines else me.pos
        )
        nearest_tavern = (
            min(taverns, key=lambda t: abs(t[0] - me.pos[0]) + abs(t[1] - me.pos[1])) if taverns else me.pos
        )
        self.prev_life = me.life

        return (
            path, action, decisions, str(hero_move), nearest_enemy, nearest_mine, nearest_tavern
        )
