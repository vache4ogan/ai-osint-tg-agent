from pydantic import Field, BaseModel
from typing import List
from src.llm_core import llm


class ExtractedEntity(BaseModel):
    name: str = Field(description="Название сущности (например: OpenAI, Python, RAG)")
    label: str = Field(description="Тип сущности. Строго одно из: ORG (компании), TECH (технологии/фреймворки), PERSON (люди)")

class NERResult(BaseModel):
    entities: List[ExtractedEntity]

def extract_entities_from_text(text: str) -> List[ExtractedEntity]:
    """Прогоняет кусок текста через LLM для поиска сущностей"""
    
    # Используем Ollama со структурированным выводом
    struct_llm = llm.with_structured_output(NERResult)
    
    prompt = f"""Ты — ИИ-аналитик. Твоя задача найти в тексте компании (ORG), технологии (TECH) и имена людей (PERSON).
    Если ничего нет, верни пустой список.
    Текст: {text[:1000]}...""" # Берем начало статьи для экономии времени
    
    try:
        result = struct_llm.invoke(prompt)
        return result.entities
    except Exception as e:
        print(f"Ошибка NER: {e}")
        return []