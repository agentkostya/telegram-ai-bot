import os
import requests
import random
import json
import urllib.parse

# Загружаем настройки из секретов GitHub
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

# Темы для постов
TOPICS = [
    "футуристические технологии и искусственный интеллект",
    "космос и удивительные открытия астрономии",
    "невероятные факты о природе и животных",
    "лайфхак для продуктивности и саморазвития",
    "загадки истории, которые не имеют ответа"
]

# Промпт, который заставляет ИИ вернуть строгий JSON
PROMPT_TEMPLATE = """Ты - профессиональный помощник для ведения Telegram-канала.
Тема: {topic}

Сгенерируй ответ СТРОГО в формате JSON с двумя полями:
1. "post_text": Короткий, живой пост на русском языке (3-5 предложений, с 1-2 эмодзи, без хештегов).
2. "image_prompt": Краткое, детальное визуальное описание картинки для генерации на АНГЛИЙСКОМ языке (например: "cinematic shot of a futuristic neon city, highly detailed, 8k resolution, dramatic lighting").

НЕ добавляй никакой другой текст, маркдаун или комментарии. Только валидный JSON."""

def generate_content():
    topic = random.choice(TOPICS)
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/agentkostya/telegram-ai-bot",
            "X-Title": "Telegram AI Bot",
        },
        json={
            # Используем модель, которая отлично понимает формат JSON
            "model": "nvidia/nemotron-3.5-lightning:free", 
            "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(topic=topic)}],
            "temperature": 0.8,
            "response_format": { "type": "json_object" } # Заставляем модель выдавать только JSON
        },
        timeout=60,
    )
    response.raise_for_status()
    result_text = response.json()["choices"][0]["message"]["content"]
    return json.loads(result_text)

def send_to_telegram_with_photo(post_text, image_prompt):
    # 1. Генерируем ссылку на картинку через Pollinations.ai (бесплатно, без ключа!)
    # Кодируем промпт для безопасной вставки в URL и добавляем случайное число (seed), чтобы картинки не повторялись
    encoded_prompt = urllib.parse.quote(image_prompt)
    random_seed = random.randint(1, 10000)
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={random_seed}"

    # 2. Отправляем в Telegram как фото с текстовой подписью
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    payload = {
        "chat_id": CHANNEL_ID,
        "photo": image_url,
        "caption": post_text,
        "parse_mode": "HTML"
    }
    
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()

def main():
    print("🤖 Генерируем текст и промпт для картинки...")
    try:
        content = generate_content()
        post_text = content.get("post_text", "Ошибка генерации текста")
        image_prompt = content.get("image_prompt", "beautiful cinematic landscape, highly detailed, 8k")
    except Exception as e:
        print(f"❌ Ошибка парсинга JSON: {e}")
        return

    print(f"📝 Текст поста: {post_text}")
    print(f"🎨 Промпт для картинки: {image_prompt}")

    print("📤 Отправляем фото с текстом в Telegram...")
    try:
        result = send_to_telegram_with_photo(post_text, image_prompt)
        print(f"✅ Готово! Message ID: {result['result']['message_id']}")
    except Exception as e:
        print(f"❌ Ошибка отправки в Telegram: {e}")

if __name__ == "__main__":
    main()
