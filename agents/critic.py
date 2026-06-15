# agents/critic.py
from langchain_core.prompts import ChatPromptTemplate
from src.llm_core import llm
from agents.state import AgentState, CriticVerdict

def critique_post(state: AgentState):
    """Проверяет текст на галлюцинации"""
    
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


def should_continue(state: AgentState):
    """Роутер: решает, отправить на перепись или закончить"""
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
