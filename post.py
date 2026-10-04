import os
import requests
import random
import json
import sys

# Загружаем настройки из секретов GitHub
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
HF_API_TOKEN = os.environ["HF_API_TOKEN"] # Новый ключ для картинок

TOPICS = [
    "футуристические технологии и искусственный интеллект",
    "космос и удивительные открытия астрономии",
    "невероятные факты о природе и животных",
    "лайфхак для продуктивности и саморазвития",
    "загадки истории, которые не имеют ответа"
]

PROMPT_TEMPLATE = """Ты - профессиональный помощник для ведения Telegram-канала.
Тема: {topic}

Сгенерируй ответ СТРОГО в формате JSON с двумя полями:
1. "post_text": Короткий, живой пост на русском языке (3-5 предложений, с 1-2 эмодзи, без хештегов).
2. "image_prompt": Краткое, детальное визуальное описание картинки для генерации на АНГЛИЙСКОМ языке (например: "cinematic shot of a futuristic neon city, highly detailed, 8k resolution, dramatic lighting, no text, no watermark").

НЕ добавляй никакой другой текст, маркдаун (типа ```json) или комментарии. Только валидный JSON."""

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
            "model": "nvidia/nemotron-3.5-lightning:free",
            "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(topic=topic)}],
            "temperature": 0.8,
            "response_format": { "type": "json_object" }
        },
        timeout=60,
    )
    response.raise_for_status()
    result_text = response.json()["choices"][0]["message"]["content"]

    # Очищаем ответ от возможных маркдаун-оберток
    result_text = result_text.strip()
    if result_text.startswith("```json"): result_text = result_text[7:]
    if result_text.startswith("```"): result_text = result_text[3:]
    if result_text.endswith("```"): result_text = result_text[:-3]
    result_text = result_text.strip()

    return json.loads(result_text)

def send_to_telegram_with_photo(post_text, image_prompt):
    # 1. Генерируем картинку через Hugging Face (Stable Diffusion XL - без водяных знаков!)
    hf_url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": image_prompt}
    
    print("🎨 Запрашиваем картинку у Hugging Face...")
    hf_response = requests.post(hf_url, headers=headers, json=payload, timeout=90)
    
    # Если модель "загружается" (бывает на бесплатном тарифе), Hugging Face вернет ошибку. 
    # Мы её перехватим, чтобы вы видели причину.
    if hf_response.status_code == 503:
        raise Exception("Модель Hugging Face сейчас загружается. Просто запустите workflow еще раз через минуту!")
    hf_response.raise_for_status()
    
    # Hugging Face возвращает саму картинку (байты), а не ссылку
    image_bytes = hf_response.content

    # 2. Отправляем в Telegram как файл (фото)
    tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    files = {
        'photo': ('image.jpg', image_bytes, 'image/jpeg')
    }
    data = {
        'chat_id': CHANNEL_ID,
        'caption': post_text,
        'parse_mode': 'HTML'
    }
    
    print("📤 Отправляем фото с текстом в Telegram...")
    tg_response = requests.post(tg_url, files=files, data=data, timeout=30)
    tg_response.raise_for_status()
    return tg_response.json()

def main():
    print("🤖 Генерируем текст и промпт для картинки...")
    try:
        content = generate_content()
        post_text = content.get("post_text")
        image_prompt = content.get("image_prompt")

        if not post_text or not image_prompt:
            raise ValueError("ИИ не вернул поля post_text или image_prompt в JSON")

    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА генерации: {e}")
        sys.exit(1)

    print(f"📝 Текст поста: {post_text}")
    print(f"🎨 Промпт для картинки: {image_prompt}")

    try:
        result = send_to_telegram_with_photo(post_text, image_prompt)
        print(f"✅ Готово! Message ID: {result['result']['message_id']}")
    except Exception as e:
        print(f"❌ КРИТИЧЕСКАЯ ОШИБКА отправки в Telegram: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
