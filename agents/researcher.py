from langchain_community.tools import DuckDuckGoSearchRun

from src.llm_core import vector_store
from agents.state import AgentState

web_search = DuckDuckGoSearchRun()


def retrieve_info(state: AgentState):
    """Ищет данные в ChromaDB"""

    print(f"🔍 [Retriever]: Достаю факты из ChromaDB...")
        
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    docs = retriever.invoke(state["topic"])
    context = "\n\n".join(doc.page_content for doc in docs)
        
    print(f"   [Retriever]: Найдено {len(context)} символов контекста.")

    return {"context": context, "iterations": 0}

def web_searcher(state: AgentState):

    print("🌐 [Web Searcher]: Локальная база подвела. Ищу информацию в интернете...")

    topic = state['topic']

    try:
        search_res = web_search.invoke(topic)
        print(f"   [Web Searcher]: Найдено {len(search_res)} символов в сети.")

        return {'context': search_res}
    except Exception as e:
        print(f"   [Web Searcher]: ❌ Ошибка поиска: {e}")
        return {"context": "КРИТИЧЕСКАЯ ОШИБКА: Не удалось получить данные даже из интернета."}


def check_context(state: AgentState):
    """"Роутер: решает, хватит ли локальных данных или нужен интернет"""

    context = state["context"]

    if not context or len(context.strip()) < 100:
        print("   [Routing]: ⚠️ Локального контекста недостаточно. Нужен интернет!")
        return "search_internet"
    else:
        print("   [Routing]: ⚠️ Локальный контекст достаточек. Передаю писателю")
        return "write"
