import feedparser
import requests
from bs4 import BeautifulSoup
import time
import os # Добавили для проверки файла

from src.database import SessionLocal, Article, Entity
from src.ner_extractor import extract_entities_from_text



def get_seen_urls_from_db():
    """Достает все сохраненные URL напрямую из SQLite"""
    session = SessionLocal()
    try:
        # Делаем быстрый запрос: SELECT url FROM articles
        # .all() вернет список кортежей вида [('http...',), ('http...',)]
        urls = session.query(Article.url).all()
        
        # Распаковываем кортежи и собираем в быстрый set
        return set(url[0] for url in urls)
    except Exception as e:
        print(f"❌ Ошибка при чтении URL из базы: {e}")
        return set()
    finally:
        session.close()


def scrape_habr_ml_news(limit=3):
    rss_url = "https://habr.com/ru/rss/hub/machine_learning/all/"
    feed = feedparser.parse(rss_url)
    
    # 1. Загружаем память нашего Скаута
    seen_urls = get_seen_urls_from_db()
    print(f"🧠 В SQL-базе уже сохранено {len(seen_urls)} статей.")
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
                    
                    save_article_to_sql(title=title, url=link, text=clean_text)
                
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


def save_article_to_sql(title, url, text):
    session = SessionLocal()
    
    try:
        # 1. Сохраняем саму статью
        new_article = Article(title=title, url=url)
        session.add(new_article)
        
        # 2. Вытаскиваем сущности через LLM
        print("🧠 Извлекаю NER сущности...")
        extracted_entities = extract_entities_from_text(text)
        
        # 3. Сохраняем сущности и связываем их со статьей
        for ent in extracted_entities:
            # Ищем, есть ли уже такая сущность в базе (чтобы не плодить дубли "Python")
            db_entity = session.query(Entity).filter_by(name=ent.name).first()
            
            if not db_entity:
                db_entity = Entity(name=ent.name, label=ent.label)
                session.add(db_entity)
            
            # Связываем статью и сущность
            new_article.entities.append(db_entity)
            
        session.commit()
        print(f"✅ Статья '{title}' и {len(extracted_entities)} сущностей сохранены в SQL!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Ошибка SQL: {e}")
    finally:
        session.close()






if __name__ == "__main__":
    news = scrape_habr_ml_news(limit=5)