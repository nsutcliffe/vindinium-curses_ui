# ---------------------------------------------------------------------------
#  Decision‑making AI
# ---------------------------------------------------------------------------
from collections import deque
from typing import Any, Tuple, List

from game import Game
from models.ai_base import AIBase


class AI(AIBase):
    """Horizon‑aware, greedy Vindinium bot."""

    def __init__(self, key="UnknownDecisionMakingAI"):
        super().__init__(key)

    def clone_me(self):
        """Create a clone of the AI instance."""
        return AI(self.key)

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
