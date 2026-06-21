from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
import torch
from src.parser import scrape_habr_ml_news

def update_knowledge_base():
    torch.cuda.empty_cache()
    print("🔄 Проверка новых статей на Хабре...")
    
    # 1. Запускаем парсер
    scraped_data = scrape_habr_ml_news(limit=2)
    
    # Если парсер вернул пустой список (всё пропущено), просто выходим из функции
    if not scraped_data:
        print("🤷‍♂️ Новых статей нет. База актуальна.")
        return

    # 2. Если есть новые данные, превращаем их в документы
    docs = []
    for item in scraped_data:
        doc = Document(
            page_content=item['text'],
            metadata={"title": item['title'], "url": item['url']}
        )
        docs.append(doc)

    # 3. Чанкинг
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = text_splitter.split_documents(docs)
    print(f"✅ Новые статьи разбиты на {len(chunks)} кусков.")

    # 4. Подключаем модель и сохраняем в базу
    print("⏳ Сохраняем новые данные в ChromaDB...")
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        model_kwargs={'device': 'cuda'}
    )
    
    vector_store = Chroma(
        collection_name="osint_news",
        embedding_function=embeddings,
        persist_directory="./chroma_db" 
    )
    
    vector_store.add_documents(documents=chunks)
    print("✅ База знаний успешно обновлена!")