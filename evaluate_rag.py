import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings
import warnings

# Игнорируем предупреждения Ragas об устаревших импортах, 
# так как новые метрики из collections не работают со старым API evaluate
warnings.filterwarnings("ignore", category=DeprecationWarning)

def main():
    print("⏳ Инициализация локальных моделей...")
    
    # 1. Переопределяем LLM на локальную Ollama
    # Используем llama3 (или любую другую локальную модель) в качестве судьи
    evaluator_llm = ChatOllama(model="llama3", temperature=0)
    
    # Инициализируем Sentence Transformers для эмбеддингов
    evaluator_embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={'device': 'cpu'} # Для оценки можно использовать CPU, чтобы не грузить GPU, если он занят
    )
    
    # 2. Хардкодим тестовый датасет на русском языке (Тематика IT/Хабр)
    # Ragas ожидает ключи: question, answer, contexts
    data = {
        "question": [
            "Что такое RAG и зачем он нужен в LLM?",
            "Какие основные этапы пайплайна RAG?",
            "Что делает агент-критик в LangGraph?",
            "Заменит ли ИИ всех программистов в ближайшем году?"
        ],
        "answer": [
            "RAG (Retrieval-Augmented Generation) — это метод обогащения генеративных нейросетей внешними данными. Он нужен, чтобы LLM не галлюцинировала и опиралась на актуальную базу знаний.",
            "Основные этапы RAG: парсинг документов, чанкинг, создание эмбеддингов, сохранение в векторную БД, поиск (retrieval) релевантных кусков по запросу и генерация ответа.",
            "Агент-критик оценивает написанный пост на предмет галлюцинаций, проверяя, не выдуманы ли факты, имена или даты, которых нет в исходном контексте.",
            "Да, к концу года ИИ полностью заменит всех Junior и Middle разработчиков, останутся только архитекторы." # Специально неверный ответ (галлюцинация) для проверки метрик
        ],
        "contexts": [
            ["Генеративные модели склонны к галлюцинациям. Retrieval-Augmented Generation (RAG) решает эту проблему, подмешивая в промпт релевантные куски текста из корпоративной базы знаний, что делает ответы фактичными."],
            ["Построение RAG-пайплайна включает подготовку данных (чанкинг и векторизацию) и этап инференса: эмбеддинг запроса пользователя, поиск в ChromaDB и финальный вызов LLM с найденным контекстом."],
            ["В архитектуре мультиагентных систем на базе LangGraph часто выделяют роль Critic. Его задача — сопоставить черновик ответа (draft) с исходными фактами и вернуть фидбек или команду на переписывание."],
            ["ИИ значительно повышает продуктивность программистов, выступая в роли второго пилота (Copilot). В ближайшие годы не ожидается полной замены разработчиков, скорее изменится их стек инструментов."]
        ]
    }
    
    # 3. Оборачиваем в Dataset из библиотеки datasets
    dataset = Dataset.from_dict(data)
    
    print("🚀 Запуск Ragas Evaluation (может занять некоторое время на локальной модели)...")
    
    # 4. Запускаем оценку
    # Явно передаем наши локальные модели в функцию evaluate, чтобы избежать обращений к OpenAI API
    try:
        result = evaluate(
            dataset=dataset,
            metrics=[Faithfulness(), AnswerRelevancy()],
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        )
    except Exception as e:
        print(f"\n❌ Произошла ошибка во время оценки: {e}")
        print("💡 Совет: убедитесь, что Ollama запущена и модель llama3 установлена (ollama run llama3).")
        return
    
    # 5. Красивый вывод результатов
    print("\n✅ Оценка завершена! Итоговые метрики:\n")
    
    # Ragas возвращает средние скоры, которые можно получить прямо по ключам
    print(f"📈 Средний Faithfulness (отсутствие галлюцинаций): {result.get('faithfulness', 0):.4f}")
    print(f"📈 Средний Answer Relevancy (релевантность ответа): {result.get('answer_relevancy', 0):.4f}\n")
    
    print("📊 Детальный отчет по каждому вопросу:")
    
    # Конвертируем результат в pandas DataFrame
    df = result.to_pandas()
    
    # Настраиваем Pandas для красивого вывода в консоль
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', 1000)
    pd.set_option('display.max_colwidth', 50)
    
    # Выводим таблицу
    if 'answer_relevancy' in df.columns:
        print(df[['question', 'faithfulness', 'answer_relevancy']])
    else:
        print(df)


if __name__ == "__main__":
    main()
