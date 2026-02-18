#!/usr/bin/env python3
"""
Test if we have API access to GPT-5.3.
Uses OPENAI_API_KEY from environment or .env.
"""

import os
import sys
from pathlib import Path

# Load .env from common locations
for env_path in [
    Path(__file__).parent.parent / ".env",
    Path(__file__).parent.parent / "infrastructure" / "env.ai-automation",
]:
    if env_path.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv(env_path)
            break
        except ImportError:
            pass

try:
    from openai import OpenAI
except ImportError:
    print("Install openai: pip install openai")
    sys.exit(1)

API_KEY = os.getenv("OPENAI_API_KEY")
if not API_KEY:
    print("OPENAI_API_KEY not set. Set it or add to .env")
    sys.exit(1)

client = OpenAI(api_key=API_KEY)
MODELS_TO_TRY = ["gpt-5.3", "gpt-5.3-mini", "gpt-5.2"]

def test_model(model: str) -> bool:
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Reply with exactly: OK"}],
            max_tokens=10,
        )
        content = r.choices[0].message.content
        usage = r.usage
        print(f"  [OK] {model}: {content!r} (tokens: {usage.total_tokens})")
        return True
    except Exception as e:
        err = str(e).lower()
        if "model" in err and ("not found" in err or "does not exist" in err or "invalid" in err):
            print(f"  [NO] {model}: model not available")
        else:
            print(f"  [NO] {model}: {e}")
        return False

print("Testing GPT-5.3 access (OPENAI_API_KEY from env)...")
print()
for model in MODELS_TO_TRY:
    test_model(model)
print()
# List models we can see (optional)
print("Listing available models (first 20)...")
try:
    models = list(client.models.list())
    names = [m.id for m in models if "gpt-5" in m.id][:20]
    for n in sorted(set(names)):
        print(f"  {n}")
except Exception as e:
    print(f"  (list failed: {e})")
