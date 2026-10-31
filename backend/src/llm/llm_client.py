import os
from dotenv import load_dotenv

load_dotenv()

_ANTHROPIC_CLIENT = None


def mock_llm(prompt: str) -> str:
    """Fallback simulated response when Anthropic API key is missing or call fails."""
    preview = prompt[:60].replace("\n", " ")
    return f"[Simulated LLM response for]: \"{preview}...\" — Prompt processed safely by CAGE guardrails."


def _get_anthropic_client():
    global _ANTHROPIC_CLIENT
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or api_key.strip() in ("", "your_anthropic_api_key_here"):
        return None

    if _ANTHROPIC_CLIENT is None:
        try:
            import anthropic
            _ANTHROPIC_CLIENT = anthropic.Anthropic(api_key=api_key)
        except Exception as e:
            print(f"[LLM Client Warning] Failed to initialize Anthropic client: {e}")
            return None

    return _ANTHROPIC_CLIENT


def call_llm(prompt: str) -> str:
    """
    Executes LLM call using Anthropic Python SDK.
    Falls back to mock_llm if ANTHROPIC_API_KEY is not set or API call errors out.
    """
    client = _get_anthropic_client()

    if client is None:
        return mock_llm(prompt)

    try:
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        if response and response.content and len(response.content) > 0:
            return response.content[0].text
        return mock_llm(prompt)
    except Exception as e:
        print(f"[LLM Client Warning] Anthropic API call error: {e}. Falling back to mock_llm.")
        return mock_llm(prompt)
