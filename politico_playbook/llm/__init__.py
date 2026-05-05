"""Model-agnostic LLM access via OpenRouter.

The rest of the pipeline depends on the abstraction here, NOT on any specific
provider's SDK. To swap providers (Anthropic / OpenAI / Google / open models),
change MODEL_ID in .env. No code change.
"""
