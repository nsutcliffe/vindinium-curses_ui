from enum import Enum
import copy

from models.ai_base import AIBase


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
            return "Invalid Move"


class Actions(str, Enum):
    NEAREST_TAVERN = "NEAREST_TAVERN"
    TAKE_NEAREST_MINE = "TAKE_NEAREST_MINE"
    ATTACK_NEAREST = "ATTACK_NEAREST"
    ATTACK_RICHEST = "ATTACK_RICHEST"
    ATTACK_WEAKEST = "ATTACK_WEAKEST"
    WAIT = "WAIT"


class AI(AIBase):
    def decide(self):
        max_depth = 5  # Set how many moves to plan ahead

        def forecast(state, path):
            # Simulate action effects step-by-step from given state and path
            hero = copy.deepcopy(state.hero)
            game = copy.deepcopy(state)

            for (r, c) in path[1:]:
                char = game.board_map[r][c]

                if char == MapElements.MINE:
                    hero.gold += 1
                    hero.mines.append((r, c))
                    game.board_map[r] = game.board_map[r][:c] + ' ' + game.board_map[r][c+1:]
                elif char == MapElements.TAVERN:
                    hero.life = min(100, hero.life + 50)
                    hero.gold -= 2
                elif char == MapElements.ENEMY:
                    enemy = next((e for e in game.heroes if e.pos == (r, c)), None)
                    if enemy and hero.life >= enemy.life:
                        hero.gold += enemy.mine_count  # Gain enemy mines as gold
                        hero.life -= enemy.life // 2
                    else:
                        hero.life = 0  # Death

                hero.pos = (r, c)
                hero.life -= 1

                if hero.life <= 0:
                    return -1  # Died, worst outcome

            return hero.gold

        def explore(state, depth):
            hero = state.hero
            best_gold = hero.gold
            best_path = [hero.pos]

            def dfs(current_pos, current_path, current_life, current_gold, visited):
                nonlocal best_gold, best_path
                if len(current_path) > depth:
                    return

                r, c = current_pos
                char = state.board_map[r][c]

                # Apply effects
                new_life = current_life - 1
                new_gold = current_gold

                if char == MapElements.MINE:
                    new_gold += 1
                elif char == MapElements.TAVERN:
                    new_life = min(100, new_life + 50)
                    new_gold -= 2
                elif char == MapElements.ENEMY:
                    enemy = next((e for e in state.heroes if e.pos == (r, c)), None)
                    if enemy and new_life >= enemy.life:
                        new_gold += enemy.mine_count
                        new_life -= enemy.life // 2
                    else:
                        return

                if new_life <= 0:
                    return

                if new_gold > best_gold:
                    best_gold = new_gold
                    best_path = list(current_path)

                directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]
                for dr, dc in directions:
                    nr, nc = r + dr, c + dc
                    if not (0 <= nr < len(state.board_map) and 0 <= nc < len(state.board_map[0])):
                        continue
                    if (nr, nc) in visited:
                        continue
                    if state.board_map[nr][nc] in ['#', 'X']:
                        continue

                    visited.add((nr, nc))
                    current_path.append((nr, nc))
                    dfs((nr, nc), current_path, new_life, new_gold, visited)
                    current_path.pop()
                    visited.remove((nr, nc))

            dfs(hero.pos, [hero.pos], hero.life, hero.gold, {hero.pos})
            return best_path

        best_path = explore(self.game, max_depth)
        move = Directions.get_direction(best_path[0], best_path[1]) if len(best_path) > 1 else Directions.STAY
        print(f"{self.name} forecasts path: {best_path}, best move: {move}")
        return self._package(
            path=best_path,
            action="FORECAST_MAXIMISE_GOLD",
            decisions=["FORECAST_MAXIMISE_GOLD"],
            hero_move=move
        )
