"""Call every MODEL_* env var once and print content plus any reasoning field.

Usage: python scripts/smoke_models.py   (reads .env from repo root)
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
client = OpenAI(base_url=os.environ["NEBIUS_BASE_URL"], api_key=os.environ["NEBIUS_API_KEY"])

for tier in ("VISION", "FAST", "AGENT", "REASON"):
    model = os.environ.get(f"MODEL_{tier}")
    print(f"\n=== {tier}: {model}")
    if not model:
        print("  (unset)")
        continue
    try:
        r = client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": "Reply with the single word: pong"}], max_tokens=200
        )
        m = r.choices[0].message
        print("  content:          ", repr(m.content))
        print("  reasoning_content:", repr(getattr(m, "reasoning_content", None)))
        print("  reasoning:        ", repr(getattr(m, "reasoning", None)))
        print("  usage:            ", r.usage)
    except Exception as e:
        print("  ERROR:", e)

model = os.environ.get("MODEL_EMBED")
print(f"\n=== EMBED: {model}")
if model:
    try:
        e = client.embeddings.create(model=model, input="pre-existing disease")
        print("  dims:", len(e.data[0].embedding), " first:", e.data[0].embedding[:3])
    except Exception as ex:
        print("  ERROR:", ex)
else:
    print("  (unset)")
