from models.ai_base import AIBase, Actions, MapElements, Directions
from utils.path_finder import bfs_from_xy_to_nearest_char, bfs_from_xy_to_xy
from utils.grid_helpers import replace_map_values
from copy import deepcopy

class AI(AIBase):
    MINE_VALUE = 50
    ENEMY_MINE_PENALTY = 30
    LIFE_VALUE = 1
    GOLD_VALUE = 0.2
    DEATH_PENALTY = 1000
    TAVERN_BONUS = 20
    LOOKAHEAD_DEPTH = 3  # 2-ply minimax

    def decide(self):
        if self.game is None or getattr(self.game, 'hero', None) is None:
            return self._package(path=[(0, 0)], action=Actions.WAIT, decisions={}, hero_move=Directions.STAY)
        hero = self.game.hero
        game = self.game
        remaining_turns = getattr(game, 'max_turns', 0) - getattr(game, 'turn', 0)
        enemies = [h for h in getattr(game, 'heroes', []) if getattr(h, 'bot_id', None) != getattr(hero, 'bot_id', None)]
        owned_mines = set(getattr(hero, 'mines', []))
        game_map = replace_map_values(getattr(game, 'board_map', []), owned_mines, 'O')

        # Get all possible actions for the hero
        actions = self._get_possible_actions(game_map, hero, enemies, remaining_turns)
        if not actions:
            return self._package(path=[getattr(hero, 'pos', (0, 0))], action=Actions.WAIT, decisions={}, hero_move=Directions.STAY)

        best_action = None
        best_score = float('-inf')
        for action in actions:
            # Simulate this action and enemy's best response (2-ply minimax)
            sim_game, sim_hero, sim_enemies, sim_map = self._simulate_action(game, hero, enemies, game_map, action)
            score = self._min_value(sim_game, sim_hero, sim_enemies, sim_map, self.LOOKAHEAD_DEPTH - 1)
            if score > best_score:
                best_score = score
                best_action = action

        # Choose direction
        if best_action and len(best_action['path']) > 1:
            direction = Directions.get_direction(best_action['path'][0], best_action['path'][1])
        else:
            direction = Directions.STAY

        return self._package(
            path=best_action['path'] if best_action else [getattr(hero, 'pos', (0, 0))],
            action=best_action['action'] if best_action else Actions.WAIT,
            decisions={},
            hero_move=direction
        )

    def _get_possible_actions(self, game_map, hero, enemies, remaining_turns):
        actions = []
        # Go to tavern if low HP
        if getattr(hero, 'life', 100) < 40:
            path, dist = bfs_from_xy_to_nearest_char(game_map, getattr(hero, 'pos', (0, 0)), MapElements.TAVERN)
            if path and dist < remaining_turns:
                actions.append({'path': path, 'action': Actions.NEAREST_TAVERN})
        # Take nearest unowned mine
        path, dist = bfs_from_xy_to_nearest_char(game_map, getattr(hero, 'pos', (0, 0)), MapElements.MINE)
        if path and dist < remaining_turns and getattr(hero, 'life', 100) > 20 + dist:
            actions.append({'path': path, 'action': Actions.TAKE_NEAREST_MINE})
        # Attack nearest enemy if stronger
        for enemy in enemies:
            if getattr(hero, 'life', 100) > getattr(enemy, 'life', 100) + 10:
                path, dist = bfs_from_xy_to_xy(game_map, getattr(hero, 'pos', (0, 0)), getattr(enemy, 'pos', (0, 0)))
                if path and dist < remaining_turns:
                    actions.append({'path': path, 'action': Actions.ATTACK_NEAREST})
        # Wait as fallback
        actions.append({'path': [getattr(hero, 'pos', (0, 0)), getattr(hero, 'pos', (0, 0))], 'action': Actions.WAIT})
        return actions

    def _simulate_action(self, game, hero, enemies, game_map, action):
        # Deepcopy everything for simulation
        sim_game = deepcopy(game)
        sim_hero = deepcopy(hero)
        sim_enemies = deepcopy(enemies)
        sim_map = deepcopy(game_map)
        # Move hero
        if not action['path'] or len(action['path']) < 2:
            return sim_game, sim_hero, sim_enemies, sim_map
        next_pos = action['path'][1]
        sim_hero.pos = next_pos
        if action['action'] == Actions.NEAREST_TAVERN:
            sim_hero.life = min(100, sim_hero.life + 50)
            sim_hero.gold = max(0, sim_hero.gold - 2)
        elif action['action'] == Actions.TAKE_NEAREST_MINE:
            sim_hero.life -= 20
            if next_pos not in sim_hero.mines:
                sim_hero.mines.append(next_pos)
        elif action['action'] == Actions.ATTACK_NEAREST:
            for enemy in sim_enemies:
                if enemy.pos == next_pos:
                    enemy.life -= 20
                    if enemy.life <= 0:
                        sim_hero.gold += 10
        sim_hero.life -= 1  # Life cost per move
        # Mark owned mines with 'O'
        owned_mines = set(sim_hero.mines)
        if sim_map and owned_mines:
            sim_map = replace_map_values(sim_map, owned_mines, 'O')
        return sim_game, sim_hero, sim_enemies, sim_map

    def _min_value(self, game, hero, enemies, game_map, depth):
        if depth == 0 or getattr(hero, 'life', 0) <= 0:
            return self._evaluate_state(game, hero, enemies)
        # Simulate enemy's best move (assume only one enemy for simplicity)
        min_score = float('inf')
        for enemy in enemies:
            enemy_actions = self._get_possible_actions(game_map, enemy, [hero] + [e for e in enemies if e != enemy], getattr(game, 'max_turns', 0) - getattr(game, 'turn', 0))
            for action in enemy_actions:
                sim_game, sim_enemy, sim_heroes, sim_map = self._simulate_action(game, enemy, [hero] + [e for e in enemies if e != enemy], game_map, action)
                # Now it's our turn again
                score = self._max_value(sim_game, hero, enemies, sim_map, depth - 1)
                if score < min_score:
                    min_score = score
        return min_score

    def _max_value(self, game, hero, enemies, game_map, depth):
        if depth == 0 or getattr(hero, 'life', 0) <= 0:
            return self._evaluate_state(game, hero, enemies)
        max_score = float('-inf')
        actions = self._get_possible_actions(game_map, hero, enemies, getattr(game, 'max_turns', 0) - getattr(game, 'turn', 0))
        for action in actions:
            sim_game, sim_hero, sim_enemies, sim_map = self._simulate_action(game, hero, enemies, game_map, action)
            score = self._min_value(sim_game, sim_hero, sim_enemies, sim_map, depth - 1)
            if score > max_score:
                max_score = score
        return max_score

    def _evaluate_state(self, game, hero, enemies):
        # Score: mines, life, gold, penalize enemy mines, bonus for tavern proximity, big penalty for death
        score = len(getattr(hero, 'mines', [])) * self.MINE_VALUE
        score += getattr(hero, 'life', 0) * self.LIFE_VALUE
        score += getattr(hero, 'gold', 0) * self.GOLD_VALUE
        for enemy in enemies:
            score -= len(getattr(enemy, 'mines', [])) * self.ENEMY_MINE_PENALTY
        if getattr(hero, 'life', 0) <= 0:
            score -= self.DEATH_PENALTY
        # Bonus for being near a tavern if low HP
        if getattr(hero, 'life', 100) < 40:
            path, dist = bfs_from_xy_to_nearest_char(getattr(game, 'board_map', []), getattr(hero, 'pos', (0, 0)), MapElements.TAVERN)
            if dist < 3:
                score += self.TAVERN_BONUS
        return score 