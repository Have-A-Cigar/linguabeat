"""Translation service: Google Cloud Translate v2 + LLM fallback for ambiguous words."""

from __future__ import annotations

import os
from typing import Optional

import httpx

# Russian words where literal translation loses context — route through LLM
_HOMONYMS: frozenset[str] = frozenset({
    "замок", "коса", "мир", "свет", "лук", "ключ", "среда", "пол",
    "брак", "вид", "год", "дорогой", "злой", "острый", "правый",
    "белый", "красный", "чистый", "старый", "простой", "горький",
    "кисть", "стекло", "стекла", "лист", "листья", "корень", "корни",
    "нота", "нет", "ток", "кран", "бор", "пара", "сток", "течь",
})

_LANG_CODES = {
    "zh": "zh-CN",
    "en": "en",
    "hi": "hi",
    "ar": "ar",
    "es": "es",
}


async def translate(
    word: str,
    context: str,
    target_lang: str = "en",
) -> Optional[str]:
    """Translate *word* in the context of *context* string.

    Strategy:
    1. If word (lower-cased) is in homonym list → LLM fallback for context-aware result.
    2. Otherwise → Google Cloud Translate v2 REST API.
    3. If no API key configured → return None (caller stores NULL, retried later).
    """
    word_lower = word.lower().rstrip(".,!?:;")
    lang_code = _LANG_CODES.get(target_lang, target_lang)

    if word_lower in _HOMONYMS:
        result = await _llm_translate(word, context, lang_code)
        if result:
            return result

    return await _google_translate(word, lang_code)


async def _google_translate(text: str, target: str) -> Optional[str]:
    api_key = os.getenv("GOOGLE_TRANSLATE_API_KEY")
    if not api_key:
        return None

    url = "https://translation.googleapis.com/language/translate/v2"
    params = {
        "q": text,
        "source": "ru",
        "target": target,
        "key": api_key,
        "format": "text",
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            return data["data"]["translations"][0]["translatedText"]
    except Exception:
        return None


async def _llm_translate(word: str, context: str, target: str) -> Optional[str]:
    """Use OpenAI GPT-4o-mini for context-sensitive translation of homonyms."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None

    prompt = (
        f"Translate the Russian word «{word}» in the context of the following line:\n"
        f"«{context}»\n\n"
        f"Target language code: {target}\n"
        f"Reply with ONLY the translated word or short phrase. No explanations."
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 20,
                    "temperature": 0,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return None
