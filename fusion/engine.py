import httpx
import asyncio

class llms:
    def __init__(self, data):
        self.models_available = {
            "openrouter": self.openrouter,
            "gemini": self.gemini,
            "groq": self.groq,
            "sambanova": self.sambanova,
            "cerebras": self.cerebras,
            "mistral": self.mistral
        }
        
        self.judge_provider = data.get("judge").get("provider")  # e.g. "groq"
        if self.judge_provider not in self.models_available:
            raise Exception(f"Judge provider '{self.judge_provider}' is not available")
        
        self.workers = data.get("workers")
        self.users_question = self.workers.get("prompt")
        
        if self.model_checker(self.workers.get("models")):
            raise Exception("Model Not available")

        self.judge_data = data.get("judge")
        self.all_ai_result = None
        self.judge_result = None
        asyncio.run(self.run())  

    async def run(self):
        self.all_ai_result = await self.call_worker(self.workers)
        self.judge_result = await self.judge(self.judge_data)

    async def judge(self, judge_data):
        judge_provider = judge_data.get("provider")   # company name: "groq"
        prompt = judge_data.get("prompt")
        users_question = self.users_question 
        combiner = f"{prompt}\n question Asked by the user '{users_question}' \n\n"
        for data in self.all_ai_result:
            model_name = data.get("model_info", {}).get("model_name")
            provider = data.get("model_info", {}).get("provider")
            content = data.get("content")
            combiner += f"--- {model_name} ({provider}) ---\n{content}\n\n"
        
        print(combiner)
        judge_result = await self.models_available.get(judge_provider)(combiner, judge_data)
        return {
            "judge_provider": judge_provider,
            "result": judge_result
        }

    async def call_worker(self, worker_data):
        prompt = worker_data.get("prompt")
        tasks = []
        provider_names = []
        
        for provider_name, call_model in self.models_available.items():
            if provider_name in worker_data.get("models").keys():
                if provider_name == self.judge_provider:
                    continue
                tasks.append(call_model(prompt))
                provider_names.append(provider_name)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        worker_result = []
        for provider_name, result in zip(provider_names, results):
            if isinstance(result, Exception):
                worker_result.append({provider_name: f"Error: {str(result)}"})
            else:
                worker_result.append(result)

        return worker_result

    def model_checker(self, models_data):
        for i in models_data.keys():
            if i not in self.models_available.keys():
                return True
        return False


    async def openrouter(self, prompt, judge=None):
        openrouter_data = judge if judge is not None else self.workers.get("models").get("openrouter")
        
        if not openrouter_data:
            raise Exception("Openrouter config not found")

        api_key = openrouter_data.get("Api-key")
        model_name = openrouter_data.get("model_name")   # e.g. "openrouter/free"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    timeout=30.0
                )
                result = response.json()
                choice = result.get("choices", [])[0]
                message = choice.get("message", {})

                return {
                    "model_info": {
                        "model_name": result.get("model"),
                        "provider": "openrouter",
                    },
                    "content": message.get("content"),
                    "status": "success"
                }
        except Exception as e:
            return {
                "model_info": {
                    "model_name": model_name,
                    "provider": "openrouter",
                },
                "content": None,
                "status": "failed",
                "error": str(e)
            }


    async def gemini(self, prompt, judge=None):
        gemini_data = judge if judge is not None else self.workers.get("models").get("gemini")

        if not gemini_data:
            raise Exception("Gemini config not found")
        
        api_key = gemini_data.get("Api-key")
        model_name = gemini_data.get("model_name")   # e.g. "gemini-2.5-flash"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}",
                    headers={"Content-Type": "application/json"},
                    json={
                        "contents": [
                            {
                                "parts": [
                                    {"text": prompt}
                                ]
                            }
                        ]
                    },
                    timeout=30.0
                )
                result = response.json()
                candidate = result.get("candidates", [])[0]
                content = candidate.get("content", {}).get("parts", [])[0].get("text")

                return {
                    "model_info": {
                        "model_name": result.get("modelVersion"),
                        "provider": "gemini",
                    },
                    "content": content,
                    "status": "success"
                }

        except Exception as e:
            return {
                "model_info": {
                    "model_name": model_name,
                    "provider": "gemini",
                },
                "content": None,
                "status": "failed",
                "error": str(e)
            }

    async def groq(self, prompt, judge=None):
        groq_data = judge if judge is not None else self.workers.get("models").get("groq")
        
        if not groq_data:
            raise Exception("Groq config not found")

        api_key = groq_data.get("Api-key")
        model_name = groq_data.get("model_name")   # e.g. "llama-3.1-8b-instant"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    timeout=30.0
                )
                result = response.json()
                choice = result.get("choices", [])[0]
                message = choice.get("message", {})

                return {
                    "model_info": {
                        "model_name": result.get("model"),
                        "provider": "groq",
                    },
                    "content": message.get("content"),
                    "status": "success"
                }

        except Exception as e:
            return {
                "model_info": {
                    "model_name": model_name,
                    "provider": "groq",
                },
                "content": None,
                "status": "failed",
                "error": str(e)
            }
    
    async def sambanova(self, prompt, judge=None):
        sambanova_data = judge if judge is not None else self.workers.get("models").get("sambanova")

        if not sambanova_data:
            raise Exception("Sambanova config not found")

        api_key = sambanova_data.get("Api-key")
        model_name = sambanova_data.get("model_name")   # e.g. "DeepSeek-V3.1"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sambanova.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    timeout=30.0
                )
                result = response.json()
                choice = result.get("choices", [])[0]
                message = choice.get("message", {})

                return {
                    "model_info": {
                        "model_name": result.get("model"),
                        "provider": "sambanova",
                    },
                    "content": message.get("content"),
                    "status": "success"
                }

        except Exception as e:
            return {
                "model_info": {
                    "model_name": model_name,
                    "provider": "sambanova",
                },
                "content": None,
                "status": "failed",
                "error": str(e)
            }

    async def cerebras(self, prompt, judge=None):
        cerebras_data = judge if judge is not None else self.workers.get("models").get("cerebras")

        if not cerebras_data:
            raise Exception("Cerebras config not found")

        api_key = cerebras_data.get("Api-key")
        model_name = cerebras_data.get("model_name")   # e.g. "gpt-oss-120b"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    timeout=30.0
                )
                result = response.json()
                choice = result.get("choices", [])[0]
                message = choice.get("message", {})

                return {
                    "model_info": {
                        "model_name": result.get("model"),
                        "provider": "cerebras",
                    },
                    "content": message.get("content"),
                    "status": "success"
                }

        except Exception as e:
            return {
                "model_info": {
                    "model_name": model_name,
                    "provider": "cerebras",
                },
                "content": None,
                "status": "failed",
                "error": str(e)
            }

    async def mistral(self, prompt, judge=None):
        mistral_data = judge if judge is not None else self.workers.get("models").get("mistral")

        if not mistral_data:
            raise Exception("Mistral config not found")

        api_key = mistral_data.get("Api-key")
        model_name = mistral_data.get("model_name")   # e.g. "mistral-small-latest"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model_name,
                        "messages": [{"role": "user", "content": prompt}]
                    },
                    timeout=30.0
                )
                result = response.json()
                choice = result.get("choices", [])[0]
                message = choice.get("message", {})

                return {
                    "model_info": {
                        "model_name": result.get("model"),
                        "provider": "mistral",
                    },
                    "content": message.get("content"),
                    "status": "success"
                }

        except Exception as e:
            return {
                "model_info": {
                    "model_name": model_name,
                    "provider": "mistral",
                },
                "content": None,
                "status": "failed",
                "error": str(e)
            }


