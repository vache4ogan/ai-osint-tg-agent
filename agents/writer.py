from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from src.llm_core import llm
from agents.state import AgentState

def write_post(state: AgentState):
    """Генерирует черновик на основе контекста"""
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
