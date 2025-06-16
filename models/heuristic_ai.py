#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Vindinium heuristic AI — **v3.2: marginal‑value mines & distance penalty**
=======================================================================

Two strategy tweaks requested:

1. **No hard mine cap.**  We now capture a mine whenever its *marginal value*
   (remaining turns minus rough breakeven) is positive, instead of stopping at
   7/5/2.
2. **Distance penalty.**  The farther the mine, the less attractive.  The rule
   used is

   ```python
   worth = remaining_turns – path_len – 10
   ```
   …so a mine one step away “pays for itself” if ≥ 10 turns remain; a mine 6
   steps away needs ≥ 16 turns, etc.

No other behaviour changed.  Still pure standard‑library.
"""

from collections import deque
from typing import List, Tuple, Any

from models.ai_base import AIBase


class AI(AIBase):
    """Phase‑aware greedy Vindinium bot adaptive to any max‑turn setting."""

    def decide(self):
        g = self.game
        me = g.hero
        turn: int = g.turn
        TOTAL: int = getattr(g, "max_turns", 150)
        remaining = TOTAL - turn

        # --------------------------------------------------------------
        # Phase detection + mini‑opening after respawn
        # --------------------------------------------------------------
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

        critical_hp = 35 if phase == "opening" else 30 if phase == "mid" else 25

        # --------------------------------------------------------------
        # Board state
        # --------------------------------------------------------------
        walls = set(g.walls_locs)
        taverns = set(g.taverns_locs)
        all_mines = set(g.mines_locs)
        owned_mines = set(getattr(me, "mines", []))
        mines = all_mines - owned_mines  # only neutral/enemy mines
        enemies = [h for h in g.heroes if h.bot_id != me.bot_id]

        # Path‑finding helpers ----------------------------------------
        mine_tiles = all_mines  # treat *every* mine as an obstacle unless it is our target

        def passable(pos):
            """Walkable if inside board, not a wall, and not a mine tile."""
            return (
                    0 <= pos[0] < g.board_size
                    and 0 <= pos[1] < g.board_size
                    and pos not in walls
                    and pos not in mine_tiles
            )

        def cardinal(pos):
            y, x = pos
            for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < g.board_size and 0 <= nx < g.board_size:
                    yield (ny, nx)

        def bfs(start, targets):
            """Breadth‑first search that treats mines as walls *except* if a mine is our target."""
            if not targets:
                return None, []
            if start in targets:
                return start, [start]
            q = deque([start])
            prev = {start: None}
            while q:
                cur = q.popleft()
                for nxt in cardinal(cur):
                    if nxt in prev:
                        continue
                    if nxt not in targets and not passable(nxt):
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

        # 1. Heal if low ------------------------------------------------
        if me.life <= critical_hp and taverns:
            tavern, path = bfs(me.pos, taverns)
            if path:
                dbg.append(("heal", tavern))
                return self._package(path, "Heal", dbg, first_step(path))

        # 2. Opportunistic kill ---------------------------------------
        for e in sorted(enemies, key=lambda h: h.life):
            if e.life > 40:
                continue
            _, path = bfs(me.pos, {e.pos})
            if path and len(path) - 1 <= 5:
                dbg.append(("kill", e.bot_id))
                return self._package(path, "Kill", dbg, first_step(path))

        # 3. Capture mine (marginal‑value rule) ------------------------
        if mines:
            mine, path = bfs(me.pos, mines)
            if path:
                path_len = len(path) - 1
                worth = remaining - path_len - 10  # 10‑turn breakeven + distance penalty
                if worth > 0:
                    dbg.append(("mine", mine, "worth", worth))
                    return self._package(path, "Mine", dbg, first_step(path))

        # 4. Default: hold --------------------------------------------
        return self._package(path=[me.pos], action="Hold", decisions=dbg, hero_move="Stay")

    # ---------------------------- helper -----------------------------


if __name__ == "__main__":
    print("AI module loaded – hand control to the engine.")
