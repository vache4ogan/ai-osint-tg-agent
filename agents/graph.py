# src/graph.py
from langgraph.graph import StateGraph, START, END

# Импортируем состояние и всех агентов
from agents.state import AgentState
from agents.researcher import retrieve_info, web_searcher, check_context
from agents.writer import write_post
from agents.critic import critique_post, should_continue

# ==========================================
# СБОРКА ГРАФА
# ==========================================
workflow = StateGraph(AgentState)

# Добавляем узлы
workflow.add_node("retriever", retrieve_info)
workflow.add_node("writer", write_post)
workflow.add_node("critic", critique_post)
workflow.add_node('web_searcher', web_searcher)

# Добавляем связи (ребра)
workflow.add_edge(START, "retriever")

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

workflow.add_conditional_edges(
    "critic",
    should_continue,
    {
        "continue": "writer", 
        "end": END            
    }
)

# Компилируем граф
app = workflow.compile()