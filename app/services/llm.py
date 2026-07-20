from openai import AsyncOpenAI

from app.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)

SYSTEM_PROMPT = """You generate diagram source code only.
Return raw {diagram_type} syntax with no markdown fences or explanation."""


async def generate_source(prompt: str, diagram_type: str) -> str:
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT.format(diagram_type=diagram_type)},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    content = response.choices[0].message.content
    if not content:
        raise ValueError("OpenAI returned empty diagram source")
    return content.strip()
