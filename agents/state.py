from pydantic import BaseModel, Field
from typing import TypedDict



class CriticVerdict(BaseModel):
    is_approved: bool = Field(description = 'True, если в тексте нет галлюцинаций и он полностью соответствует фактам. False, если есть ошибки.')
    feedback: str = Field(description="Если is_approved=False, подробно распиши замечания и что нужно исправить. Если True, оставь поле пустым.")


class AgentState(TypedDict):
    topic: str
    context: str
    draft: str
    critique: CriticVerdict
    iterations: int
