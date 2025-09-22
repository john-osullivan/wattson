# agent-core/wattson/autogen_cfg.py
import os
llm_cfg = {
    "model": os.getenv("WATTSON_LLM_MODEL", "gpt-4o-mini"),
    "api_key": os.getenv("OPENAI_API_KEY", ""),
    # if you run a local OpenAI-compatible server:
    # "base_url": os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1"),
    "temperature": 0,
}
