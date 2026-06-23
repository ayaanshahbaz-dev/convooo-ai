import requests
import json
import traceback
import datetime
import os

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

PERSONAS = {
    "default": "You are Convoo, a helpful, intelligent, and concise AI assistant.",
    "roaster": "You are a savage, witty, and highly sarcastic AI. You must roast the user brutally but playfully in every response. Spare no feelings, be creative and funny.",
    "coder": "You are an elite senior software engineer. Provide highly optimized, clean, and well-documented code. Explain complex concepts clearly without fluff."
}

def perform_web_search(query):
    if not DDGS:
        return "Web search is currently unavailable."
    try:
        # Try general web search
        results = list(DDGS().text(query, max_results=3))
        
        # If web search returns nothing or garbage, fallback to news search
        if not results:
            results = list(DDGS().news(query, max_results=3))
            
        if not results:
            return "No web results found."
        
        context = "Here are the latest web search results:\n\n"
        for i, res in enumerate(results):
            title = res.get('title', '')
            body = res.get('body', res.get('abstract', ''))
            url = res.get('href', res.get('url', ''))
            context += f"[{i+1}] {title}\n{body}\nURL: {url}\n\n"
        return context
    except Exception as e:
        return f"Web search failed: {str(e)}"

def get_ai_response_stream(user_text, history, persona="default", enable_search=False, global_memory=""):
    messages = []
    
    sys_prompt = PERSONAS.get(persona, PERSONAS["default"])
    
    current_dt = datetime.datetime.now().strftime("%A, %B %d, %Y %I:%M %p")
    sys_prompt += f"\n\nIMPORTANT FACT: The current system date and time is literally exactly {current_dt}. Do NOT say you don't know the day/date/time. Use this exact timestamp if asked."

    if global_memory:
        sys_prompt += f"\n\nContext about the user from previous chats:\n{global_memory}"
        
    messages.append({
        "role": "system",
        "content": sys_prompt
    })

    for msg in history:
        messages.append({"role": msg["role"], "content": msg["content"]})

    final_user_text = user_text
    if enable_search:
        search_results = perform_web_search(user_text)
        final_user_text = f"User Question: {user_text}\n\nSearch Results:\n{search_results}\n\nPlease answer the user's question using the search results provided."

    messages.append({"role": "user", "content": final_user_text})

    payload = {
        "model": "meta-llama/llama-3.1-8b-instruct",
        "messages": messages,
        "stream": True
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        with requests.post(OPENROUTER_URL, headers=headers, json=payload, stream=True) as response:
            if response.status_code != 200:
                yield f"\n\n**API Error:** {response.status_code}"
                return
            
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith('data: '):
                        data_str = decoded[6:]
                        if data_str.strip() == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except Exception:
                            pass
    except Exception as e:
        traceback.print_exc()
        yield "\n\n**Error:** Connection lost or service unavailable."

def get_ai_title(user_text):
    messages = [
        {"role": "system", "content": "You are a title generator. Respond ONLY with a short, 3-5 word title summarizing the user's message. Do not use quotes or punctuation at the end."},
        {"role": "user", "content": user_text}
    ]
    payload = {"model": "meta-llama/llama-3.1-8b-instruct", "messages": messages}
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    try:
        res = requests.post(OPENROUTER_URL, headers=headers, json=payload)
        data = res.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"].strip(' "')
        return user_text[:30] + "..."
    except Exception:
        return user_text[:30] + "..."