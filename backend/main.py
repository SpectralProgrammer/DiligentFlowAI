
from fastapi import FastAPI
from pydantic import BaseModel
from model import Llama3

app = FastAPI()

def load_system_prompt():
    try:
        with open("backend/model_system_prompt.txt", "r") as f:
            return f.read()
    except FileNotFoundError:
        return None

system_prompt = load_system_prompt()

ai_model = Llama3(model="llama3.1:8b", system_prompt=system_prompt)


class ChatRequest(BaseModel):
    prompt: str # JSON -> {"prompt" : "..."} 

class ChatResponse(BaseModel):
    response: str # JSON -> {"response": "..."}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        response = ai_model.chat(prompt=request.prompt)
        return ChatResponse(response=response)
    except Exception as e:
        return {"error": str(e)}

@app.get("/")
async def root():
    return {"message":"Project is up and running"}