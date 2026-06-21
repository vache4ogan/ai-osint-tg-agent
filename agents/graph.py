# src/graph.py
from langgraph.graph import StateGraph, START, END

# Импортируем состояние и всех агентов
from agents.state import AgentState
from agents.researcher import retrieve_info, web_searcher, check_context, route_by_intent
from agents.writer import write_post
from agents.critic import critique_post, should_continue
from agents.data_analyst import sql_analyst_node # Импортируем нашего нового SQL-агента
# ==========================================
# СБОРКА ГРАФА
# ==========================================
workflow = StateGraph(AgentState)

# Добавляем узлы
workflow.add_node("sql_analyst", sql_analyst_node) # <-- НОВЫЙ УЗЕЛ
workflow.add_node("retriever", retrieve_info)
workflow.add_node("writer", write_post)
workflow.add_node("critic", critique_post)
workflow.add_node('web_searcher', web_searcher)

# Добавляем связи (ребра)
workflow.add_conditional_edges(
    START,
    route_by_intent,
    {
        "go_to_sql": "sql_analyst",
        "go_to_rag": "retriever"
    }
)

# Если отработал SQL-аналитик, он собрал цифры в context и сразу передает их Писателю
workflow.add_edge("sql_analyst", "writer")

# Старый контентный пайплайн RAG (остается без изменений)
workflow.add_conditional_edges(
    "retriever",
    check_context,
    {
        "search_internet": "web_searcher",
        "write": "writer"
    }
)
workflow.add_edge("web_searcher", "writer")
workflow.add_edge("writer", "critic")

# Проверка критика (остается без изменений)
workflow.add_conditional_edges(
    "critic",
    should_continue,
    {
        "continue": "writer", 
        "end": END            
    }
)

app = workflow.compile()