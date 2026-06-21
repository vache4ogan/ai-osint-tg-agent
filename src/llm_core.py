from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_ollama import ChatOllama

# 1. Инициализируем модель эмбеддингов
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cuda'},
    encode_kwargs={'batch_size': 4}
)

# 2. Просто подключаемся к существующей папке (без добавления новых текстов)
vector_store = Chroma(
    collection_name="osint_news",
    embedding_function=embeddings,
    persist_directory="./chroma_db"
)

# 3. Подключаем саму LLM
llm = ChatOllama(model="llama3:latest", temperature=0.1)