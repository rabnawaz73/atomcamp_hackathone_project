import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MEDICAL_KNOWLEDGE = [
    {
        "topic": "Hydration",
        "content": (
            "Adults should aim for 2-3 litres of water daily. Signs of dehydration include "
            "dark urine, dry mouth, fatigue, and dizziness. Increase intake during exercise "
            "and hot weather."
        ),
    },
    {
        "topic": "Common Cold",
        "content": (
            "Common cold symptoms include runny nose, sore throat, cough, and mild fever. "
            "Rest, fluids, and over-the-counter symptom relief are usually sufficient. "
            "See a doctor if symptoms persist beyond 10 days or worsen significantly."
        ),
    },
    {
        "topic": "Blood Pressure",
        "content": (
            "Normal blood pressure is typically below 120/80 mmHg. Hypertension (high blood "
            "pressure) often has no symptoms. Lifestyle changes include reducing sodium, "
            "regular exercise, maintaining healthy weight, and limiting alcohol."
        ),
    },
    {
        "topic": "Diabetes Management",
        "content": (
            "Type 2 diabetes management includes monitoring blood glucose, balanced meals "
            "with controlled carbohydrates, regular physical activity, and medication "
            "adherence as prescribed. Regular HbA1c checks are recommended."
        ),
    },
    {
        "topic": "Stress and Anxiety",
        "content": (
            "Managing stress includes deep breathing exercises, regular physical activity, "
            "adequate sleep (7-9 hours), mindfulness meditation, and maintaining social "
            "connections. Seek professional help if anxiety interferes with daily life."
        ),
    },
    {
        "topic": "Exercise Guidelines",
        "content": (
            "WHO recommends at least 150 minutes of moderate aerobic activity or 75 minutes "
            "of vigorous activity per week, plus muscle-strengthening activities twice weekly. "
            "Start gradually if new to exercise."
        ),
    },
    {
        "topic": "Sleep Hygiene",
        "content": (
            "Good sleep hygiene includes consistent sleep schedule, cool dark bedroom, "
            "avoiding screens 1 hour before bed, limiting caffeine after 2 PM, and "
            "aiming for 7-9 hours of sleep for adults."
        ),
    },
    {
        "topic": "Allergies",
        "content": (
            "Allergic reactions range from mild (sneezing, itching) to severe (anaphylaxis). "
            "Common triggers include pollen, dust mites, pet dander, and certain foods. "
            "Antihistamines help mild symptoms; use epinephrine auto-injector for anaphylaxis."
        ),
    },
    {
        "topic": "Headache",
        "content": (
            "Tension headaches are the most common type, often caused by stress, poor posture, "
            "or dehydration. Rest, hydration, and OTC pain relievers may help. Seek immediate "
            "care for sudden severe headache, headache with fever/stiff neck, or after head injury."
        ),
    },
    {
        "topic": "Nutrition Basics",
        "content": (
            "A balanced diet includes fruits, vegetables, whole grains, lean proteins, and "
            "healthy fats. Limit processed foods, added sugars, and excessive sodium. "
            "Portion control and variety are key principles."
        ),
    },
]

_vectorstore = None


def _get_chroma_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data" / "chroma"


def get_rag_context(query: str, k: int = 3) -> str:
    """Retrieve relevant medical knowledge for a user query."""
    global _vectorstore

    try:
        from langchain_community.vectorstores import Chroma
        from langchain_openai import OpenAIEmbeddings
        from langchain_core.documents import Document

        from healthguardian.config import get_settings

        settings = get_settings()
        chroma_dir = _get_chroma_dir()
        chroma_dir.mkdir(parents=True, exist_ok=True)

        if settings.openrouter_api_key:
            embeddings = OpenAIEmbeddings(
                model="openai/text-embedding-3-small",
                openai_api_key=settings.openrouter_api_key,
                openai_api_base="https://openrouter.ai/api/v1",
            )
        else:
            return _keyword_fallback(query)

        if _vectorstore is None:
            if (chroma_dir / "chroma.sqlite3").exists():
                _vectorstore = Chroma(
                    persist_directory=str(chroma_dir),
                    embedding_function=embeddings,
                )
            else:
                docs = [
                    Document(page_content=item["content"], metadata={"topic": item["topic"]})
                    for item in MEDICAL_KNOWLEDGE
                ]
                _vectorstore = Chroma.from_documents(
                    documents=docs,
                    embedding=embeddings,
                    persist_directory=str(chroma_dir),
                )

        results = _vectorstore.similarity_search(query, k=k)
        if not results:
            return _keyword_fallback(query)

        return "\n\n".join(
            f"[{doc.metadata.get('topic', 'General')}] {doc.page_content}" for doc in results
        )
    except Exception as exc:
        logger.warning("RAG retrieval failed, using keyword fallback: %s", exc)
        return _keyword_fallback(query)


def _keyword_fallback(query: str) -> str:
    """Simple keyword matching when vector store is unavailable."""
    query_lower = query.lower()
    matches = []
    for item in MEDICAL_KNOWLEDGE:
        if any(word in query_lower for word in item["topic"].lower().split()):
            matches.append(f"[{item['topic']}] {item['content']}")
        elif any(word in item["content"].lower() for word in query_lower.split() if len(word) > 4):
            matches.append(f"[{item['topic']}] {item['content']}")

    if not matches:
        matches = [f"[{item['topic']}] {item['content']}" for item in MEDICAL_KNOWLEDGE[:3]]

    return "\n\n".join(matches[:3])
