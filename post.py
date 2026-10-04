import os
import requests
import random
import json
import sys
import base64

# Загружаем настройки из секретов GitHub
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
NVIDIA_API_KEY = os.environ["NVIDIA_API_KEY"]

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
2. "image_prompt": Краткое, детальное визуальное описание картинки для генерации на АНГЛИЙСКОМ языке (например: "cinematic shot of a futuristic neon city, highly detailed, 8k resolution, dramatic lighting").

НЕ добавляй никакой другой текст, маркдаун (типа ```json) или комментарии. Только валидный JSON."""

def generate_content():
    """Генерируем текст поста и промпт для картинки через NVIDIA Llama 3.1"""
    topic = random.choice(TOPICS)
    
    response = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "meta/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(topic=topic)}],
            "temperature": 0.8,
            "max_tokens": 500,
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
    """Генерируем картинку через NVIDIA Stable Diffusion XL"""
    response = requests.post(
        "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl",
        headers={
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={
            "prompt": image_prompt + ", masterpiece, best quality, highly detailed",
            "height": 1024,
            "width": 1024,
            "steps": 25,
            "seed": random.randint(1, 10000),
        },
        timeout=120,
    )
    response.raise_for_status()
    
    # NVIDIA возвращает картинку в base64
    data = response.json()
    image_base64 = data["artifacts"][0]["base64"]
    image_bytes = base64.b64decode(image_base64)
    
    return image_bytes

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
    
    response = requests.post(tg_url, files=files, data=data, timeout=30)
    response.raise_for_status()
    return response.json()

def main():
    print("🤖 Генерируем текст и промпт для картинки (NVIDIA Llama 3.1)...")
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

    print("🎨 Генерируем картинку (NVIDIA SDXL)...")
    try:
        image_bytes = generate_image(image_prompt)
    except Exception as e:
        print(f"❌ ОШИБКА генерации картинки: {e}")
        sys.exit(1)

    print("📤 Отправляем фото с текстом в Telegram...")
    try:
        result = send_to_telegram_with_photo(post_text, image_bytes)
        print(f"✅ Готово! Message ID: {result['result']['message_id']}")
    except Exception as e:
        print(f"❌ ОШИБКА отправки в Telegram: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
