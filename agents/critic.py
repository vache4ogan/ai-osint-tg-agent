# agents/critic.py
from langchain_core.prompts import ChatPromptTemplate
from src.llm_core import llm
from agents.state import AgentState, CriticVerdict

def critique_post(state: AgentState):
    """Проверяет текст на галлюцинации"""
    
    print("🧐 [Critic]: Ищу галлюцинации в черновике...")
    parse_error = state.get("parse_error", "")
    
    messages = [
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
        2. Строго следуй JSON схеме при ответе.
        """)
    ]
    
    if parse_error:
        messages.append(("human", f"В предыдущий раз ты вернул невалидный JSON. Ошибка Pydantic:\n{parse_error}\nИсправь формат и верни строго JSON, соответствующий схеме CriticVerdict."))
    else:
        messages.append(("human", "Твой вердикт?"))
        
    prompt = ChatPromptTemplate.from_messages(messages)
    struct_llm = llm.with_structured_output(CriticVerdict)
    
    chain = prompt | struct_llm

    try:
        verdict = chain.invoke({"context": state["context"], "draft": state["draft"]})
        return {"critique": verdict, "parse_error": ""}
    except Exception as e:
        print(f"⚠️ [Critic]: Ошибка парсинга JSON: {e}")
        return {"parse_error": str(e)}


def should_continue(state: AgentState):
    """Роутер: решает, отправить на перепись, на ретрай критика или закончить"""
    parse_error = state.get("parse_error", "")
    
    if parse_error:
        print("   [Routing]: 🔄 Сбой структуры JSON. Возвращаю Критику на исправление (Retry).")
        return "retry"
        
    verdict = state["critique"]
    iterations = state.get("iterations", 0)
    
    feedback_preview = verdict.feedback[:100] if verdict.feedback else "Ошибок нет."
    print(f"   [Routing]: Ответ критика: {feedback_preview}...") 
    
    # ЖЕСТКОЕ УСЛОВИЕ: Только точное совпадение или защита от бесконечного цикла
    if verdict.is_factual or iterations >= 3:
        print("   [Routing]: ✅ Пост ИДЕАЛЕН. Завершаю работу.")
        return "end"
    else:
        print("   [Routing]: ❌ КРИТИК НАШЕЛ БРЕД! Отправляю Писателю на переделку.")
        return "continue"
