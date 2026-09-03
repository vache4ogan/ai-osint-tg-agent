import asyncio
from agents.graph import app
from src.evaluator import evaluate_single_response

async def main():
    print("🤖 Запускаем тестовый прогон пайплайна (без Telegram)...")
    topic = "Машинное обучение в 2024 году"
    
    print(f"\n1️⃣ Тема запроса: {topic}")
    print("⏳ Агенты (Researcher, Writer, Critic) работают...")
    
    # 1. Запуск графа
    initial_state = {"topic": topic}
    final_state = await asyncio.to_thread(app.invoke, initial_state)
    
    draft = final_state.get("draft", "Нет черновика")
    context = final_state.get("context", "")
    is_factual = final_state.get("is_factual", False)
    
    print("\n✅ Агенты завершили работу!")
    print("-" * 50)
    print("ЧЕРНОВИК:\n", draft)
    print("-" * 50)
    print(f"Пройдена ли проверка фактов (is_factual): {is_factual}")
    
    # 2. Оценка через Ragas
    print("\n⏳ Запускаем Ragas оценку (Faithfulness, Answer Relevancy)...")
    metrics = await asyncio.to_thread(evaluate_single_response, topic, draft, context)
    
    print("\n✅ Оценка завершена!")
    print("📊 Метрики качества (Ragas):")
    print(f"• Faithfulness (нет галлюцинаций): {metrics['faithfulness']}")
    print(f"• Answer Relevancy (по теме): {metrics['answer_relevancy']}")
    
if __name__ == "__main__":
    asyncio.run(main())
