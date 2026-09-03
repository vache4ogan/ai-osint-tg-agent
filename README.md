# 🤖 OSINT Telegram-бот с агентами (LangGraph + CRAG + Ragas)

![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![LangGraph](https://img.shields.io/badge/LangGraph-Agentic_AI-orange)
![LLM](https://img.shields.io/badge/Local_LLM-Ollama-lightgrey)
![Ragas](https://img.shields.io/badge/Evaluation-Ragas-success)
![RAG](https://img.shields.io/badge/Architecture-CRAG-yellow)

**Продвинутая мультиагентная система** для мониторинга IT-индустрии, агрегации технологического контента и автоматической генерации качественных, проверенных публикаций для Telegram-каналов.

Проект демонстрирует глубокое понимание современных концепций **LLMOps**, построения агентов на базе **LangGraph** и обеспечения Production-ready стандартов, таких как:
* Оценка RAG-пайплайна через **Ragas** (прямо в UI бота!).
* Борьба с галлюцинациями через паттерн **Corrective RAG (CRAG)** и агента-критика.
* Использование **Semantic Chunking** для сохранения глубокого контекста при векторизации.
* Отказоустойчивость: строгая валидация ответов LLM (Pydantic) и **Self-Correction (Retry-петли)**.

---

## 📐 Архитектура системы и воркфлоу агентов

Пайплайн построен вокруг ролевых ИИ-агентов, взаимодействующих в рамках графа (LangGraph):

1. 🕷 **Scout (Парсер):** Мониторит RSS-ленты и парсит сырой HTML с технологических платформ (например, Хабр).
2. 🧠 **Semantic Chunker:** Векторизация происходит не тупым делением по символам, а через `SemanticChunker`. Текст дробится на основе косинусного расстояния между предложениями, сохраняя цельные смысловые блоки и прикрепляя богатые метаданные (URL, дата, теги).
3. 🔎 **Retriever Node (CRAG):** Выполняет семантический поиск по `ChromaDB` (используя `paraphrase-multilingual-MiniLM-L12-v2`). Если извлеченного контекста недостаточно для полного ответа, динамически активируется **Web Search** (через DuckDuckGo) для добора актуальных фактов из интернета.
4. ✍️ **Writer Node:** Генерирует черновик поста, опираясь *строго* на собранные факты, соблюдая формат и Tone of Voice канала.
5. 🛡 **Critic Node (Валидация через Pydantic + Retry):** Выступает в роли безжалостного редактора.
   - Проверяет текст на галлюцинации и логические ошибки.
   - Использует `with_structured_output` для строгого JSON-формата.
   - **Self-Correction:** Если локальная модель (Llama3/Qwen) ошибается в структуре JSON, граф перехватывает `ValidationError` и зацикливается, передавая ошибку модели с требованием исправиться (до 3 итераций).
6. 📊 **Evaluator Node (Ragas):** Интегрирован процесс оценки качества прямо на лету! Каждый сгенерированный черновик оценивается метриками **Faithfulness** (отсутствие галлюцинаций) и **Answer Relevancy** с выводом результатов модератору.
7. 👤 **Human-in-the-Loop:** Финальный результат с оценками Ragas отправляется в Telegram-панель администратора на модерацию (Опубликовать / Перегенерировать / Отклонить).

---

## 🛠️ Технологический стек

* **Оркестрация агентов:** LangGraph, LangChain
* **LLM Backend:** Ollama (локальные модели, default: `llama3`)
* **Оценка качества (Evaluation):** Ragas, HuggingFace Datasets, Pandas
* **Векторная база и эмбеддинги:** ChromaDB, HuggingFace Embeddings (`paraphrase-multilingual-MiniLM-L12-v2`)
* **Данные и парсинг:** SQLite (кэш), BeautifulSoup4, Feedparser
* **Бот-интерфейс и асинхронность:** Aiogram 3.x

---

## 📂 Структура проекта

```text
TG_agent/
├── agents/                       # Модули мультиагентной системы
│   ├── state.py                  # AgentState, CriticVerdict и схемы Pydantic
│   ├── researcher.py             # Агент-Исследователь: векторный поиск + веб-поиск (CRAG)
│   ├── writer.py                 # Агент-Писатель: генерация постов
│   ├── critic.py                 # Агент-Критик: фактчекинг и Retry-петли
│   └── graph.py                  # Сборка графа маршрутизации LangGraph
│
├── src/                          # Сервисы ядра
│   ├── parser.py                 # Парсинг и очистка HTML
│   ├── chanking.py               # Продвинутый Semantic Chunking
│   ├── evaluator.py              # 🆕 Интеграция Ragas для оценки Faithfulness & Relevancy
│   ├── llm_core.py               # Инициализация LLM и векторного хранилища
│   └── tg_bot.py                 # Telegram HITL-интерфейс
│
├── evaluate_rag.py               # 🆕 Отдельный скрипт для batch-оценки RAG на тестовом датасете
├── test_pipeline.py              # Скрипт полного тестирования пайплайна агентов локально
├── requirements.txt              # Полный список зависимостей
└── README.md                     # Документация проекта
```

---

## 🚀 Быстрый запуск

### 1. Подготовка окружения
Клонируйте репозиторий и создайте виртуальное окружение:
```bash
git clone https://github.com/vache4ogan/ai-osint-tg-agent.git
cd ai-osint-tg-agent

python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Запуск локальной LLM
Убедитесь, что `ollama` установлена и модель скачана:
```bash
ollama pull llama3:latest
```
*(LLM и эмбеддинги исполняются полностью локально, без зависимости от платных API).*

### 3. Настройка Telegram Бота
Создайте файл `src/config.py` в корне проекта со следующим содержимым:
```python
# src/config.py
token = "ВАШ_ТОКЕН_ТЕЛЕГРАМ_БОТА"
```

### 4. Запуск проекта
Запустите бота (интерфейс Human-in-the-Loop):
```bash
python -m src.tg_bot
```
Бот пришлет вам готовый пост вместе с расчетом метрик **Faithfulness** и **Relevancy** от Ragas прямо в сообщение!

### 5. Оффлайн тестирование и оценка
Хотите прогнать Ragas-оценку на хардкоженом датасете для тестов?
```bash
python evaluate_rag.py
```
Хотите протестировать работу всего графа LangGraph локально в терминале без Telegram?
```bash
python test_pipeline.py
```

---

## 🎯 План развития (Roadmap)

- [x] Интеграция фреймворка **Ragas** для автоматической оценки качества ретривала и точности генерации (Faithfulness, Relevancy).
- [x] Внедрение **Semantic Chunking** для осмысленного разделения документов.
- [x] Реализация **Retry-механизмов** для стабильной работы LLM со строгими JSON-схемами.
- [x] Интеграция оценок Ragas напрямую в Telegram HITL интерфейс.
- [ ] Разработка Agent-Illustrator с использованием SD/DALL-E для генерации обложек к постам.
- [ ] Контейнеризация экосистемы (docker-compose) для бесшовного деплоя.