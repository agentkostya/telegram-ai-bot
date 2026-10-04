import os
import requests
import random

# Загружаем настройки из секретов GitHub
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

# Темы для постов (можете поменять их под свой канал)
TOPICS = [
    "интересный факт о технологиях и будущем",
    "короткий совет по продуктивности",
    "мотивирующая мысль на день",
    "неочевидный лайфхак для повседневной жизни",
    "удивительный научный факт"
]

PROMPT_TEMPLATE = """Напиши короткий пост для Telegram-канала на русском языке.
Тема: {topic}

Требования:
- Длина: 3-5 предложений (до 500 символов)
- Стиль: живой, дружелюбный, без воды и клише
- В конце добавь 1-2 подходящих эмодзи
- НЕ используй хештеги
- НЕ пиши вступлений вроде "Вот интересный факт" или "Привет, подписчики"
- Выдай ТОЛЬКО готовый текст поста, без комментариев"""

def generate_post():
    topic = random.choice(TOPICS)
    prompt = PROMPT_TEMPLATE.format(topic=topic)

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/agentkostya/telegram-ai-bot",
            "X-Title": "Telegram AI Bot",
        },
        json={
            "model": "nvidia/nemotron-3.5-lightning:free",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
        },
        timeout=60,
    )
    
    # Эта строка покажет точную причину ошибки от OpenRouter, если она будет
    if response.status_code != 200:
        print(f"❌ Ошибка OpenRouter: {response.status_code} - {response.text}")
        
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        json={
            "chat_id": CHANNEL_ID,
            "text": text,
            "parse_mode": "HTML",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()

def main():
    print("🤖 Генерируем пост...")
    post = generate_post()
    print(f"📝 Текст поста:\n{post}\n")

    print("📤 Отправляем в Telegram...")
    result = send_to_telegram(post)
    print(f"✅ Готово! Message ID: {result['result']['message_id']}")

if __name__ == "__main__":
    main()
