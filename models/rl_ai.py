from models.ai_base import AIBase, Actions, MapElements, Directions
from utils.path_finder import bfs_from_xy_to_nearest_char, bfs_from_xy_to_xy
from utils.grid_helpers import replace_map_values
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import random
from collections import deque
import math

class DQN(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(DQN, self).__init__()
        self.network = nn.Sequential(
            nn.Linear(input_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, output_size)
        )
    
    def forward(self, x):
        return self.network(x)

class AI(AIBase):
    MINE_GOLD_VALUE = 1
    TAVERN_HEAL_COST = 2
    TAVERN_HEAL_AMOUNT = 50
    LIFE_COST_PER_STEP = 1
    MINE_TAKE_COST = 20
    MIN_LIFE = 1
    
    def __init__(self, name="RLAI", key="YourKeyHere"):
        super().__init__(name, key)
        # RL parameters
        self.state_size = 12  # [hero_pos_x, hero_pos_y, hero_life, hero_gold, mine_count, 
                             # nearest_mine_dist, nearest_enemy_dist, nearest_tavern_dist,
                             # remaining_turns, board_size, is_leading, has_low_hp]
        self.action_size = 5  # [North, South, East, West, Stay]
        self.hidden_size = 64
        self.memory = deque(maxlen=10000)
        self.gamma = 0.95    # discount factor
        self.epsilon = 1.0   # exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.995
        self.learning_rate = 0.001
        self.batch_size = 32
        
        # Initialize DQN
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = DQN(self.state_size, self.hidden_size, self.action_size).to(self.device)
        self.target_model = DQN(self.state_size, self.hidden_size, self.action_size).to(self.device)
        self.optimizer = optim.Adam(self.model.parameters(), lr=self.learning_rate)
        self.update_target_model()
        
        # Game state tracking
        self.prev_state = None
        self.prev_action = None
        self.prev_reward = None
        
    def update_target_model(self):
        self.target_model.load_state_dict(self.model.state_dict())
        
    def get_state(self):
        """Convert game state to neural network input"""
        hero = self.game.hero
        game = self.game
        enemies = [h for h in game.heroes if h.bot_id != hero.bot_id]
        
        # Mark owned mines on the map
        owned_mines = set(hero.mines)
        game_map = replace_map_values(game.board_map, owned_mines, 'O')
        
        # Find nearest objects
        mine_path, mine_dist = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.MINE)
        enemy_path, enemy_dist = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.ENEMY)
        tavern_path, tavern_dist = bfs_from_xy_to_nearest_char(game_map, hero.pos, MapElements.TAVERN)
        
        # Calculate if leading
        is_leading = all(hero.mine_count >= e.mine_count for e in enemies)
        
        # Calculate if low HP
        has_low_hp = hero.life < 30
        
        return np.array([
            hero.pos[0] / game.board_size,  # Normalize position
            hero.pos[1] / game.board_size,
            hero.life / 100.0,  # Normalize life
            hero.gold / 100.0,  # Normalize gold
            hero.mine_count / 10.0,  # Normalize mine count
            mine_dist / game.board_size if mine_dist != float('inf') else 1.0,
            enemy_dist / game.board_size if enemy_dist != float('inf') else 1.0,
            tavern_dist / game.board_size if tavern_dist != float('inf') else 1.0,
            (game.max_turns - game.turn) / game.max_turns,
            1.0,  # board_size is constant
            1.0 if is_leading else 0.0,
            1.0 if has_low_hp else 0.0
        ])
        
    def get_reward(self):
        """Calculate reward based on game state changes"""
        hero = self.game.hero
        reward = 0
        
        # Reward for owning mines
        reward += hero.mine_count * 0.1
        
        # Reward for gold
        reward += hero.gold * 0.05
        
        # Penalty for low health
        if hero.life < 30:
            reward -= (30 - hero.life) * 0.1
            
        # Reward for being alive
        reward += 0.1
        
        return reward
        
    def act(self, state):
        """Choose action using epsilon-greedy policy"""
        if random.random() <= self.epsilon:
            return random.randrange(self.action_size)
        
        with torch.no_grad():
            state = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.model(state)
            return q_values.argmax().item()
            
    def remember(self, state, action, reward, next_state, done):
        """Store experience in replay memory"""
        self.memory.append((state, action, reward, next_state, done))
        
    def replay(self):
        """Train on a batch of experiences"""
        if len(self.memory) < self.batch_size:
            return
            
        minibatch = random.sample(self.memory, self.batch_size)
        states = torch.FloatTensor([i[0] for i in minibatch]).to(self.device)
        actions = torch.LongTensor([i[1] for i in minibatch]).to(self.device)
        rewards = torch.FloatTensor([i[2] for i in minibatch]).to(self.device)
        next_states = torch.FloatTensor([i[3] for i in minibatch]).to(self.device)
        dones = torch.FloatTensor([i[4] for i in minibatch]).to(self.device)
        
        current_q_values = self.model(states).gather(1, actions.unsqueeze(1))
        next_q_values = self.target_model(next_states).max(1)[0].detach()
        target_q_values = rewards + (1 - dones) * self.gamma * next_q_values
        
        loss = nn.MSELoss()(current_q_values.squeeze(), target_q_values)
        
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay
            
    def decide(self):
        hero = self.game.hero
        game = self.game
        
        # Get current state
        current_state = self.get_state()
        
        # Choose action
        action_idx = self.act(current_state)
        action_map = {
            0: "North",
            1: "South",
            2: "East",
            3: "West",
            4: "Stay"
        }
        direction = action_map[action_idx]
        
        # Calculate next position
        next_pos = hero.pos
        if direction == "North":
            next_pos = (hero.pos[0] - 1, hero.pos[1])
        elif direction == "South":
            next_pos = (hero.pos[0] + 1, hero.pos[1])
        elif direction == "East":
            next_pos = (hero.pos[0], hero.pos[1] + 1)
        elif direction == "West":
            next_pos = (hero.pos[0], hero.pos[1] - 1)
            
        # Validate move
        if (0 <= next_pos[0] < game.board_size and 
            0 <= next_pos[1] < game.board_size and 
            game.board_map[next_pos[0]][next_pos[1]] != '#'):
            path = [hero.pos, next_pos]
        else:
            path = [hero.pos]
            direction = "Stay"
            
        # Get reward
        reward = self.get_reward()
        
        # Store experience if we have a previous state
        if self.prev_state is not None:
            self.remember(self.prev_state, self.prev_action, reward, current_state, False)
            self.replay()
            
        # Update previous state and action
        self.prev_state = current_state
        self.prev_action = action_idx
        
        # Update target network periodically
        if game.turn % 100 == 0:
            self.update_target_model()
            
        return self._package(
            path=path,
            action=Actions.WAIT,  # We'll let the game handle the actual action based on the position
            decisions={},
            hero_move=direction
        ) 