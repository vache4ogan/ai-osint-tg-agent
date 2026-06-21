# agents/analyst.py
import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.llm_core import llm
from src.database import engine # Берем наш движок базы данных
from agents.state import AgentState

def sql_analyst_node(state: AgentState):
    """Агент, который переводит вопрос в SQL, выполняет его и собирает данные"""
    
    print("📊 [SQL Analyst]: Перевожу запрос в SQL и анализирую базу...")
    
    user_query = state["topic"] # В поле topic у нас лежит сам вопрос пользователя

    # Жестко описываем схему базы для LLM, чтобы она знала имена таблиц и колонок
    system_prompt = """Ты — эксперт по SQL и анализу данных. Твоя задача — перевести текстовый запрос пользователя в ОДИН корректный SQL-запрос для SQLite.

    Вот схема нашей базы данных:
    
    Таблица: articles
    - id (INTEGER, primary key)
    - title (VARCHAR) - название статьи
    - url (VARCHAR) - ссылка на статью

    Таблица: entities
    - id (INTEGER, primary key)
    - name (VARCHAR) - название сущности (например: OpenAI, Python, PyTorch, Илья Суцкевер)
    - label (VARCHAR) - тип сущности (Strict одно из: ORG, TECH, PERSON)

    Таблица: article_entities (Связующая таблица многие-ко-многим)
    - id (INTEGER, primary key)
    - article_id (INTEGER, внешняя ссылка на articles.id)
    - entity_id (INTEGER, внешняя ссылка на entities.id)

    ПРАВИЛА:
    1. Возвращай ТОЛЬКО чистый SQL-запрос. Никаких пояснений, никакого форматирования markdown (НЕ используй ```sql).
    2. Используй только те таблицы и колонки, которые описаны выше.
    3. Будь аккуратен с регистрами. Если ищешь конкретную технологию, используй LIKE %запрос% для гибкости.
    4. Ограничивай выдачу (LIMIT 10), если запрос предполагает большой список.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Переведи этот запрос в SQL: {query}")
    ])

    # Цепочка для генерации текста запроса
    chain = prompt | llm | StrOutputParser()
    raw_sql = chain.invoke({"query": user_query})
    
    # Очищаем запрос от возможных артефактов (на случай если модель все-таки засунула его в ```sql)
    clean_sql = raw_sql.replace("```sql", "").replace("```", "").strip()
    
    print(f"   [SQL Analyst]: Сгенерирован SQL-запрос:\n   👉 {clean_sql}")
    
    # Выполняем запрос в базе данных
    try:
        with engine.connect() as connection:
            import sqlalchemy as sa
            result = connection.execute(sa.text(clean_sql))
            # Собираем строки в понятный для человека текст
            rows = result.fetchall()
            
            if not rows:
                db_context = "В базе данных ничего не найдено по этому запросу."
            else:
                # Превращаем результаты в читаемую строку
                db_context = "Результаты анализа базы данных:\n"
                for row in rows:
                    db_context += f"- {', '.join(str(item) for item in row)}\n"
                    
            print(f"   [SQL Analyst]: Успешно получено {len(rows)} строк из БД.")
            
    except Exception as e:
        print(f"   [SQL Analyst]: ❌ Ошибка выполнения SQL: {e}")
        db_context = f"Ошибка при анализе базы данных. Не удалось выполнить SQL-запрос."

    # Кладем собранные цифры/данные в контекст, чтобы Писатель (Writer) сделал из них красивый пост
    return {"context": db_context}