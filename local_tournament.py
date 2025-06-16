import threading

from clients.basic_client import BasicClient
from clients.tui_client import Config
from models import decision_making_ai, heuristic_ai, random_ai, survival_bot, tactical_ai

# Local tournament for Vindinium AIs
# Configuration for the local tournament

# heuristic1: h6d870j3
# decisionmaking1: 0l2ymca1
# random1: 7177z2hc
# survival_bot: chvtv9cm
# clone_me
ai_configs = [
    {"ai": decision_making_ai.AI("decisionmaking1", "qarfl5z8"), "key": "qarfl5z8"},
    {"ai": heuristic_ai.AI("heuristic1", "hi4uk6g8"), "key": "hi4uk6g8"},
    {"ai": tactical_ai.AI("tactical1", "bar7j5gv"), "key": "bar7j5gv"},
    {"ai": survival_bot.AI("survivalbot1", "gntccajo"), "key": "gntccajo"}
]

base_config = dict(
    number_of_games=100,
    number_of_turns=30,
    map_name="m6",  # Map name: "m1", "m2", "m3", "m4", "m5", or "m6"
    game_mode="arena",
    server_url="http://localhost",
    delay=0
)
if __name__ == "__main__":
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
