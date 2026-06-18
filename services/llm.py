from healthguardian.config import get_settings


def get_crewai_llm():
    """Return a CrewAI-compatible LLM configured for OpenRouter / DeepSeek."""
    settings = get_settings()
    if not settings.openrouter_api_key:
        return None

    try:
        from crewai import LLM
    except ImportError:
        return None

    model_name = settings.openrouter_model
    # Remove prefix if present, then add single openrouter/ prefix for CrewAI
    if model_name.startswith("openrouter/"):
        model_name = model_name.replace("openrouter/", "", 1)

    return LLM(
        model=f"openrouter/{model_name}",
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
        temperature=0.7,
        max_tokens=2048,
    )


def get_openai_client():
    """Return an OpenAI client pointed at OpenRouter for streaming chat."""
    from openai import OpenAI

    settings = get_settings()
    if not settings.openrouter_api_key:
        return None

    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=settings.openrouter_api_key,
    )


def stream_chat_completion(messages: list[dict], model: str | None = None):
    """Yield tokens from a streaming chat completion."""
    client = get_openai_client()
    settings = get_settings()

    if client is None:
        yield (
            "⚠️ OpenRouter API key not configured. "
            "Please set OPENROUTER_API_KEY in your .env file."
        )
        return

    raw_model = model or settings.openrouter_model
    clean_model = raw_model
    if clean_model.startswith("openrouter/"):
        clean_model = clean_model.replace("openrouter/", "", 1)

    response = client.chat.completions.create(
        model=clean_model,
        messages=messages,
        stream=True,
        max_tokens=2048,
    )
    for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
