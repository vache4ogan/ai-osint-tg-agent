from pydantic import BaseModel, Field
from typing import TypedDict, List, Optional


class CriticVerdict(BaseModel):
    is_factual: bool = Field(description='True, если в тексте нет галлюцинаций и он полностью соответствует фактам. False, если есть ошибки.')
    feedback: str = Field(description="Если is_factual=False, подробно распиши замечания и что нужно исправить. Если True, оставь поле пустым.")
    hallucinations: List[str] = Field(default=[], description="Список найденных галлюцинаций. Если их нет, оставь список пустым.")


class AgentState(TypedDict):
    topic: str
    context: str
    draft: str
    critique: Optional[CriticVerdict]
    iterations: int
    parse_error: str
