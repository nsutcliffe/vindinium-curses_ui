import gc
import threading

# Configure garbage collection
gc.set_threshold(700, 10, 5)  # Increase thresholds to reduce collection frequency
gc.disable()  # Disable automatic garbage collection during tournament

from clients.basic_client import BasicClient
from clients.tui_client import Config
from models import heuristic_ai, tactical_ai_v2, risk_reward_ai, murder_bot_working_copy

# Local tournament for Vindinium AIs
# Configuration for the local tournament

ai_configs = [

    {"ai": heuristic_ai.AI("heuristic1", "rhjcaktk"), "key": "rhjcaktk"},
    {"ai": tactical_ai_v2.AI("tactical_v2", "2c6zjpf2"), "key": "2c6zjpf2"},
    {"ai": risk_reward_ai.AI("risk_reward_v1", "afqfyt87"), "key": "afqfyt87"},
    {"ai": murder_bot_working_copy.AI("murder_bot_v1", "mt5h908j"), "key": "mt5h908j"}

]

base_config = dict(
    number_of_games=500,
    number_of_turns=100,
    map_name="m6",  
    game_mode="arena",
    server_url="http://localhost",
    delay=0# Map name: "m1", "m2", "m3", "m4", "m5", or "m6"
)
if __name__ == "__main__":
    try:
        client_configs = [
            Config.from_dict({**base_config, **ai_config}) for ai_config in ai_configs
        ]
        clients = [BasicClient(config) for config in client_configs]

        input("Press Enter to launch the tournament...")

        threads = []
        for c in clients:
            t = threading.Thread(target=c.play)
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        print("Tournament completed.")
    finally:
        gc.enable()  # Re-enable garbage collection after tournament
