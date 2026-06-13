from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_community.tools import DuckDuckGoSearchRun
web_search = DuckDuckGoSearchRun()


from pydantic import BaseModel, Field

# Импортируем базу и LLM (убедись, что llm_core.py у тебя чистый, как мы делали в прошлом шаге)
from src.chanking import update_knowledge_base
from src.llm_core import llm, vector_store 



# СХЕМА ОТВЕТА КРИТИКА

class CriticVerdict(BaseModel):
    is_approved: bool = Field(description="True, если в тексте нет галлюцинаций и он полностью соответствует фактам. False, если есть ошибки.")
    feedback: str = Field(description="Если is_approved=False, подробно распиши замечания и что нужно исправить. Если True, оставь поле пустым.")



# ==========================================
# 1. СОСТОЯНИЕ (STATE)
# ==========================================
class AgentState(TypedDict):
    topic: str
    context: str
    draft: str
    critique: CriticVerdict      # Замечания от Критика
    iterations: int      # Счетчик, чтобы не уйти в бесконечный цикл

# ==========================================
# 2. УЗЛЫ (NODES)
# ==========================================
def retrieve_info(state: AgentState):
    print(f"🔍 [Retriever]: Достаю факты из ChromaDB...")
    
    retriever = vector_store.as_retriever(search_kwargs={"k": 3})
    docs = retriever.invoke(state["topic"])
    context = "\n\n".join(doc.page_content for doc in docs)
    
    print(f"   [Retriever]: Найдено {len(context)} символов контекста.")

    return {"context": context, "iterations": 0}

def write_post(state: AgentState):
    iteration = state.get("iterations", 0) + 1
    print(f"✍️ [Writer]: Пишу черновик (Попытка {iteration})...")
    
    system_prompt = """Ты — IT-журналист. Напиши пост для Telegram на РУССКОМ ЯЗЫКЕ.
    
    ЖЕСТКОЕ ПРАВИЛО 1: Используй информацию ТОЛЬКО внутри тегов <facts>. 
    ЖЕСТКОЕ ПРАВИЛО 2: ТЕБЕ СТРОГО ЗАПРЕЩЕНО ИСПОЛЬЗОВАТЬ ТЕГИ <facts> В СВОЕМ ОТВЕТЕ. Это системные теги.
    
    <facts>
    {context}
    </facts>"""
    
    if state.get("critique") and not state["critique"].is_approved:
        system_prompt += f"\n\nВНИМАНИЕ! РЕДАКТОР ВЕРНУЛ ТЕКСТ НА ДОРАБОТКУ. ИСПРАВЬ ЭТИ ОШИБКИ:\n{state['critique']}"
        
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Напиши пост на тему: {topic}")
    ])
    
    chain = prompt | llm | StrOutputParser()
    draft = chain.invoke({"context": state["context"], "topic": state["topic"]})
    
    return {"draft": draft, "iterations": iteration}

def critique_post(state: AgentState):
    print("🧐 [Critic]: Ищу галлюцинации в черновике...")
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", """Ты — безжалостный редактор-фактчекер. Твоя единственная цель — найти ложь.
        
        Сравни <draft> (текст автора) с <facts> (исходные данные).
        
        <facts>
        {context}
        </facts>
        
        <draft>
        {draft}
        </draft>
        
        ПРАВИЛА:
        1. Если в <draft> есть имена (например, Марсель Дутш), даты, концепции или проекты, которых НЕТ в <facts> — это галлюцинация.
        2. Если ты нашел галлюцинацию, напиши ЧТО ИМЕННО выдумано и строго прикажи это убрать.
        3. Если черновик ИДЕАЛЬНО совпадает с фактами, выведи ровно одно слово: APPROVE. Никаких других слов, символов или пересказов текста!"""),
        ("human", "Твой вердикт?")
    ])
    struct_llm = llm.with_structured_output(CriticVerdict)
    
    chain = prompt | struct_llm

    verdict = chain.invoke({"context": state["context"], "draft": state["draft"]})
    
    return {"critique": verdict}


# УЗЕЛ WEB_seracher

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




# ==========================================
# 3. ЛОГИКА МАРШРУТИЗАЦИИ (EDGES)
# ==========================================
def should_continue(state: AgentState):
    verdict = state["critique"]
    iterations = state["iterations"]
    
    print(f"   [Routing]: Ответ критика: {verdict.feedback[:100]}...") # Печатаем кусок ответа
    
    # ЖЕСТКОЕ УСЛОВИЕ: Только точное совпадение или защита от бесконечного цикла
    if verdict.is_approved or iterations >= 3:
        print("   [Routing]: ✅ Пост ИДЕАЛЕН. Завершаю работу.")
        return "end"
    else:
        print("   [Routing]: ❌ КРИТИК НАШЕЛ БРЕД! Отправляю Писателю на переделку.")
        return "continue"


def check_context(state: AgentState):
    context = state["context"]

    if not context or len(context.strip()) < 100:
        print("   [Routing]: ⚠️ Локального контекста недостаточно. Нужен интернет!")
        return "search_internet"
    else:
        print("   [Routing]: ⚠️ Локального контекста недостаточно. Нужен интернет!")
        return "search_internet"

# ==========================================
# 4. СБОРКА ГРАФА
# ==========================================
workflow = StateGraph(AgentState)

workflow.add_node("retriever", retrieve_info)
workflow.add_node("writer", write_post)
workflow.add_node("critic", critique_post)
workflow.add_node('web_searcher', web_searcher)


workflow.add_edge(START, "retriever")


workflow.add_conditional_edges(
    "retriever",
    check_context,
    {
        "search_internet":"web_searcher",
        "write": "writer"
    }
)

workflow.add_edge("web_searcher", "writer")

workflow.add_edge("writer", "critic") # После Писателя всегда идет Критик

# Условное ребро после Критика
workflow.add_conditional_edges(
    "critic",
    should_continue,
    {
        "continue": "writer", # Если есть ошибки -> обратно к писателю
        "end": END            # Если всё ок -> конец
    }
)

app = workflow.compile()

# ==========================================
# 5. ТЕСТ
# ==========================================
if __name__ == "__main__":
    # 1. Сначала проверяем, как работает локальный RAG (если тема есть в ChromaDB)
    print("\n--- ТЕСТ 1: Запрос по локальной базе (Хабр) ---")
    # Передай тему, статьи по которой твой парсер ТОЧНО скачивал
    local_topic = "Почему автономия без сигналов для AI-агента — это разгон в тумане" 
    
    print(f"🚀 Запуск графа для локальной темы: '{local_topic}'...\n")
    state_local = app.invoke({"topic": local_topic})
    print("\n✅ ИТОГОВЫЙ ПОСТ ИЗ ЛОКАЛЬНОЙ БАЗЫ:\n")
    print(state_local["draft"])

    print("\n" + "="*50 + "\n")

    # 2. А теперь тестируем Агента-Интернета (CRAG)
    print("--- ТЕСТ 2: Запрос через Интернет (DuckDuckGo) ---")
    # Передаем абсолютно новую тему 2026 года, которой 100% нет в твоем локальном ChromaDB
    web_topic = "Выход новой нейросети GPT-5 от OpenAI и ее главные архитектурные фичи"
    
    print(f"🚀 Запуск графа для интернет-темы: '{web_topic}'...\n")
    state_web = app.invoke({"topic": web_topic})
    print("\n✅ ИТОГОВЫЙ ПОСТ С ИСПОЛЬЗОВАНИЕМ ИНТЕРНЕТА:\n")
    print(state_web["draft"])