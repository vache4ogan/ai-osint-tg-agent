import feedparser
import requests
from bs4 import BeautifulSoup
import time
import os # Добавили для проверки файла

# Указываем имя файла, где будем хранить память о ссылках
CACHE_FILE = "seen_urls.txt"

def get_seen_urls():
    """Читает архив ссылок с диска и возвращает их в виде множества (set)"""
    if not os.path.exists(CACHE_FILE):
        return set()
    with open(CACHE_FILE, "r", encoding="utf-8") as f:
        # Читаем файл, убираем переносы строк и кладем в set (для быстрого поиска)
        return set(f.read().splitlines())

def save_url_to_cache(url):
    """Дописывает новую ссылку в конец архива"""
    with open(CACHE_FILE, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def scrape_habr_ml_news(limit=3):
    rss_url = "https://habr.com/ru/rss/hub/machine_learning/all/"
    feed = feedparser.parse(rss_url)
    
    # 1. Загружаем память нашего Скаута
    seen_urls = get_seen_urls()
    print(f"🧠 В памяти агента уже сохранено {len(seen_urls)} статей.")
    print(f"📡 В RSS найдено свежих статей: {len(feed.entries)}")
    
    scraped_data = []
    
    for entry in feed.entries[:limit]:
        title = entry.title
        link = entry.link
        
        # 2. ЖЕСТКАЯ ПРОВЕРКА НА ДУБЛИКАТЫ
        if link in seen_urls:
            print(f"⏭️ Пропускаю (уже читали): {title}")
            continue # Переходим к следующей статье, не скачивая HTML
            
        print(f"\n🔍 Читаю новую статью: {title}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(link, headers=headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                content_div = soup.find('div', class_=lambda c: c and 'article-body' in c)
                
                if content_div:
                    clean_text = content_div.get_text(separator=' ', strip=True)
                    scraped_data.append({
                        'title': title,
                        'url': link,
                        'text': clean_text
                    })
                    print(f"✅ Успешно скачано: {len(clean_text)} символов.")
                    
                    # 3. ЗАПОМИНАЕМ ССЫЛКУ ПОСЛЕ УСПЕШНОГО СКАЧИВАНИЯ
                    save_url_to_cache(link)
                    # Обновляем сет в памяти, чтобы не было дублей внутри одного запуска
                    seen_urls.add(link) 
                else:
                    print("⚠️ Не удалось найти тело статьи.")
            else:
                print(f"❌ Ошибка доступа: {response.status_code}")
                
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Ошибка при парсинге: {e}")
            
    return scraped_data


if __name__ == "__main__":
    news = scrape_habr_ml_news(limit=5)