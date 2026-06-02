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
            {"name": "Gemma 2 9B", "model_id": "gemma2-9b-it", "ability": ["text"]},
        ]
    },
    "cerebras": {
        "name": "Cerebras",
        "models": [
            {"name": "gpt-oss-120b", "model_id": "gpt-oss-120b", "ability": ["text"]},
            {"name": "Llama 3.1 8B", "model_id": "llama3.1-8b", "ability": ["text"]},
        ]
    },
    "sambanova": {
        "name": "SambaNova",
        "models": [
            {"name": "DeepSeek-V3.1", "model_id": "DeepSeek-V3.1", "ability": ["text"]},
            {"name": "Llama 3.2 11B Vision", "model_id": "Llama-3.2-11B-Vision-Instruct", "ability": ["text", "vision"]},
            {"name": "Qwen2.5 72B", "model_id": "Qwen2.5-72B-Instruct", "ability": ["text"]},
        ]
    },
    "mistral": {
        "name": "Mistral",
        "models": [
            {"name": "mistral-small-latest", "model_id": "mistral-small-latest", "ability": ["text"]},
            {"name": "Mistral Small", "model_id": "mistral-small-latest", "ability": ["text"]},
            {"name": "Codestral", "model_id": "codestral-latest", "ability": ["text", "code"]},
        ]
    },
}