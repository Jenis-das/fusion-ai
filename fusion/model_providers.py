PROVIDERS = {
    "gemini": {
        "name": "Google Gemini",
        "models": [
            {"name": "Gemini 1.5 Pro", "model_id": "gemini-1.5-pro", "ability": ["text"]},
            {"name": "Gemini 1.5 Flash", "model_id": "gemini-1.5-flash", "ability": ["text"]},
            {"name": "Gemini 2.0 Flash", "model_id": "gemini-2.0-flash", "ability": ["text"]},
        ]
    },
    "openrouter": {
        "name": "OpenRouter",
        "models": [
            {"name": "GPT 4o", "model_id": "openai/gpt-4o", "ability": ["text"]},
            {"name": "Claude Sonnet 4", "model_id": "anthropic/claude-sonnet-4", "ability": ["text"]},
            {"name": "Llama 3.3 70B", "model_id": "meta-llama/llama-3.3-70b-instruct", "ability": ["text"]},
        ]
    },
    "groq": {
        "name": "Groq",
        "models": [
            {"name": "Llama 3.3 70B", "model_id": "llama-3.3-70b-versatile", "ability": ["text"]},
            {"name": "Llama 3.1 8B", "model_id": "llama-3.1-8b-instant", "ability": ["text"]},
            {"name": "Mixtral 8x7B", "model_id": "mixtral-8x7b-32768", "ability": ["text"]},
            {"name": "Gemma 2 9B", "model_id": "gemma2-9b-it", "ability": ["text"]},
        ]
    },
    "cerebras": {
        "name": "Cerebras",
        "models": [
            {"name": "Llama 3.3 70B", "model_id": "llama-3.3-70b", "ability": ["text"]},
            {"name": "Llama 3.1 8B", "model_id": "llama3.1-8b", "ability": ["text"]},
        ]
    },
    "sambanova": {
        "name": "SambaNova",
        "models": [
            {"name": "Llama 3.3 70B", "model_id": "Meta-Llama-3.3-70B-Instruct", "ability": ["text"]},
            {"name": "Llama 3.2 11B Vision", "model_id": "Llama-3.2-11B-Vision-Instruct", "ability": ["text", "vision"]},
            {"name": "Qwen2.5 72B", "model_id": "Qwen2.5-72B-Instruct", "ability": ["text"]},
        ]
    },
    "mistral": {
        "name": "Mistral",
        "models": [
            {"name": "Mistral Large", "model_id": "mistral-large-latest", "ability": ["text"]},
            {"name": "Mistral Small", "model_id": "mistral-small-latest", "ability": ["text"]},
            {"name": "Codestral", "model_id": "codestral-latest", "ability": ["text", "code"]},
        ]
    },
}