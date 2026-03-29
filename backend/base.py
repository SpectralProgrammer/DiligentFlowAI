
from abc import ABC, abstractmethod

# Requires all models to have a chat method implemented
# Prevents mismatch/errors if the model is being changed in the future
class ModelStructure(ABC):
    @abstractmethod
    def chat(self, prompt: str) -> str:
        # Sends prompt to the model and returns the response
        pass