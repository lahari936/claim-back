"""The only module that calls the LLM API. Never log prompt or response text (may hold patient data)."""
import base64
import logging
import os

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from app.models import LLMCall, Session

log = logging.getLogger(__name__)

# max_retries: the SDK backs off on 429/5xx, which the free NVIDIA tier returns under load.
client = OpenAI(base_url=os.environ["NEBIUS_BASE_URL"], api_key=os.environ["NEBIUS_API_KEY"], max_retries=4)

TIERS = ("vision", "fast", "agent", "reason", "embed")
MODELS = {t: os.environ[f"MODEL_{t.upper()}"] for t in TIERS}
# USD per 1M tokens as "input,output", e.g. PRICE_REASON=0.6,2.4. Defaults to free.
PRICES = {t: tuple(float(x) for x in os.environ.get(f"PRICE_{t.upper()}", "0,0").split(",")) for t in TIERS}


def log_usage(case_id: str | None, tier: str, usage) -> None:
    tin = getattr(usage, "prompt_tokens", 0) or 0
    tout = getattr(usage, "completion_tokens", 0) or 0
    pin, pout = PRICES[tier]
    with Session.begin() as s:
        s.add(LLMCall(case_id=case_id, tier=tier, model=MODELS[tier], input_tokens=tin, output_tokens=tout,
                      cost=(tin * pin + tout * pout) / 1e6))
    log.info("llm tier=%s in=%d out=%d", tier, tin, tout)


def _text(msg) -> str:
    # Reasoning models may leave content empty; fall back to the reasoning field.
    return msg.content or getattr(msg, "reasoning_content", None) or ""


def _json_slice(s: str) -> str:
    # Tolerate ```json fences or stray prose around the object.
    start, end = s.find("{"), s.rfind("}")
    return s[start:end + 1] if start != -1 and end > start else s


def call_json(tier: str, system: str, user: str, schema: type[BaseModel], case_id: str | None):
    for _ in range(2):
        r = client.chat.completions.create(
            model=MODELS[tier],
            messages=[{"role": "system", "content": system + "\nReturn only JSON matching this schema:\n"
                       + str(schema.model_json_schema())},
                      {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        log_usage(case_id, tier, r.usage)
        try:
            return schema.model_validate_json(_json_slice(_text(r.choices[0].message)))
        except ValidationError as e:
            user += f"\n\nYour last output failed validation: {e}. Fix it."
    raise RuntimeError("LLM output invalid after retry")


def transcribe_image(png: bytes, case_id: str | None) -> str:
    # /no_think: with thinking on, the Omni model loops on long transcriptions.
    r = client.chat.completions.create(
        model=MODELS["vision"],
        messages=[{"role": "system", "content": "/no_think"},
                  {"role": "user", "content": [
                      {"type": "text", "text": "Transcribe all text in this image exactly, keeping line breaks. "
                                               "Output only the text."},
                      {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(png).decode()}},
                  ]}],
        temperature=0.2,
        max_tokens=4000,
    )
    log_usage(case_id, "vision", r.usage)
    return r.choices[0].message.content or ""


def embed(texts: list[str], case_id: str | None) -> list[list[float]]:
    r = client.embeddings.create(model=MODELS["embed"], input=texts)
    log_usage(case_id, "embed", r.usage)
    return [d.embedding for d in r.data]
