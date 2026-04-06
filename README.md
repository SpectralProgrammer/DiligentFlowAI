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

* All packages (`fastapi`, `uvicorn`, `pydantic`) install successfully
* No errors in the terminal

---

## 3. Get a Gemini API Key

Create an API key in Google AI Studio:
https://aistudio.google.com/app/apikey

Add it to your backend environment:

```bash
GEMINI_API_KEY=your_key_here
```

Expected output:

* The key is available to the backend process

---

## 4. Choose a Gemini Model

This project defaults to **gemini-2.0-flash**.

```bash
GEMINI_MODEL=gemini-2.0-flash
```

Expected output:

* The model name is available to the backend process

---

## 5. Run the Backend Server

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

## 6. Test the API (Swagger UI)

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

  * Ensure `GEMINI_API_KEY` is set
  * Ensure the backend has internet access

* **No response / hangs**

  * Retry and check the backend logs for Gemini API errors

* **Invalid API key**

```bash
echo %GEMINI_API_KEY%
```

Make sure the key is present and valid

---

## Summary

You should now have:

* Gemini API key configured
* FastAPI server running
* `/chat` endpoint returning AI responses