# data = {
#     "judge": {
#         "provider": "groq",                          # company name
#         "Api-key": "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",
#         "model_name": "llama-3.1-8b-instant",        # actual model name
#         "prompt": "You are judge all other ai present here now you have to evaluate all the answers provided by the other ai and give the correct answer"
#     },
#     "workers": {
#         "prompt": "If a train travels 120km in 1.5 hours, what is its speed in km/h and m/s ?",
#         "models": {
#             "gemini": {
#                 "Api-key": "AIzaSyCKjWH_anOmP3JvMdGfxpXUimCjva6tsKs",
#                 "model_name": "gemini-2.5-flash",    # actual model name
#             },
#             # "openrouter": {
#             #     "Api-key": "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",
#             #     "model_name": "openrouter/free",     # actual model name
#             # },
#             "groq": {
#                 "Api-key": "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",
#                 "model_name": "llama-3.1-8b-instant", # actual model name
#             },
#             # "sambanova": {
#             #     "Api-key": "c67624f7-c28f-4a00-81b0-9fe3d23ef977",
#             #     "model_name": "DeepSeek-V3.1",       # actual model name
#             # },
#             "cerebras": {
#                 "Api-key": "csk-82thdd29n4mxwtx3kft4jmyw594r3426px2m4kn5feyh9hkp",
#                 "model_name": "gpt-oss-120b",        # actual model name
#             },
#             "mistral": {
#                 "Api-key": "B493Xa3BneNY00eERygvEVhG1MUMzrVo",
#                 "model_name": "mistral-small-latest", # actual model name
#             },
#         }
#     }
# }

# result = llms(data)
# print(result.all_ai_result)
# print(result.judge_result)