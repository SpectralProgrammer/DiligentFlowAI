
from abc import ABC, abstractmethod
from collections.abc import Sequence

# Requires all models to have a chat method implemented
# Prevents mismatch/errors if the model is being changed in the future
class ModelStructure(ABC):
    @abstractmethod
    def chat(
        self,
        prompt: str | None = None,
        messages: Sequence[dict[str, str]] | None = None,
    ) -> str:
        # Sends prompt or conversation history to the model and returns the response
        pass
