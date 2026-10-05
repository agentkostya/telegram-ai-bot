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
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "")

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

# Промпт для генерации контента на основе новостей
PROMPT_TEMPLATE = """Ты - профессиональный журналист для ведения Telegram-канала о бизнесе и экономике РФ.
Тема: {topic}

Актуальная новость для анализа:
{news_content}

ВАЖНО: Используй ТОЛЬКО информацию из предоставленной новости и официальные источники (РБК, TACC, Коммерсант, FinExpertiza, Skolkovo, МЭР России, ЦБ РФ, Московская биржа и т.д.).

Сгенерируй ответ СТРОГО в формате JSON с четырьмя полями:
1. "post_text": ПОДРОБНЫЙ пост на русском языке (12-15 предложений, с 3-4 эмодзи, без хештегов). Должен содержать:
   - Краткое описание новости (2-3 предложения)
   - Причины и предпосылки события (2-3 предложения)
   - Влияние на рынок/экономику (2-3 предложения)
   - Мнения экспертов если есть (2-3 предложения)
   - Возможные последствия (2-3 предложения)
   Включи конкретные цифры, суммы в миллиардах, проценты роста/падения, имена компаний и экспертов.

2. "key_facts": Массив из 5-6 ключевых фактов в виде статистики и цифр по новости.
   Примеры: "Рост на 15.3%", "Инвестиции в размере $2.5 млрд", "Создано 5000 рабочих мест"

3. "source_info": Официальный источник новости (с указанием даты публикации если известна).
   Используй только авторитетные источники: РБК, TACC, Коммерсант, FinExpertiza, МЭР России, ЦБ РФ, Московская биржа

4. "image_prompt": Профессиональное визуальное описание картинки на АНГЛИЙСКОМ языке (12-15 слов). 
   Должно отражать бизнес/экономику/финансы. ОБЯЗАТЕЛЬНО в конец: ", no watermark, no text, no signature, masterpiece, 8k"
   Примеры: "professional business meeting in modern office, stock market graphs, growth charts, financial data, 8k resolution, detailed"

НЕ добавляй никакой другой текст, маркдаун или комментарии. Только валидный JSON."""

def get_russian_business_news():
    """Получаем актуальные новости о бизнесе РФ из достоверных источников"""
    
    if not NEWS_API_KEY:
        print("⚠️  NEWS_API_KEY не установлен, используем шаблонную новость")
        return "Российский рынок показывает положительную динамику развития. Крупные компании инвестируют в новые проекты и расширяют деятельность."
    
    try:
        # Используем News API для получения российских новостей
        news_url = "https://newsapi.org/v2/everything"
        params = {
            "q": "Russia business economy",
            "language": "ru",
            "sortBy": "publishedAt",
            "apiKey": NEWS_API_KEY,
            "pageSize": 5
        }
        
        print("📰 Получаем свежие новости о бизнесе в РФ...")
        response = requests.get(news_url, params=params, timeout=10)
        response.raise_for_status()
        
        articles = response.json().get("articles", [])
        if articles:
            # Берем самую свежую новость
            latest_news = articles[0]
            news_text = f"Источник: {latest_news.get('source', {}).get('name', 'Неизвестно')}\n"
            news_text += f"Дата: {latest_news.get('publishedAt', '')}\n"
            news_text += f"Заголовок: {latest_news.get('title', '')}\n"
            news_text += f"Описание: {latest_news.get('description', '')}"
            
            print(f"✅ Новость найдена: {latest_news.get('title', 'Без названия')[:60]}...")
            return news_text
        else:
            print("⚠️  Новостей не найдено, используем шаблонную новость")
            return "Российский рынок показывает положительную динамику развития. Крупные компании инвестируют в новые проекты и расширяют деятельность."
            
    except Exception as e:
        print(f"⚠️  Ошибка получения новостей: {e}")
        return "Российский рынок показывает положительную динамику развития. Крупные компании инвестируют в новые проекты и расширяют деятельность."

def generate_content():
    """Генерируем текст через OpenRouter на основе реальных новостей"""
    topic = random.choice(TOPICS)
    news_content = get_russian_business_news()
    
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
            "messages": [{"role": "user", "content": PROMPT_TEMPLATE.format(topic=topic, news_content=news_content)}],
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
