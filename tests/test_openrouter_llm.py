import os
import requests
from dotenv import load_dotenv


def main():
    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    model = os.getenv("OPENROUTER_MODEL", "openrouter/free")

    if not api_key:
        raise ValueError("Missing OPENROUTER_API_KEY in .env")

    url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "chatbot-rag-local-demo",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "Reply with one short sentence: API test successful."
            }
        ],
        "max_tokens": 200,
        "temperature": 0.1,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=60)
    data = response.json()

    print("Status code:", response.status_code)

    if response.status_code != 200:
        print(data)
        return

    answer = data["choices"][0]["message"]["content"]
    print("Answer:", answer)
    print("Usage:", data.get("usage"))


if __name__ == "__main__":
    main()