import threading

from clients.basic_client import BasicClient
from clients.tui_client import Config
from models import DecisionMakingAI

# Local tournament for Vindinium AIs
# Configuration for the local tournament


ai_configs = [
    {"ai": DecisionMakingAI.AI(), "key": "6jbgism2"},
    {"ai": DecisionMakingAI.AI(), "key": "wwkeyefm"},
    {"ai": DecisionMakingAI.AI(), "key": "e8sfxp67"},
    {"ai": DecisionMakingAI.AI(), "key": "krvfyov4"}

]

base_config = dict(
    number_of_games=10,
    number_of_turns=10,
    map_name="m6",  # Map name: "m1", "m2", "m3", "m4", "m5", or "m6"
    game_mode="arena",
    server_url="http://localhost",
    delay=0.1
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
