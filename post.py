import os
import requests
import random
import json
import sys
import urllib.parse

# Загружаем настройки из секретов GitHub
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

# Темы для новостей о бизнесе и экономике РФ
TOPICS = [
    "Новости о бизнесе в России",
    "Экономические новости РФ",
    "Развитие стартапов в России",
    "Российский рынок акций и финансы",
    "Инновации в российской экономике",
    "Трудовой рынок и занятость в России",
    "Международная торговля России"
]

# Промпт для генерации контента о бизнесе и экономике РФ
PROMPT_TEMPLATE = """Ты - профессиональный журналист для ведения Telegram-канала о бизнесе и экономике РФ.
Тема: {topic}

Используй свои знания о российском бизнесе, экономике и финансовых рынках.
Ссылайся только на достоверные официальные источники (РБК, TACC, Коммерсант, FinExpertiza, МЭР России, ЦБ РФ, Московская биржа и т.д.).

Сгенерируй ответ СТРОГО в формате JSON с четырьмя полями:
1. "post_text": ПОДРОБНЫЙ пост на русском языке (12-15 предложений, с 3-4 эмодзи, без хештегов). Должен содержать:
   - Описание актуальной ситуации в теме (2-3 предложения)
   - Ключевые факты и тренды (2-3 предложения)
   - Влияние на российский рынок и экономику (2-3 предложения)
   - Мнения аналитиков и экспертов (2-3 предложения)
   - Будущие перспективы развития (2-3 предложения)
   Включи конкретные цифры, суммы, проценты, имена компаний и экспертов.

2. "key_facts": Массив из 5-6 ключевых статистических фактов по теме.
   Примеры: "Рост на 15.3% за квартал", "Инвестиции превысили $2.5 млрд", "Создано более 5000 рабочих мест"

3. "source_info": Официальные авторитетные источники информации.
   Используй: РБК, TACC, Коммерсант, FinExpertiza, МЭР России, ЦБ РФ, Московская биржа

4. "image_prompt": Профессиональное визуальное описание картинки на АНГЛИЙСКОМ языке (12-15 слов). 
   Должно отражать бизнес/экономику/финансы. ОБЯЗАТЕЛЬНО в конец: ", no watermark, no text, no signature, masterpiece, 8k"
   Примеры: "professional business meeting with stock market graphs, growth charts, financial data on screens, modern office, 8k"

НЕ добавляй никакой другой текст, маркдаун или комментарии. Только валидный JSON."""

def generate_content():
    """Генерируем текст через OpenRouter по заданной теме"""
    topic = random.choice(TOPICS)
    
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer ******",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/agentkostya/telegram-ai-bot",
            "X-Title": "Telegram AI Bot",
        },
        json={
            "model": "openrouter/free",
            "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(topic=topic)}],
            "temperature": 0.7,
            "response_format": { "type": "json_object" }
        },
        timeout=60,
    )
    response.raise_for_status()
    result_text = response.json()["choices"][0]["message"]["content"]

    # Очищаем ответ от маркдауна
    result_text = result_text.strip()
    if result_text.startswith("```json"): result_text = result_text[7:]
    if result_text.startswith("```"): result_text = result_text[3:]
    if result_text.endswith("```"): result_text = result_text[:-3]
    result_text = result_text.strip()

    return json.loads(result_text)

def generate_image(image_prompt):
    """Скачиваем картинку напрямую с Pollinations как файл (без водяных знаков)"""
    encoded_prompt = urllib.parse.quote(image_prompt)
    random_seed = random.randint(1, 99999)
    
    # Используем модель flux и nologo=true
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={random_seed}&model=flux"
    
    print(f"🎨 Скачиваем картинку с Pollinations (seed: {random_seed})...")
    
    # Скачиваем картинку как байты, а не просто ссылку
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    response = requests.get(image_url, headers=headers, timeout=60)
    response.raise_for_status()
    
    print("✅ Картинка успешно скачана в память!")
    return response.content

def send_to_telegram_with_photo(post_text, image_bytes):
    """Отправляем фото (как файл) с текстом в Telegram"""
    tg_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    
    files = {
        'photo': ('image.jpg', image_bytes, 'image/jpeg')
    }
    data = {
        'chat_id': CHANNEL_ID,
        'caption': post_text,
        'parse_mode': "HTML"
    }
    
    print("📤 Отправляем фото с текстом в Telegram...")
    tg_response = requests.post(tg_url, files=files, data=data, timeout=30)
    tg_response.raise_for_status()
    return tg_response.json()

def main():
    print("🤖 Генерируем текст и промпт для картинки на основе новостей РФ...")
    try:
        content = generate_content()
        post_text = content.get("post_text")
        image_prompt = content.get("image_prompt")
        key_facts = content.get("key_facts", [])
        source_info = content.get("source_info", "")

        if not post_text or not image_prompt:
            raise ValueError("ИИ не вернул поля post_text или image_prompt")

    except Exception as e:
        print(f"❌ ОШИБКА генерации текста: {e}")
        sys.exit(1)

    print(f"\n📝 Текст поста:\n{post_text}")
    if source_info:
        print(f"\n📚 Источник: {source_info}")
    if key_facts:
        print(f"\n📌 Ключевые факты:")
        for i, fact in enumerate(key_facts, 1):
            print(f"   {i}. {fact}")
    print(f"\n🎨 Промпт для картинки: {image_prompt}")

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
