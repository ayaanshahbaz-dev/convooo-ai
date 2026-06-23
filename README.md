# Convoo.ai

A full-stack real-time AI chat platform built with Django and vanilla frontend technologies. It features streaming responses, persistent memory, and live web-augmented AI interactions using Llama 3.1 via OpenRouter.

---

## 🚀 Features

* Real-time token streaming (like ChatGPT-style responses)
* Persistent chat sessions with database storage
* Local + cross-session memory system
* Live web search integration (DuckDuckGo-based retrieval)
* Dynamic AI personas (Coder, Default, etc.)
* Auto-generated chat titles
* Markdown rendering with code highlighting
* Copy-to-clipboard code blocks
* Clean glassmorphic UI (no frameworks)

---

## 🧠 Architecture

Frontend (Vanilla JS)

* Sends user messages via fetch API
* Streams response using ReadableStream
* Renders markdown in real time

Backend (Django)

* Handles authentication and sessions
* Stores messages in SQLite
* Builds prompt with memory + persona + web data
* Streams response using StreamingHttpResponse

AI Layer (ai.py)

* Injects system time
* Adds memory context
* Optionally performs web search
* Sends request to OpenRouter (Llama 3.1)

---

## 🛠 Tech Stack

* Django (Backend)
* Python
* Vanilla JavaScript
* HTML/CSS (Glassmorphism UI)
* SQLite (Database)
* OpenRouter API (Llama 3.1 8B)
* DuckDuckGo Search (ddgs)
* marked.js (Markdown rendering)

---

## ⚙️ Setup Instructions

```bash
git clone https://github.com/ayaanshahbaz-dev/convooo-ai.git
cd convooo-ai
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python manage.py runserver
```

Create `.env` file:

```
OPENROUTER_API_KEY=your_key_here
```

---

## 📌 Status

This project is actively developed and serves as a portfolio-grade AI engineering project demonstrating real-time streaming and LLM orchestration.

---

## 📷 Screenshots

(Add screenshots here)

---

## 🔗 Live Demo

Coming soon
