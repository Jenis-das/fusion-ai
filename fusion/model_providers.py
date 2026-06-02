PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "models": [
            {"name": "gemini-2.5-flash", "model_id": "gemini-2.5-flash", "ability": ["text"]},
        ]
    },
    "openrouter": {
        "name": "OpenRouter",
        "models": [
            {"name": "Gopenrouter/free", "model_id": "openrouter/free", "ability": ["text"]},
        ]
    },
    "groq": {
        "name": "Groq",
        "models": [
            {"name": "llama-3.1-8b-instant", "model_id": "llama-3.1-8b-instant", "ability": ["text"]},
            {"name": "qwen3-32b", "model_id": "qwen/qwen3-32b", "ability": ["text"]},
            {"name": "groq-compound", "model_id": "groq/compound", "ability": ["text"]},
            {"name": "groq-compound-mini", "model_id": "groq/compound-mini", "ability": ["text"]},
            {"name": "llama-3.3-70b-versatile", "model_id": "llama-3.3-70b-versatile", "ability": ["text"]},
        ]
    },
    "cerebras": {
        "name": "Cerebras",
        "models": [
            {"name": "gpt-oss-120b", "model_id": "gpt-oss-120b", "ability": ["text"]},
            {"name": "zai-glm-4.7", "model_id": "zai-glm-4.7", "ability": ["text"]},
        ]
    },
    "sambanova": {
        "name": "SambaNova",
        "models": [
            {"name": "DeepSeek-V3.1", "model_id": "DeepSeek-V3.1", "ability": ["text"]},
            {"name": "gpt-oss-120b", "model_id": "gpt-oss-120b", "ability": ["text", "vision"]},
            {"name": "Meta-Llama-3.3-70B-Instruct", "model_id": "Meta-Llama-3.3-70B-Instruct", "ability": ["text"]},
            {"name": "gemma-3-12b-it", "model_id": "gemma-3-12b-it", "ability": ["text"]},
            {"name": "gemma-4-31B-it", "model_id": "gemma-4-31B-it", "ability": ["text"]},
            {"name": "Llama-4-Maverick-17B-128E-Instruct", "model_id": "Llama-4-Maverick-17B-128E-Instruct", "ability": ["text"]},
        ]
    },
    "mistral": {
        "name": "Mistral",
        "models": [
            {"name": "mistral-small-latest", "model_id": "mistral-small-latest", "ability": ["text"]},
            {"name": "mistral-small-2603", "model_id": "mistral-small-2603", "ability": ["text"]},
            {"name": "mistral-medium-3-5", "model_id": "mistral-medium-3-5", "ability": ["text", "code"]},
        ]
    },
}