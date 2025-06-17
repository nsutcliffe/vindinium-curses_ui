import threading
import gc
import os
import torch
from models.rl_ai import AI as RLAI

# Configure garbage collection
gc.set_threshold(700, 10, 5)  # Increase thresholds to reduce collection frequency
gc.disable()  # Disable automatic garbage collection during tournament

# Create a shared model directory
MODEL_DIR = "models/rl_models"
os.makedirs(MODEL_DIR, exist_ok=True)

# Create a shared model instance
shared_model = RLAI("shared_model", "shared_key")
model_path = os.path.join(MODEL_DIR, "shared_model.pt")

# Load existing model if available
if os.path.exists(model_path):
    shared_model.model.load_state_dict(torch.load(model_path))
    shared_model.update_target_model()
    print("Loaded existing model from", model_path)

# Create RL agents that share the same model
ai_configs = [
    {"ai": RLAI("rl_agent_1", "g4c4a3h4"), "key": "g4c4a3h4"},
    {"ai": RLAI("rl_agent_2", "ed0doz0b"), "key": "ed0doz0b"},
    {"ai": RLAI("rl_agent_3", "4dt5ntfz"), "key": "4dt5ntfz"},
    {"ai": RLAI("rl_agent_4", "0op2xrnr"), "key": "0op2xrnr"}
]

# Share the model and memory between all agents
for config in ai_configs:
    config["ai"].model = shared_model.model
    config["ai"].target_model = shared_model.target_model
    config["ai"].memory = shared_model.memory
    config["ai"].optimizer = shared_model.optimizer

base_config = dict(
    number_of_games=500,
    number_of_turns=100,
    map_name="m6",  # Map name: "m1", "m2", "m3", "m4", "m5", or "m6"
    game_mode="arena",
    server_url="http://localhost",
    delay=0
)

def save_model():
    """Save the shared model periodically"""
    torch.save(shared_model.model.state_dict(), model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    try:
        from clients.basic_client import BasicClient
        from clients.tui_client import Config

        client_configs = [
            Config.from_dict({**base_config, **ai_config}) for ai_config in ai_configs
        ]
        clients = [BasicClient(config) for config in client_configs]

        input("Press Enter to launch the RL tournament...")

        # Start a thread to periodically save the model
        save_thread = threading.Thread(target=lambda: [
            save_model() for _ in range(base_config["number_of_games"] // 10)
        ])
        save_thread.daemon = True
        save_thread.start()

        # Start game threads
        threads = []
        for c in clients:
            t = threading.Thread(target=c.play)
            t.start()
            threads.append(t)

        # Wait for all games to complete
        for t in threads:
            t.join()

        # Save the final model
        save_model()
        print("Tournament completed.")

    finally:
        gc.enable()  # Re-enable garbage collection after tournament 