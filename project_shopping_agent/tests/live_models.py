"""Model selection for the live tests and evals. Import this BEFORE any project module.

By default chat and the off-topic check run on openai/gpt-oss-120b, so testing never
uses up Qwen's free daily quota, whatever .env says. Photos still use
GROQ_VISION_MODEL from .env (Qwen is the only image model on the key).

  --app-model          use the models in .env instead
  --model NAME         use another Groq chat model (e.g. openai/gpt-oss-20b, which has
                       its own daily quota)
"""

import os
import sys

TEST_MODEL = "openai/gpt-oss-120b"


def _take_flag(flag: str, has_value: bool = False) -> str | bool | None:
    if flag not in sys.argv:
        return None
    i = sys.argv.index(flag)
    value = sys.argv[i + 1] if has_value else True
    del sys.argv[i:i + (2 if has_value else 1)]
    return value


USE_APP_MODEL = bool(_take_flag("--app-model"))
chosen = _take_flag("--model", has_value=True) or TEST_MODEL

if not USE_APP_MODEL:
    # Set before config.py loads .env (load_dotenv does not override these).
    os.environ["GROQ_MODEL"] = chosen
    os.environ["GROQ_GUARDRAIL_MODEL"] = chosen
    os.environ["GROQ_REASONING_EFFORT"] = "low" if chosen.startswith("openai/gpt-oss") else "none"
