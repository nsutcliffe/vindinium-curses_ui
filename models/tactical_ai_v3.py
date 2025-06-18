import os

from models.ai_base import AIBase, Actions, MapElements, Directions
from utils.grid_helpers import replace_map_values
from utils.path_finder import bfs_from_xy_to_xy, bfs_from_xy_to_nearest_char


class AI(AIBase):

    def decide(self):
        def get_nearest_mine_info():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.MINE)
            return path, distance

        def get_nearest_enemy_info():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.ENEMY)
            return path, distance

        def get_nearest_tavern_info():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.TAVERN)
            return path, distance

        def is_mine_worth_it(distance):
            # Calculate if taking a mine is worth it based on remaining turns
            cost = 20  # HP cost to take mine
            turns_to_reach = distance
            turns_earning = remaining_turns - turns_to_reach
            if turns_earning <= 0 or hero.life - cost - turns_to_reach < 1:
                return False

        def get_enemy_by_position(pos):
            enemy = [e for e in enemies if
                     e.pos[0] == pos[0] and e.pos[1] == pos[1]]
            if len(enemy) == 0:
                print(f"Position for enemy not found: {pos}, {enemies}")
                print(f"Position for enemy not found: {pos}, {enemies}")
                print(f"Position for enemy not found: {pos}, {enemies}")
                print(f"Position for enemy not found: {pos}, {enemies}")
            return enemy[0]

        hero = self.game.hero
        game = self.game
        remaining_turns = getattr(game, 'max_turns', 0) - getattr(game, 'turn', 0)
        enemies = [h for h in getattr(game, 'heroes', []) if
                   getattr(h, 'bot_id', None) != getattr(hero, 'bot_id', None)]
        enemies_by_mines = sorted(enemies, key=lambda h: getattr(h, 'mine_count', 0), reverse=True)
        owned_mines = set(getattr(hero, 'mines', []))
        game_map = getattr(self.game, 'board_map', [])
        game_map = replace_map_values(game_map, owned_mines, 'O')

        nearest_enemy_info = get_nearest_enemy_info()
        nearest_mine_info = get_nearest_enemy_info()
        nearest_tavern_info = get_nearest_tavern_info()

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

        def opportunistic_tavern_if():
            if nearest_tavern_info[1] < 2 and getattr(hero, 'gold', 0) >= 2 and getattr(hero, 'life', 100) < 65:
                return nearest_tavern_info[0], Actions.OPPORTUNISTIC_TAVERN

        def defend_mines_if():
            # Check if any enemy is close to our mines
            for mine_pos in hero.mines:
                for enemy in enemies:
                    path, distance = bfs_from_xy_to_xy(game_map, enemy.pos, mine_pos)

                    if distance < 3 and hero.life > enemy.life:
                        # Intercept enemy before they reach our mine
                        intercept_path, _ = bfs_from_xy_to_xy(game_map, hero.pos, enemy.pos)
                        return intercept_path, Actions.DEFEND_MINE
            return None

        def end_game_if():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.TAVERN)

            if phase == "end" and is_leading and distance <= remaining_turns:
                return path, Actions.ENDGAME_TAVERN
            else:
                return None

        def do_nearest_mine_if():
            path, distance = nearest_tavern_info
            if is_mine_worth_it(distance):
                return path, Actions.TAKE_NEAREST_MINE
            else:
                return None

        def attack_richest_if():
            richest = enemies_by_mines[0]
            path, distance = bfs_from_xy_to_xy(game_map, hero.pos, richest.pos)

            if distance < remaining_turns and hero.life - 1 >= richest.life:
                # If they have many mines, be more aggressive
                if richest.mine_count >= 3:
                    return path, Actions.ATTACK_RICHEST

            return None

        def opportunistic_kill_if():
            path, distance = nearest_enemy_info
            if len(path) > 0:
                enemy_position = path[-1]
                enemy = get_enemy_by_position(enemy_position)
                if distance < 4 and enemy.life <= hero.life - 1:
                    return path, Actions.ATTACK_NEAREST
            return None

        def attack_nearest_if():
            path, distance = nearest_enemy_info
            if len(path) > 0:
                enemy_position = path[-1]
                enemy = [e for e in enemies if
                         e.pos[0] == enemy_position[0] and e.pos[1] == enemy_position[1]]
                if distance < remaining_turns and len(enemy) > 0 and enemy[0].life <= hero.life - distance - 1:
                    return path, Actions.ATTACK_NEAREST
            return None

        def go_to_tavern_if():
            path, distance = nearest_tavern_info
            # Only go to tavern if we have enough gold and the heal is worth it
            if (distance < remaining_turns and
                    (hero.life < critical_hp or (hero.life < 65 and distance < 2)) and
                    (hero.gold >= 2 or distance * hero.mine_count >= 2)):
                return path, Actions.NEAREST_TAVERN
            return None

        def take_mine_with_refuel_if():
            for tavern in self.game.taverns_locs:
                # 2. Path to tavern
                path_to_tavern, dist_to_tavern = bfs_from_xy_to_xy(game_map, hero.pos, tavern)
                # 3. Path from tavern to target
                if len(path_to_tavern) > 0:
                    path_tavern_to_target, dist_tavern_to_target = bfs_from_xy_to_nearest_char(game_map, tavern,
                                                                                               MapElements.MINE)
                    # 4. Can we reach tavern before dying, and then target after healing?
                    if (hero.gold >= 2 and
                            100 - dist_tavern_to_target > 20):  # 100 = healed life
                        # Combine paths (avoid duplicate tavern node)
                        full_path = path_to_tavern + path_tavern_to_target[1:]
                        return full_path, Actions.TWO_STOP_MINE
            return None

        def kill_with_refuel_if():
            for tavern in self.game.taverns_locs:
                # 2. Path to tavern
                path_to_tavern, dist_to_tavern = bfs_from_xy_to_xy(game_map, hero.pos, tavern)
                # 3. Path from tavern to target
                if len(path_to_tavern) > 0:
                    path_tavern_to_target, dist_tavern_to_target = bfs_from_xy_to_nearest_char(game_map, tavern,
                                                                                               MapElements.ENEMY)
                    if len(path_tavern_to_target) > 0:
                        # 4. Can we reach tavern before dying, and then target after healing?
                        enemy = get_enemy_by_position(path_tavern_to_target[-1])
                        if 100 - dist_tavern_to_target > enemy.life:  # 100 = healed life
                            # Combine paths (avoid duplicate tavern node)
                            full_path = path_to_tavern + path_tavern_to_target[1:]
                            if len(full_path) < 2:
                                print("Path to tavern")
                                print(path_to_tavern)
                                print("Enemy")
                                print(enemy)
                                print("tavern to enemy")
                                print(path_tavern_to_target)
                            return full_path, Actions.TWO_STOP_ATTACK
            return None

        def run_if():
            """Return (path, Actions.RUN) for a move that increases distance from the nearest enemy, or stay if not possible."""

            # Find nearest enemy
            path, dist = nearest_enemy_info
            if not path or len(path) < 2:
                return None
            enemy_pos = path[-1]
            y, x = hero.pos
            moves = {
                Directions.NORTH: (y - 1, x),
                Directions.SOUTH: (y + 1, x),
                Directions.EAST: (y, x + 1),
                Directions.WEST: (y, x - 1),
                Directions.STAY: (y, x)
            }
            best_move = Directions.STAY
            best_dist = abs(y - enemy_pos[0]) + abs(x - enemy_pos[1])
            for direction, new_pos in moves.items():
                if (0 <= new_pos[0] < len(game_map) and 0 <= new_pos[1] < len(game_map[0]) and
                        game_map[new_pos[0]][new_pos[1]] in {' ', MapElements.HERO}):
                    dist_to_enemy = abs(new_pos[0] - enemy_pos[0]) + abs(new_pos[1] - enemy_pos[1])
                    if dist_to_enemy > best_dist:
                        best_move = direction
                        best_dist = dist_to_enemy
            if best_move == Directions.STAY:
                return None
            else:
                path = [hero.pos, moves[best_move]]
            return path, Actions.RUN

        def do_suicide_if():
            if hero.mine_count == 0 and hero.gold == 0:
                path_1, distance_1 = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.ENEMY)
                path_2, distance_2 = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.MINE)
                path, distance = (path_1, distance_1) if distance_1 < distance_2 else (path_2, distance_2)
                if distance < remaining_turns * 2:
                    return path, Actions.SUICIDE
            return None

        policy_names = [
            "opportunistic_tavern_if", "end_game_if", "defend_mines_if", "go_to_tavern_if", "opportunistic_kill_if",
            "do_nearest_mine_if", "attack_richest_if", "take_mine_with_refuel_if", "kill_with_refuel_if",
            "attack_nearest_if", "do_suicide_if", "run_if"
        ]
        policy_funcs = [
            opportunistic_tavern_if, end_game_if, defend_mines_if, go_to_tavern_if, opportunistic_kill_if,
            do_nearest_mine_if, attack_richest_if, take_mine_with_refuel_if, kill_with_refuel_if,
            attack_nearest_if, do_suicide_if, run_if
        ]
        policy_results = {}
        path_and_action = None

        for name, func in zip(policy_names, policy_funcs):
            result = func()
            policy_results[name] = result
            if result is not None:
                path_and_action = result
                break

        def wait(hero, game, policy_results, phase):
            # Extract game id from URL
            url = getattr(game, 'url', None)
            game_id = 'N/A'
            if url and isinstance(url, str):
                parts = url.rstrip('/').split('/')
                if parts:
                    game_id = parts[-1]
            nearest_mine_path, nearest_mine_dist = nearest_mine_info
            nearest_enemy_path, nearest_enemy_dist = nearest_enemy_info
            nearest_tavern_path, nearest_tavern_dist = nearest_tavern_info
            # Prepare map printout
            board_map = getattr(game, 'board_map', None)
            if board_map:
                if isinstance(board_map, list):
                    map_str = '\n'.join(''.join(str(cell) for cell in row) for row in board_map)
                else:
                    map_str = str(board_map)
            else:
                map_str = 'N/A'
            msg = (
                f"AI decided to WAIT.\n"
                f"Game id: {game_id}\n"
                f"Turn: {game.turn}/{game.max_turns}, phase: {phase}\n"
                f"Hero state: pos={hero.pos}, life={hero.life}, gold={hero.gold}, mines={hero.mine_count}\n"
                f"Policy results:\n"
            )
            for name, result in policy_results.items():
                msg += f"  {name}: {result}\n"
            msg += f"Nearest mine: path={nearest_mine_path}, distance={nearest_mine_dist}\n"
            msg += f"Nearest enemy: path={nearest_enemy_path}, distance={nearest_enemy_dist}\n"
            msg += f"Nearest tavern: path={nearest_tavern_path}, distance={nearest_tavern_dist}\n"
            msg += f"Game map:\n{map_str}\n"
            # Write to file in exceptions folder
            os.makedirs('exceptions', exist_ok=True)
            filename = f"exceptions/wait_exception_{game_id}_turn{getattr(game, 'turn', 'NA')}.log"
            with open(filename, 'w') as f:
                f.write(msg)
            raise Exception(msg)

        if path_and_action is None:
            wait(hero, game, policy_results, phase)
        try:
            move = Directions.get_direction(hero.pos, path_and_action[0][1])
            # If nothing to do, stay still or chase random enemy mine
            return self._package(
                path=path_and_action[0],
                action=path_and_action[1],
                decisions=[path_and_action[1]],
                hero_move=move
            )
        except Exception as e:
            print(path_and_action)
            raise e
