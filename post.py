import os
import requests
import random
import json
import sys
import urllib.parse
import feedparser

# Загружаем настройки из секретов GitHub
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]

# Надежные RSS-ленты (VC.ru - лучший для бизнеса/IT, ТАСС и Лента как запасные)
RSS_FEEDS = [
    "https://vc.ru/rss",                         # VC.ru: Бизнес, стартапы, технологии (очень надежный)
    "https://tass.ru/rss/v2.xml?categories=7",   # ТАСС: Экономика
    "https://lenta.ru/rss/news/economy"          # Лента.ру: Экономика
]

# Заголовки, чтобы притвориться обычным браузером и обойти блокировки
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*"
}

def get_real_news():
    """Получает реальные свежие новости из официальных RSS-лент с обходом блокировок"""
    
    for feed_url in RSS_FEEDS:
        print(f"📡 Пытаемся загрузить ленту: {feed_url}")
        try:
            # Делаем запрос как обычный браузер
            response = requests.get(feed_url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            
            # Парсим полученный XML-контент
            feed = feedparser.parse(response.content)
            
            if feed.entries:
                print(f"✅ Успешно загружено {len(feed.entries)} новостей!")
                
                # Берем 2-3 случайные свежие новости из топ-10
                recent_news = feed.entries[:10]
                selected_news = random.sample(recent_news, min(3, len(recent_news)))
                
                # Формируем контекст для ИИ
                news_context = "\n".join([
                    f"- Заголовок: {entry.title}\n  Кратко: {entry.get('summary', entry.get('description', 'Нет описания'))[:300]}...\n  Источник: {entry.link}"
                    for entry in selected_news
                ])
                return news_context
                
        except Exception as e:
            print(f"⚠️ Не удалось загрузить эту ленту, пробуем следующую: {e}")
            continue
            
    raise Exception("Не удалось загрузить новости ни из одного источника")

def generate_content(news_context):
    """Генерирует пост на основе реальных новостей"""
    prompt = f"""Ты - профессиональный финансовый журналист и ведущий Telegram-канала о бизнесе и экономике РФ.
Вот реальные свежие новости из проверенных источников:
{news_context}

Твоя задача: Напиши качественный, экспертный пост для Telegram-канала на основе этих реальных фактов.

СТРОГИЕ требования к тексту:
1. Объем: РОВНО 2 абзаца (разделенных одним пустым переносом строки \\n\\n).
   - Первый абзац: Суть новости, конкретные факты, цифры, названия компаний.
   - Второй абзац: Краткий экспертный анализ: почему это важно для рынка, бизнеса или обычных людей.
2. Стиль: Деловой, уверенный, живой. Без воды, клише и восклицательных знаков.
3. В конце добавь 1-2 подходящих эмодзи.
4. НЕ используй хештеги.
5. НЕ придумывай факты, опирайся только на предоставленный контекст.

Требования к картинке:
Сгенерируй поле "image_prompt" на АНГЛИЙСКОМ языке. Опиши строгий, кинематографичный визуальный образ этой новости (например: "modern Moscow city business district, financial data holograms, cinematic lighting, highly detailed, photorealistic, no text, no watermark").

Ответь СТРОГО в формате JSON с двумя полями: "post_text" и "image_prompt". Никакого лишнего текста, маркдауна (```json) или комментариев."""

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
    response = requests.get(image_url, headers=HEADERS, timeout=60)
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
    print("📡 Этап 1: Получение реальных новостей...")
    try:
        news_context = get_real_news()
        print("✅ Новости успешно получены!")
    except Exception as e:
        print(f"❌ ОШИБКА получения новостей: {e}")
        sys.exit(1)

    print("🤖 Этап 2: Генерация экспертного поста и промпта для картинки...")
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
