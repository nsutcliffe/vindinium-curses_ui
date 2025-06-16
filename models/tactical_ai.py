from enum import Enum

from models.ai_base import AIBase
from utils.grid_helpers import replace_map_values
from utils.path_finder import bfs_from_xy_to_xy, bfs_from_xy_to_nearest_char


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
            return "Invalid Move"


class Actions(str, Enum):
    NEAREST_TAVERN = "NEAREST_TAVERN"
    ENDGAME_TAVERN = "ENDGAME_TAVERN"
    TAKE_NEAREST_MINE = "TAKE_NEAREST_MINE"
    ATTACK_NEAREST = "ATTACK_NEAREST"
    ATTACK_RICHEST = "ATTACK_RICHEST"
    ATTACK_WEAKEST = "ATTACK_WEAKEST"
    WAIT = "WAIT"


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

        def end_game_if():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.TAVERN)

            if phase == "end" and is_leading and distance <= remaining_turns:
                return path, Actions.ENDGAME_TAVERN
            else:
                return None

        def do_nearest_if():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.MINE)
            if distance < remaining_turns:
                return path, Actions.TAKE_NEAREST_MINE
            else:
                return None

        def attack_richest_if():
            richest = enemies_by_mines[0]
            path, distance = bfs_from_xy_to_xy(game_map, hero.pos, richest.pos)
            if distance < remaining_turns and hero.life >= richest.life and hero.life > critical_hp + distance * 5:
                return path, Actions.ATTACK_RICHEST
            else:
                return None

        def opportunistic_kill_if():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.ENEMY)
            enemy_position = path[-1]
            enemy = [e for e in enemies if
                     e.pos[0] == enemy_position[0] and e.pos[1] == enemy_position[1]]
            if distance < 4 and len(enemy) > 0 and enemy[0].life <= hero.life:
                return path, Actions.ATTACK_NEAREST
            return None

        def attack_nearest_if():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.ENEMY)
            enemy_position = path[-1]
            enemy = [e for e in enemies if
                     e.pos[0] == enemy_position[0] and e.pos[1] == enemy_position[1]]
            if distance < remaining_turns and len(enemy) > 0 and enemy[0].life <= hero.life:
                return path, Actions.ATTACK_NEAREST
            return None

        def attack_weakest_if():
            weakest = min(enemies, key=lambda e: e.life)
            if weakest.life < hero.life:
                path, distance = bfs_from_xy_to_xy(game_map, hero.pos, weakest.pos)
                if distance < remaining_turns:
                    return path, Actions.ATTACK_WEAKEST
            return None

        def go_to_tavern_if():
            path, distance = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.TAVERN)
            if distance < remaining_turns and hero.life < critical_hp:
                return path, Actions.NEAREST_TAVERN
            return None

        def wait():
            return [], Actions.WAIT

        policy_priority = [end_game_if,
                           go_to_tavern_if,
                           opportunistic_kill_if,
                           do_nearest_if,
                           attack_richest_if,
                           attack_weakest_if,
                           attack_nearest_if,
                           wait]
        path_and_action = None
        i = 0

        while path_and_action is None:
            path_and_action = policy_priority[i]()
            i += 1
        move = Directions.get_direction(hero.pos, path_and_action[0][1])
        # If nothing to do, stay still or chase random enemy mine
        print(f"{self.name} has decided to: {path_and_action[1]} and move to the {move}")
        return self._package(
            path=path_and_action[0],
            action=path_and_action[1],
            decisions=[path_and_action[1]],
            hero_move=move
        )
