import warnings
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy
from langchain_ollama import ChatOllama
from langchain_huggingface import HuggingFaceEmbeddings

# Игнорируем предупреждения Ragas об устаревших импортах
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Инициализируем локальные модели один раз на уровне модуля
evaluator_llm = ChatOllama(model="llama3", temperature=0)
evaluator_embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    model_kwargs={'device': 'cpu'} 
)

faithfulness_metric = Faithfulness()
answer_relevancy_metric = AnswerRelevancy()

def evaluate_single_response(question: str, answer: str, context: str) -> dict:
    """
    Оценивает сгенерированный ответ через Ragas (Faithfulness и Answer Relevancy).
    Возвращает словарь с результатами от 0 до 1.
    """
    # Собираем данные в формате Dataset
    data = {
        "question": [question],
        "answer": [answer],
        # Ragas ожидает список строк для контекста одного вопроса
        "contexts": [[context] if context else [""]] 
    }
    dataset = Dataset.from_dict(data)
    
    try:
        # Запускаем оценку (этот вызов блокирующий, поэтому должен запускаться через to_thread)
        result = evaluate(
            dataset=dataset,
            metrics=[faithfulness_metric, answer_relevancy_metric],
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        )
        return {
            "faithfulness": round(result.get("faithfulness", 0.0), 3),
            "answer_relevancy": round(result.get("answer_relevancy", 0.0), 3)
        }
    except Exception as e:
        print(f"Ragas evaluation error: {e}")
        return {"faithfulness": 0.0, "answer_relevancy": 0.0}
