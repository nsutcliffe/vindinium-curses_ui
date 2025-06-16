from abc import ABC, abstractmethod

from game import Game


class AIBase(ABC):
    def __init__(self, key: str):
        self.game: Game | None = None
        self.prev_life: int | None = None
        self.key = key  # Unique identifier for the AI instanceer for the AI instance

    @abstractmethod
    def process(self, game: Game):
        pass
    @abstractmethod
    def decide(self):
        """Decide the next move based on the current game state."""
        pass
    @abstractmethod
    def clone_me(self):
        """Create a clone of the AI instance."""
        pass