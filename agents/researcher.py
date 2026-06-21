from langchain_community.tools import DuckDuckGoSearchRun

from src.llm_core import vector_store, llm
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


def route_by_intent(state: AgentState):
    """Решает, куда направить запрос: на обычный RAG или на SQL-аналитику"""
    
    user_query = state["topic"]
    
    # Быстрый промпт к LLM для классификации интента
    prompt = f"""Проанализируй запрос пользователя и определи его цель.
    Если пользователь просит статистику, аналитику, тренды, подсчет чего-либо в базе или топ технологий/компаний — верни строго одно слово: ANALYTICS.
    Если пользователь просит написать пост на конкретную тему или пересказать статью — верни строго одно слово: RAG.
    
    Запрос: {user_query}
    Вердикт:"""
    
    # Вызываем напрямую через строковый парсер
    from langchain_core.output_parsers import StrOutputParser
    verdict = (llm | StrOutputParser()).invoke(prompt).strip().upper()
    
    if "ANALYTICS" in verdict:
        print("   [Router]: 📈 Обнаружен аналитический запрос. Направляю к SQL-Аналитику.")
        return "go_to_sql"
    else:
        print("   [Router]: 📝 Обнаружен контентный запрос. Направляю к стандартному RAG.")
        return "go_to_rag"