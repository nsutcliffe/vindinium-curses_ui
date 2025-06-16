
from models.ai_base import AIBase, Actions, MapElements, Directions
from utils.grid_helpers import replace_map_values
from utils.path_finder import bfs_from_xy_to_xy, bfs_from_xy_to_nearest_char


class AI(AIBase):

    def decide(self):
        hero = self.game.hero
        game = self.game
        remaining_turns = game.max_turns - game.turn
        enemies = [h for h in game.heroes if h.bot_id != hero.bot_id]
        enemies_by_mines = sorted(enemies, key=lambda h: h.mine_count, reverse=True)

        owned_mines = set(hero.mines)
        game_map = replace_map_values(self.game.board_map, owned_mines, MapElements.OWNED_MINE)

        just_respawned = (
                self.prev_life is not None and self.prev_life <= 0 and hero.life == 100
        )

        pct = game.turn / game.max_turns
        if just_respawned or pct < 0.25:
            phase = "opening"
        elif pct < 0.85:
            phase = "mid"
        else:
            phase = "end"

        critical_hp = 35 if phase == "opening" else 30 if phase == "mid" else 25

        def should_do_nearest_mine():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.MINE)
            if distance < remaining_turns:
                return path, Actions.TAKE_NEAREST_MINE
            else:
                return None

        def should_attack_richest():
            richest = enemies_by_mines[0]
            path, distance = bfs_from_xy_to_xy(game_map, hero.pos, richest.pos)
            if distance < remaining_turns and hero.life >= richest.life:
                return path, Actions.ATTACK_RICHEST
            else:
                return None

        def opportunistic_kill():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.ENEMY)
            if path:
                enemy_position = path[-1]
                enemy = [e for e in enemies if e.pos == enemy_position]
                if distance < 4 and enemy and enemy[0].life <= hero.life:
                    return path, Actions.ATTACK_NEAREST
            return None

        def should_attack_nearest():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.ENEMY)
            if path:
                enemy_position = path[-1]
                enemy = [e for e in enemies if e.pos == enemy_position]
                if distance < remaining_turns and enemy and enemy[0].life <= hero.life:
                    return path, Actions.ATTACK_NEAREST
            return None

        def should_go_to_tavern():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.TAVERN)
            if distance < remaining_turns and hero.life < critical_hp:
                return path, Actions.NEAREST_TAVERN
            return None

        def wait():
            return [hero.pos, hero.pos], Actions.WAIT

        policy_priority = [
            should_go_to_tavern,
            opportunistic_kill,
            should_do_nearest_mine,
            should_attack_richest,
            should_attack_nearest,
            wait
        ]

        path_and_action = None
        i = 0
        while path_and_action is None:
            path_and_action = policy_priority[i]()
            i += 1

        path, action = path_and_action
        path = self.inject_opportunistic_detour(path, action)

        move = Directions.get_direction(hero.pos, path[1]) if len(path) > 1 else Directions.STAY

        print(f"{self.name} has decided to: {action} and move to the {move}")
        return self._package(
            path=path,
            action=action,
            decisions=[action],
            hero_move=move
        )

    def inject_opportunistic_detour(self, path, action):
        hero = self.game.hero
        game_map = replace_map_values(self.game.board_map, set(hero.mines), MapElements.OWNED_MINE)

        detour_targets = []
        if action != Actions.NEAREST_TAVERN:
            detour_targets += [MapElements.TAVERN]
        if action != Actions.TAKE_NEAREST_MINE:
            detour_targets += [MapElements.MINE]
        if action not in [Actions.ATTACK_NEAREST, Actions.ATTACK_RICHEST, Actions.ATTACK_WEAKEST]:
            detour_targets += [MapElements.ENEMY]

        max_detour_cost = 3
        for i, pos in enumerate(path[:5]):
            for target_type in detour_targets:
                detour_path, detour_cost = bfs_from_xy_to_nearest_char(game_map, pos, target_type)
                if not detour_path or detour_cost > max_detour_cost:
                    continue

                rejoin_target = path[i + 1] if i + 1 < len(path) else path[-1]
                rejoin_path, rejoin_cost = bfs_from_xy_to_xy(game_map, detour_path[-1], rejoin_target)
                if rejoin_path and detour_cost + rejoin_cost <= max_detour_cost + 1:
                    return path[:i] + detour_path + rejoin_path[1:]

        return path
