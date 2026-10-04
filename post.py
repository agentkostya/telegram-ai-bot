import os
import requests
import random
import json
import sys
import time
import base64

# Загружаем настройки из секретов GitHub
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
HF_API_TOKEN = os.environ["HF_API_TOKEN"]

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
    """Генерируем текст через OpenRouter (проверенный рабочий вариант)"""
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
            "model": "qwen/qwen-2.5-7b-instruct:free",
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

def generate_image(image_prompt):
    """Генерируем картинку через Hugging Face FLUX (быстро, без водяных знаков, с защитой от сбоев)"""
    hf_url = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-schnell"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    payload = {"inputs": image_prompt + ", masterpiece, best quality, highly detailed, no text, no watermark"}
    
    print("🎨 Запрашиваем картинку у Hugging Face (FLUX)...")
    
    # Делаем до 3 попыток, чтобы обойти временные сбои сети GitHub Actions
    for attempt in range(3):
        try:
            hf_response = requests.post(hf_url, headers=headers, json=payload, timeout=90)
            
            if hf_response.status_code == 503:
                print(f"⏳ Модель загружается, пробуем еще раз (попытка {attempt + 1}/3)...")
                time.sleep(5)
                continue
                
            hf_response.raise_for_status()
            
            # Hugging Face возвращает саму картинку (байты)
            print("✅ Картинка успешно сгенерирована!")
            return hf_response.content
            
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Сетевая ошибка (попытка {attempt + 1}/3): {e}")
            if attempt == 2:
                raise Exception("Не удалось сгенерировать картинку после 3 попыток")
            time.sleep(5)

def send_to_telegram_with_photo(post_text, image_bytes):
    """Отправляем фото с текстом в Telegram"""
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
            raise ValueError("ИИ не вернул поля post_text или image_prompt")

    except Exception as e:
        print(f"❌ ОШИБКА генерации текста: {e}")
        sys.exit(1)

    print(f"📝 Текст поста: {post_text}")
    print(f"🎨 Промпт для картинки: {image_prompt}")

    try:
        image_bytes = generate_image(image_prompt)
    except Exception as e:
        print(f"❌ ОШИБКА генерации картинки: {e}")
        sys.exit(1)

    try:
        result = send_to_telegram_with_photo(post_text, image_bytes)
        print(f"✅ Готово! Message ID: {result['result']['message_id']}")
    except Exception as e:
        print(f"❌ ОШИБКА отправки в Telegram: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
