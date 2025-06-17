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
        game_map = self.game.board_map
        game_map = replace_map_values(game_map, owned_mines, 'O')

        is_leading = all(hero.mine_count >= e.mine_count for e in enemies)

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

        def calculate_mine_value(distance):
            # Calculate if taking a mine is worth it based on remaining turns
            cost = 20  # HP cost to take mine
            turns_to_reach = distance
            turns_earning = remaining_turns - turns_to_reach
            if turns_earning <= 0:
                return False
            # Only take mine if we can earn back the HP cost in gold
            return turns_earning >= cost

        def defend_mines_if():
            # Check if any enemy is close to our mines
            for mine_pos in hero.mines:
                for enemy in enemies:
                    path, distance = bfs_from_xy_to_xy(game_map, enemy.pos, mine_pos)
                    if distance < 3 and hero.life > enemy.life + distance:
                        # Intercept enemy before they reach our mine
                        intercept_path, _ = bfs_from_xy_to_xy(game_map, hero.pos, path[0])
                        return intercept_path, Actions.DEFEND_MINE
            return None

        def end_game_if():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.TAVERN)

            if phase == "end" and is_leading and distance <= remaining_turns:
                return path, Actions.ENDGAME_TAVERN
            else:
                return None

        def do_nearest_if():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.MINE)
            if distance < remaining_turns and calculate_mine_value(distance):
                return path, Actions.TAKE_NEAREST_MINE
            else:
                return None

        def attack_richest_if():
            richest = enemies_by_mines[0]
            path, distance = bfs_from_xy_to_xy(game_map, hero.pos, richest.pos)
            # More aggressive attack if they have many mines
            if distance < remaining_turns and hero.life - distance - 1 >= richest.life and hero.life > critical_hp + distance * 5:
                # If they have many mines, be more aggressive
                if richest.mine_count >= 3:
                    return path, Actions.ATTACK_RICHEST
                # Otherwise only attack if we're significantly stronger
                elif hero.life > richest.life * 1.5:
                    return path, Actions.ATTACK_RICHEST
            return None

        def opportunistic_kill_if():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.ENEMY)
            if len(path) > 0:
                enemy_position = path[-1]
                enemy = [e for e in enemies if
                         e.pos[0] == enemy_position[0] and e.pos[1] == enemy_position[1]]
                if distance < 4 and len(enemy) > 0 and enemy[0].life <= hero.life - distance - 1:
                    return path, Actions.ATTACK_NEAREST
            return None

        def attack_nearest_if():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.ENEMY)
            if len(path) > 0:
                enemy_position = path[-1]
                enemy = [e for e in enemies if
                         e.pos[0] == enemy_position[0] and e.pos[1] == enemy_position[1]]
                if distance < remaining_turns and len(enemy) > 0 and enemy[0].life <= hero.life - distance - 1:
                    return path, Actions.ATTACK_NEAREST
            return None

        def attack_weakest_if():
            weakest = min(enemies, key=lambda e: e.life)
            path, distance = bfs_from_xy_to_xy(game_map, hero.pos, weakest.pos)
            if weakest.life < hero.life - distance - 1 and distance < remaining_turns:
                    return path, Actions.ATTACK_WEAKEST
            return None

        def go_to_tavern_if():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.TAVERN)
            # Only go to tavern if we have enough gold and the heal is worth it
            if (distance < remaining_turns and 
                hero.life < critical_hp and 
                hero.gold >= 2 and 
                # Only heal if we'll get good value from the heal
                (hero.life + 50 - distance) * hero.mine_count > 2):
                return path, Actions.NEAREST_TAVERN
            return None

        def suicide():
            if hero.mine_count == 0 and hero.gold == 0:
                path_1, distance_1 = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.ENEMY)
                path_2, distance_2 = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.MINE)
                path, distance = (path_1, distance_1) if distance_1 < distance_2 else (path_2, distance_2)
                if distance < remaining_turns * 2:
                    return path, Actions.SUICIDE
            return None

        def wait():
            return [hero.pos, hero.pos], Actions.WAIT

        policy_priority = [end_game_if,
                           defend_mines_if,
                           go_to_tavern_if,
                           opportunistic_kill_if,
                           do_nearest_if,
                           attack_richest_if,
                           attack_weakest_if,
                           attack_nearest_if,
                           suicide,
                           wait]
        path_and_action = None
        i = 0

        while path_and_action is None:
            path_and_action = policy_priority[i]()
            i += 1
        move = Directions.get_direction(hero.pos, path_and_action[0][1])
        # If nothing to do, stay still or chase random enemy mine
        return self._package(
            path=path_and_action[0],
            action=path_and_action[1],
            decisions=[path_and_action[1]],
            hero_move=move
        )