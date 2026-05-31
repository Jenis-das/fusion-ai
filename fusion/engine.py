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
        
        self.judge_name = data.get("judge").get("models")  # "model" not "models"
        
        if self.judge_name not in self.models_available:
            raise Exception(f"Judge '{self.judge_name}' is not available")
        
        self.workers = data.get("workers")
        
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
        judge_model = judge_data.get("models")  # "model" not "models"
        prompt = judge_data.get("prompt")

        combiner = f"You are a Judge AI.\n\nUser Prompt: {prompt}\n\n"
        for data in self.all_ai_result:
            model_name = data.get("model_info", {}).get("model_name")
            provider = data.get("model_info", {}).get("provider")
            content = data.get("content")
            combiner += f"--- {model_name} ({provider}) ---\n{content}\n\n"

        judge_result = await self.models_available.get(judge_model)(combiner, judge_data)
        return {
            "judge": judge_model,
            "result": judge_result
        }

    async def call_worker(self, worker_data):
        prompt = worker_data.get("prompt")
        tasks = []
        model_names = []
        
        for model_name, call_model in self.models_available.items():
            if model_name in worker_data.get("models").keys():
                if model_name == self.judge_name:
                    continue
                tasks.append(call_model(prompt))
                model_names.append(model_name)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        worker_result = []
        for model_name, result in zip(model_names, results):
            if isinstance(result, Exception):
                worker_result.append({model_name: f"Error: {str(result)}"})
            else:
                worker_result.append(result)

        return worker_result

    def model_checker(self, models_data):
        for i in models_data.keys():
            if i not in self.models_available.keys():
                return True
        return False




    async def openrouter(self, prompt, judge = None):
        openrouter_data = None 
        if judge is None:
            openrouter_data = self.workers.get("models").get("openrouter")
        else:
            openrouter_data = judge
        
        
        if not openrouter_data:
            raise Exception("Openrouter config not found")
        api_key = openrouter_data.get("Api-key")
        provider = openrouter_data.get("provider")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": provider,
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
                        "provider": result.get("provider"),
                    },
                    "content": message.get("content"),
                    "status": "success"
                }
        except Exception as e:
            return {
                "model_info": {
                    "model_name": "openrouter",
                    "provider": provider,
                },
                "content": None,
                "status": "failed",
                "error": str(e)
            }



    async def gemini(self, prompt, judge = None):
        gemini_data = None 
        if judge is None:
            gemini_data = self.workers.get("models").get("gemini")
        else:
            gemini_data = judge


        if not gemini_data:
            raise Exception("Gemini config not found")
        
        api_key = gemini_data.get("Api-key")
        provider = gemini_data.get("provider")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{provider}:generateContent?key={api_key}",
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
                usage = result.get("usageMetadata", {})

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
                    "model_name": "gemini",
                    "provider": provider,
                },
                "content": None,
                "status": "failed",
                "error": str(e)
            }

    async def groq(self, prompt, judge = None):
        groq_data = None
        if groq_data is None:
            groq_data = self.workers.get("models").get("groq")
        else:
            groq_data = judge
        
        if not groq_data:
            raise Exception("Groq config not found")

        api_key = groq_data.get("Api-key")
        provider = groq_data.get("provider")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": provider,  # e.g. "llama-3.1-8b-instant"
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
                    "model_name": "groq",
                    "provider": provider,
                },
                "content": None,
                "status": "failed",
                "error": str(e)
            }
    
    async def sambanova(self, prompt, judge = None):
        sambanova_data = None
        if judge is None:
            sambanova_data = self.workers.get("models").get("sambanova")
        else:
            sambanova_data = judge
        if not sambanova_data:
            raise Exception("Sambanova config not found")

        api_key = sambanova_data.get("Api-key")
        provider = sambanova_data.get("provider")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sambanova.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": provider,  # e.g. "DeepSeek-V3.1"
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
                    "model_name": "sambanova",
                    "provider": provider,
                },
                "content": None,
                "status": "failed",
                "error": str(e)
            }    
    async def cerebras(self, prompt, judge = None):
        cerebras_data = None
        if cerebras_data is None:
            cerebras_data = self.workers.get("models").get("cerebras")
        else:
            cerebras_data = judge

        if not cerebras_data:
            raise Exception("Cerebras config not found")

        api_key = cerebras_data.get("Api-key")
        provider = cerebras_data.get("provider")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": provider,  # e.g. "gpt-oss-120b"
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
                    "model_name": "cerebras",
                    "provider": provider,
                },
                "content": None,
                "status": "failed",
                "error": str(e)
            }
        

    async def mistral(self, prompt, judge = None):
        mistral_data = None
        if judge is None:
            mistral_data = self.workers.get("models").get("mistral")
        else:
            mistral_data = judge
        if not mistral_data:
            raise Exception("Mistral config not found")

        api_key = mistral_data.get("Api-key")
        provider = mistral_data.get("provider")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": provider,  # e.g. "mistral-small-latest"
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
                    "model_name": "mistral",
                    "provider": provider,
                },
                "content": None,
                "status": "failed",
                "error": str(e)
            }

    
data = {
    "judge": {
        "models" : "groq",
        "Api-key" : "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",
        "provider": "llama-3.1-8b-instant",
        "prompt" : "You are judge all other ai present here now you have to evaluate all the answers provided by the other ai and give the correct answer"
    },
    "workers": {
        "prompt": "If a train travels 120km in 1.5 hours, what is its speed in km/h and m/s ?",
        "models": {
            "gemini": {
                "Api-key": "AIzaSyCKjWH_anOmP3JvMdGfxpXUimCjva6tsKs",
                "provider": "gemini-2.5-flash",
            },
            "openrouter": {
                "Api-key": "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",
                "provider": "openrouter/free",
            },
            "groq": {
                "Api-key": "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",
                "provider": "llama-3.1-8b-instant",
            },
            "sambanova": {
                "Api-key": "c67624f7-c28f-4a00-81b0-9fe3d23ef977",
                "provider": "DeepSeek-V3.1",
            },
            "cerebras": {
                "Api-key": "csk-82thdd29n4mxwtx3kft4jmyw594r3426px2m4kn5feyh9hkp",
                "provider": "gpt-oss-120b",
            },
            "mistral": {
                "Api-key": "B493Xa3BneNY00eERygvEVhG1MUMzrVo",
                "provider": "mistral-small-latest",
            },
        }
    }
}

result = llms(data)
print(result.all_ai_result)
print(result.judge_result)