import threading
import gc

# Configure garbage collection
gc.set_threshold(700, 10, 5)  # Increase thresholds to reduce collection frequency
gc.disable()  # Disable automatic garbage collection during tournament

from clients.basic_client import BasicClient
from clients.tui_client import Config
from models import decision_making_ai, heuristic_ai, random_ai, survival_bot, tactical_ai, tactical_with_detour, \
    forecasting_ai, plan_ahead_ai, tactical_ai_v2, risk_reward_ai, hybrid_ai, pattern_ai

# Local tournament for Vindinium AIs
# Configuration for the local tournament

# heuristic1: h6d870j3
# decisionmaking1: 0l2ymca1
# random1: 7177z2hc
# survival_bot: chvtv9cm
# clone_me
ai_configs = [
    # {"ai": tactical_with_detour.AI("tactical_with_detour", "9fozp368"), "key": "9fozp368"},
    # {"ai": forecasting_ai.AI("forecasting_ai_1", "fkbkkzfh"), "key": "fkbkkzfh"},
    # {"ai": forecasting_ai.AI("dynamic_pr_1", "djt4l0fh"), "key": "djt4l0fh"},
    
    # {"ai": plan_ahead_ai.AI("plan_ahead_1", "7wfi0qb3"), "key": "7wfi0qb3"},
    #{"ai": heuristic_ai.AI("heuristic1", "hi4uk6g8"), "key": "hi4uk6g8"},
    #{"ai": tactical_ai.AI("tactical_v1", "smzjvxeb"), "key": "smzjvxeb"},
    # {"ai": survival_bot.AI("survivalbot1", "gntccajo"), "key": "gntccajo"}
    {"ai": tactical_ai_v2.AI("tactical_v2", "mtthsi5p"), "key": "mtthsi5p"},
    {"ai": risk_reward_ai.AI("risk_reward_v1", "3n38jgzg"), "key": "3n38jgzg"},
    {"ai": hybrid_ai.AI("hybrid_v1", "10k139up"), "key": "10k139up"},
    {"ai": pattern_ai.AI("pattern_v1", "d1p8mz5x"), "key": "d1p8mz5x"}


]

base_config = dict(
    number_of_games=500,
    number_of_turns=100,
    map_name="m6",  # Map name: "m1", "m2", "m3", "m4", "m5", or "m6"
    game_mode="arena",
    server_url="http://localhost",
    delay=0
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
