#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Vindinium Bot – horizon‑aware heuristic AI
=========================================

* Uses the official **`bot_id`** field everywhere (no `.id` fallback).
* When looking for a mine to capture, it **excludes mines you already own**, so
  the bot never targets a tile it controls.
* Works for any `maxTurns` length by scaling its phase boundaries.
* Pure Python ≥ 3.8; no external dependencies.

Modules
-------
* `Hero`, `Game` – light state wrappers for the server JSON.
* `AI` – the decision‑making brain. Instantiate *once*; call `process(state)`
  then `decide()` each turn.
"""

from collections import deque
from typing import Any, List, Tuple

# ---------------------------------------------------------------------------
#  Domain objects
# ---------------------------------------------------------------------------


class Hero:
    """A minimal mirror of the JSON hero structure."""

    def __init__(self, hero_dict: dict):
        self.bot_id: int = hero_dict["id"]  # ← server uses "id" in JSON
        self.life: int = hero_dict["life"]
        self.gold: int = hero_dict["gold"]
        self.pos: Tuple[int, int] = (hero_dict["pos"]["x"], hero_dict["pos"]["y"])
        self.spawn_pos: Tuple[int, int] = (
            hero_dict["spawnPos"]["x"],
            hero_dict["spawnPos"]["y"],
        )
        self.crashed: bool = hero_dict["crashed"]
        self.mine_count: int = hero_dict["mineCount"]
        self.mines: List[Tuple[int, int]] = []  # filled later by Game
        self.name: str = hero_dict["name"]
        # Optional fields missing on training bots
        self.elo: int = hero_dict.get("elo", 0)
        self.user_id: int = hero_dict.get("userId", 0)
        self.last_move: str | None = hero_dict.get("lastDir")


class Game:
    """Wrapper that parses the raw game JSON into handy structures."""

    def __init__(self, state: dict):
        self.state = state
        self.mines = {}  # Dictionary to store mine ownership
        self.mines_locs = []  # List of mine positions
        self.spawn_points_locs = {}
        self.taverns_locs = []
        self.hero = None
        self.heroes = []
        self.heroes_locs = []
        self.walls_locs = []
        self.url = None
        self.turn = None
        self.max_turns = None
        self.finished = None
        self.board_size = None
        self.board_map = []

        self.process_data(self.state)

    def process_data(self, state):
        """Parse the game state"""
        self.set_url(state['viewUrl'])
        self.process_hero(state['hero'])
        self.process_game(state['game'])

    def set_url(self, url):
        """Set the game object url var"""
        self.url = url

    def process_hero(self, hero):
        """Process the hero data"""
        self.hero = Hero(hero)

    def process_game(self, game):
        """Process the game data"""
        process = {'board': self.process_board,
                    'heroes': self.process_heroes}
        self.turn = game['turn']
        self.max_turns = game['maxTurns']
        self.finished = game['finished']
        for key in sorted(game.keys()):  # TODO: board must go before heroes
            if key in process:
                process[key](game[key])

    def process_board(self, board):
        """Process the board datas
            - Retrieve walls locs, tavern locs
            - Converts tiles in a displayable form"""
        self.board_size = board['size']
        tiles = board['tiles']
        map_line = ""
        char = None
        for y in range(0, len(tiles), self.board_size * 2):
            line = tiles[y:y+self.board_size*2]
            for x in range(0, len(line), 2):
                tile = line[x:x+2]
                tile_coords = (y//self.board_size//2, x//2)
                if tile[0] == " ":
                    # It's passable
                    char = " "
                elif tile[0] == "#":
                    # It's a wall
                    char = "#"
                    self.walls_locs.append(tile_coords)
                elif tile[0] == "$":
                    # It's a mine
                    char = "$"
                    self.mines_locs.append(tile_coords)
                    # Handle mine ownership: '-' means no owner, otherwise it's a player ID
                    owner = tile[1]
                    if owner == '-':
                        self.mines[tile_coords] = None  # No owner
                    else:
                        self.mines[tile_coords] = int(owner)
                        if owner == str(self.hero.bot_id):
                            # This mine belongs to me
                            self.hero.mines.append(tile_coords)
                elif tile[0] == "[":
                    # It's a tavern
                    char = "T"
                    self.taverns_locs.append(tile_coords)
                elif tile[0] == "@":
                    # It's a hero
                    char = "H"
                    if not int(tile[1]) == self.hero.bot_id:
                        # I don't want to be put in an array !
                        # I'm not a number, i'm a free bot:-)
                        self.heroes_locs.append(tile_coords)
                    else:
                        # And I want to be differenciated
                        char = "@"
                map_line = map_line + str(char)
            self.board_map.append(map_line)
            map_line = ""

    def process_heroes(self, heroes: list):
        for h in heroes:
            self.spawn_points_locs[(h["spawnPos"]["y"], h["spawnPos"]["x"])] = h["id"]
            hero_obj = Hero(h)
            self.heroes.append(hero_obj)
            # Mark spawn on map unless occupied by hero char
            line = list(self.board_map[hero_obj.spawn_pos[1]])
            if line[hero_obj.spawn_pos[0]] not in {"@", "H"}:
                line[hero_obj.spawn_pos[0]] = "X"
            self.board_map[hero_obj.spawn_pos[1]] = "".join(line)


# ---------------------------------------------------------------------------
#  Decision‑making AI
# ---------------------------------------------------------------------------


class AI:
    """Horizon‑aware, greedy Vindinium bot."""

    def __init__(self):
        self.game: Game | None = None
        self.prev_life: int | None = None

    # ---------------------- engine entry points ----------------------

    def process(self, game: Game):
        self.game = game

    def decide(self):
        g = self.game
        me = g.hero  # type: ignore [assignment]
        turn = g.turn
        TOTAL = g.max_turns
        remaining = TOTAL - turn

        # Phase detection (percentage)
        just_respawned = (
            self.prev_life is not None and self.prev_life <= 0 and me.life == 100
        )
        pct = turn / TOTAL
        if just_respawned or pct < 0.25:
            phase = "opening"
        elif pct < 0.85:
            phase = "mid"
        else:
            phase = "end"

        want_mines = 7 if phase == "opening" else 5 if phase == "mid" else 2
        critical_hp = 35 if phase == "opening" else 30 if phase == "mid" else 25

        # Sets for fast look‑ups
        walls = set(g.walls_locs)
        taverns = set(g.taverns_locs)
        mines_all = set(g.mines_locs)
        my_mines = set(me.mines)
        mines = mines_all - my_mines  # ← ignore mines we already own
        enemies = [h for h in g.heroes if h.bot_id != me.bot_id]

        # Path‑finding helpers -------------------------------------------------

        def passable(pos):
            y, x = pos
            return 0 <= y < g.board_size and 0 <= x < g.board_size and pos not in walls

        def neighbours(pos):
            y, x = pos
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nxt = (y + dy, x + dx)
                if passable(nxt):
                    yield nxt

        def bfs(start, targets):
            if start in targets:
                return start, [start]
            q = deque([start])
            prev = {start: None}
            while q:
                cur = q.popleft()
                for nxt in neighbours(cur):
                    if nxt in prev:
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

        dbg: List[Tuple[str, Any]] = [("phase", phase)]

        # --------------------------------------------------------------
        # 1. Heal low HP
        if me.life <= critical_hp and taverns:
            tavern, path = bfs(me.pos, taverns)
            dbg.append(("heal@", tavern))
            return self._package(path, "Heal", dbg, first_step(path), enemies, mines_all, taverns, me)

        # --------------------------------------------------------------
        # 2. Opportunistic kill (≤40 HP enemy within 5 steps)
        for e in sorted(enemies, key=lambda h: h.life):
            if e.life > 40:
                continue
            _, path = bfs(me.pos, {e.pos})
            if path and len(path) - 1 <= 5:
                dbg.append(("kill", e.bot_id))
                return self._package(path, "Kill", dbg, first_step(path), enemies, mines_all, taverns, me)

        # --------------------------------------------------------------
        # 3. Capture mine (ROI‑aware)
        BREAKEVEN = 20
        if remaining > BREAKEVEN and len(my_mines) < want_mines and mines:
            mine, path = bfs(me.pos, mines)
            dbg.append(("mine@", mine))
            return self._package(path, "Mine", dbg, first_step(path), enemies, mines_all, taverns, me)

        # --------------------------------------------------------------
        # 4. Default – hold position
        return self._package([me.pos], "Hold", dbg, "Stay", enemies, mines_all, taverns, me)

    # ------------------------------------------------------------------
    # Tuple packaging
    # ------------------------------------------------------------------

    def _package(self, path, action, decisions, hero_move, enemies, mines_all, taverns, me):
        nearest_enemy = (
            min(enemies, key=lambda e: abs(e.pos[0] - me.pos[0]) + abs(e.pos[1] - me.pos[1])).pos
            if enemies
            else me.pos
        )
        nearest_mine = (
            min(mines_all, key=lambda m: abs(m[0] - me.pos[0]) + abs(m[1] - me.pos[1]))
            if mines_all
            else me.pos
        )
        nearest_tavern = (
            min(taverns, key=lambda t: abs(t[0] - me.pos[0]) + abs(t[1] - me.pos[1]))
            if taverns
            else me.pos
        )
        self.prev_life = me.life  # update for next turn
        return (
            path,
            action,
            decisions,
            hero_move,
            nearest_enemy,
            nearest_mine,
            nearest_tavern,
        )


# ---------------------------------------------------------------------------
#  Stand‑alone run hook (useful for local debugging)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("This module is intended to be imported by the Vindinium starter‑kit.")
