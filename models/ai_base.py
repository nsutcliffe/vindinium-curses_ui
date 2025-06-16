from abc import ABC, abstractmethod
from collections import deque

from game import Game


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


    @staticmethod
    def bfs(start, targets, game, walls, mines):
        """Breadth‑first search that treats mines as walls *except* if a mine is our target."""
        if not targets:
            return None, []
        if start in targets:
            return start, [start]
        q = deque([start])
        prev = {start: None}
        while q:
            cur = q.popleft()
            for nxt in AIBase.cardinal(cur, game):
                if nxt in prev:
                    continue
                if nxt not in targets and not AIBase.passable(nxt, game, walls, mines):
                    continue
                prev[nxt] = cur
                if nxt in targets:
                    path = [nxt]
                    while path[-1] != start:
                        path.append(prev[path[-1]])
                    path.reverse()
                    return nxt, path
                q.append(nxt)
        return None, []

    @staticmethod
    def first_step(path):
        if len(path) < 2:
            return "Stay"
        (y0, x0), (y1, x1) = path[0], path[1]
        if y1 < y0:
            return "North"
        if y1 > y0:
            return "South"
        if x1 < x0:
            return "West"
        if x1 > x0:
            return "East"
        return "Stay"

    @staticmethod
    def passable(pos, game, walls, mine_tiles):
        """Walkable if inside board, not a wall, and not a mine tile."""
        return (
                0 <= pos[0] < game.board_size
                and 0 <= pos[1] < game.board_size
                and pos not in walls
                and pos not in mine_tiles
        )

    @staticmethod
    def cardinal(pos, game):
        y, x = pos
        for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            ny, nx = y + dy, x + dx
            if 0 <= ny < game.board_size and 0 <= nx < game.board_size:
                yield (ny, nx)

    def _package(self, path, action, decisions, hero_move):
        me = self.hero()
        taverns = self.taverns()
        mines = self.mines()
        enemies = self.enemies()

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
