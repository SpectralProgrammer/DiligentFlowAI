
from ollama import chat
from base import ModelStructure

# Currently usimg llama3.1:8b from ollama
class Llama3(ModelStructure):
    def __init__(self, model:str = None, system_prompt: str = None, api_key: str = None):
        self.model = model
        self.api_key = api_key # if you using an model API, insert API key here
        self.system_prompt = system_prompt
    
    def chat(self, prompt: str) -> str:
        if self.system_prompt != None:
            prompt = f"{self.system_prompt}\n\n{prompt}"
        response = chat(
            model = self.model,
            messages = [{"role": "user", "content": prompt}],
        )
        return response["message"]["content"]
