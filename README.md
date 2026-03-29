# Backend Setup Guide

## 1. Clone the Repository

```bash
git clone https://github.com/heyamktr/Authorized-to-Act-Auth0-for-AI-Agents/tree/Backend-ONLY 
cd <your-repo-folder>/backend
```

---

## 2. Install Python Dependencies

Make sure you have **Python 3.9+** installed.

```bash
pip install -r requirements.txt
```

Expected result:

* All packages (`fastapi`, `uvicorn`, `pydantic`, `ollama`) install successfully
* No errors in the terminal

---

## 3. Install Ollama

Download and install Ollama:
https://ollama.com/download

Verify installation:

```bash
ollama --version
```

Expected output:

* A version number (e.g., `ollama version 0.x.x`)

---

## 4. Pull the Required Model

This project uses the **llama3:8b** model.

```bash
ollama pull llama3:8b
```

Expected output:

* Progress bar showing model download
* Final message indicating the model is ready

---

## 5. Start Ollama

Run:

```bash
ollama serve
```

Expected output:

* Message indicating the server is running (e.g., `Listening on localhost:11434`)

⚠️ Keep this terminal running — Ollama must stay active.

---

## 6. Run the Backend Server

In a **new terminal window**, run:

```bash
uvicorn main:app --reload
```

Expected output:

* Server startup logs
* Line similar to:

```
Uvicorn running on http://127.0.0.1:8000
```

---

## 7. Test the API (Swagger UI)

1. Open your browser and go to:

```
http://127.0.0.1:8000/docs
```

2. You will see the interactive API interface.

3. Find the **POST `/chat`** endpoint and click on it

4. Click the **"Try it out"** button

5. In the request body, enter:

```json
{
  "prompt": "How do I make pizza?"
}
```

6. Click **"Execute"**

Expected result:

* A response appears below with:

```json
{
  "response": "..."
}
```

* The response contains the AI-generated answer

---

## Troubleshooting

* **Internal Server Error**

  * Ensure Ollama is running (`ollama serve`)
  * Ensure model is installed (`ollama list`)

* **No response / hangs**

  * First request may take a few seconds while the model loads

* **Model not found**

```bash
ollama list
```

Make sure `llama3:8b` appears in the list

---

## Summary

You should now have:

* Ollama running locally
* `llama3:8b` model installed
* FastAPI server running
* `/chat` endpoint returning AI responses
