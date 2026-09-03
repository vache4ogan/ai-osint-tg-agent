from langchain_experimental.text_splitter import SemanticChunker
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
import torch
from src.parser import scrape_habr_ml_news
from datetime import datetime

def update_knowledge_base():
    torch.cuda.empty_cache()
    print("🔄 Проверка новых статей на Хабре...")
    
    # 1. Запускаем парсер
    scraped_data = scrape_habr_ml_news(limit=2)
    
    # Если парсер вернул пустой список (всё пропущено), просто выходим из функции
    if not scraped_data:
        print("🤷‍♂️ Новых статей нет. База актуальна.")
        return

    # Инициализируем эмбеддинги раньше, так как они нужны для Semantic Chunking
    print("⏳ Инициализация модели эмбеддингов...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={'device': 'cuda'}
    )

    # 2. Если есть новые данные, превращаем их в документы
    docs = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    for item in scraped_data:
        # Добавляем расширенные метаданные
        metadata = {
            "title": item['title'], 
            "url": item['url'],
            "date_parsed": current_date,
            "source": "habr"
        }
        # Если в будущем парсер будет собирать теги:
        if 'tags' in item:
            metadata['tags'] = item['tags']
            
        doc = Document(
            page_content=item['text'],
            metadata=metadata
        )
        docs.append(doc)

    # 3. Продвинутый Чанкинг (Semantic Chunking)
    # Используем эмбеддинги для разбиения текста на куски с учетом смысла и контекста
    print("🧠 Выполняем Semantic Chunking (разбиение по смыслу)...")
    text_splitter = SemanticChunker(
        embeddings, 
        breakpoint_threshold_type="percentile" # Объединяет предложения, пока разница в их смысле (косинусное расстояние) не превысит порог
    )
    chunks = text_splitter.split_documents(docs)
    print(f"✅ Новые статьи разбиты на {len(chunks)} смысловых кусков.")

    # 4. Сохраняем в базу
    print("⏳ Сохраняем новые данные в ChromaDB...")
    
    vector_store = Chroma(
        collection_name="osint_news",
        embedding_function=embeddings,
        persist_directory="./chroma_db" 
    )
    
    vector_store.add_documents(documents=chunks)
    print("✅ База знаний успешно обновлена!")