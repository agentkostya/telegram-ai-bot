import os
import requests
import random
import json
import sys
import urllib.parse
from duckduckgo_search import DDGS

# Загружаем настройки из секретов GitHub
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

# Реальные темы для поиска новостей
SEARCH_QUERIES = [
    "Новости бизнеса Россия последние",
    "Экономические новости РФ официальные",
    "Крупные компании Россия новые проекты",
    "Стартапы и технологии бизнес Россия"
]

def get_real_news():
    """Ищет реальные свежие новости в интернете"""
    query = random.choice(SEARCH_QUERIES)
    print(f"🔍 Ищем реальные новости по запросу: '{query}'")
    
    try:
        with DDGS() as ddgs:
            # Получаем топ-3 реальных результата с ссылками
            results = list(ddgs.text(query, max_results=3, region='ru-ru'))
        
        if not results:
            raise Exception("Поиск не вернул результатов")
        
        # Формируем контекст для ИИ из реальных источников
        news_context = "\n".join([
            f"- {r['title']}\n  Кратко: {r['body']}\n  Источник: {r['href']}" 
            for r in results
        ])
        return news_context
    except Exception as e:
        raise Exception(f"Ошибка поиска новостей: {e}")

def generate_content(news_context):
    """Генерирует пост на основе реальных новостей"""
    prompt = f"""Ты - профессиональный финансовый журналист и ведущий Telegram-канала о бизнесе.
Вот реальные свежие новости, которые я нашел в официальных источниках:
{news_context}

Твоя задача: Напиши качественный пост для Telegram-канала на основе этих реальных фактов.

Требования к тексту:
1. Объем: РОВНО 2 абзаца. 
   - Первый абзац: Суть новости, конкретные факты, цифры или имена.
   - Второй абзац: Краткий анализ, почему это важно для рынка или что это значит для читателей.
2. Стиль: Деловой, экспертный, но живой и понятный. Без воды и клише.
3. В конце добавь 1-2 подходящих эмодзи.
4. НЕ используй хештеги.
5. НЕ придумывай факты, используй только предоставленный контекст.

Требования к картинке:
Сгенерируй поле "image_prompt" на АНГЛИЙСКОМ языке. Опиши визуальный образ этой новости (например: "modern Moscow city business district, financial charts, cinematic lighting, highly detailed, no text, no watermark").

Ответь СТРОГО в формате JSON с двумя полями: "post_text" и "image_prompt". Никакого лишнего текста, маркдауна или комментариев."""

    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/agentkostya/telegram-ai-bot",
            "X-Title": "Telegram AI Bot",
        },
        json={
            "model": "openrouter/free",
            "messages": [{"role": "user", "content": prompt}],
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
    """Скачиваем картинку напрямую с Pollinations как файл"""
    encoded_prompt = urllib.parse.quote(image_prompt)
    random_seed = random.randint(1, 99999)
    
    image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true&seed={random_seed}&model=flux"
    
    print("🎨 Скачиваем картинку с Pollinations...")
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
    print("🔍 Этап 1: Поиск реальных новостей...")
    try:
        news_context = get_real_news()
        print("✅ Новости найдены!")
    except Exception as e:
        print(f"❌ ОШИБКА поиска: {e}")
        sys.exit(1)

    print("🤖 Этап 2: Генерация поста и промпта для картинки...")
    try:
        content = generate_content(news_context)
        post_text = content.get("post_text")
        image_prompt = content.get("image_prompt")

        if not post_text or not image_prompt:
            raise ValueError("ИИ не вернул поля post_text или image_prompt")

    except Exception as e:
        print(f"❌ ОШИБКА генерации текста: {e}")
        sys.exit(1)

    print(f"📝 Текст поста:\n{post_text}\n")
    print(f"🎨 Промпт для картинки: {image_prompt}")

    print("🎨 Этап 3: Генерация картинки...")
    try:
        image_bytes = generate_image(image_prompt)
    except Exception as e:
        print(f"❌ ОШИБКА генерации картинки: {e}")
        sys.exit(1)

    print("📤 Этап 4: Отправка в Telegram...")
    try:
        result = send_to_telegram_with_photo(post_text, image_bytes)
        print(f"✅ Готово! Message ID: {result['result']['message_id']}")
    except Exception as e:
        print(f"❌ ОШИБКА отправки в Telegram: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
