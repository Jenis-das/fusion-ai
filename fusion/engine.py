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
        
        self.judge_provider = data.get("judge").get("provider")
        if self.judge_provider not in self.models_available:
            raise Exception(f"Judge provider '{self.judge_provider}' is not available")
        
        self.workers = data.get("workers")
        self.users_question = self.workers.get("prompt")

        # ── conversation history ──────────────────────────────────────────────
        # List of {"role": "user"|"assistant", "content": "..."} dicts.
        # Workers receive the full history + the new user prompt.
        # Judge never receives history — it only compares the current round.
        self.history = data.get("history", [])   # [] on first message

        if self.model_checker(self.workers.get("models")):
            raise Exception("Model Not available")

        self.judge_data = data.get("judge")
        self.all_ai_result = None
        self.judge_result = None
        asyncio.run(self.run())

    async def run(self):
        self.all_ai_result = await self.call_worker(self.workers)
        self.judge_result = await self.judge(self.judge_data)

    # ── Judge: stateless, sees only current question + worker answers ─────────
    async def judge(self, judge_data):
        judge_provider = judge_data.get("provider")
        prompt = judge_data.get("prompt")
        users_question = self.users_question
        combiner = f"{prompt}\n\nQuestion asked by the user: '{users_question}'\n\n"
        for data in self.all_ai_result:
            model_name = data.get("model_info", {}).get("model_name")
            provider   = data.get("model_info", {}).get("provider")
            content    = data.get("content")
            combiner  += f"--- {model_name} ({provider}) ---\n{content}\n\n"

        # print(combiner)
        judge_result = await self.models_available[judge_provider](combiner, judge_data)
        return {
            "judge_provider": judge_provider,
            "result": judge_result
        }

    # ── Workers: receive full conversation history ────────────────────────────
    async def call_worker(self, worker_data):
        prompt = worker_data.get("prompt")
        tasks = []
        provider_names = []

        for provider_name, call_model in self.models_available.items():
            if provider_name in worker_data.get("models").keys():
                if provider_name == self.judge_provider:
                    continue
                # Build the messages list: history + new user turn
                messages = self._build_messages(prompt)
                tasks.append(call_model(messages=messages))
                provider_names.append(provider_name)

        results = await asyncio.gather(*tasks, return_exceptions=True)
        worker_result = []
        for provider_name, result in zip(provider_names, results):
            if isinstance(result, Exception):
                worker_result.append({
                    "model_info": {"provider": provider_name, "model_name": "unknown"},
                    "content": None,
                    "status": "failed",
                    "error": str(result)
                })
            else:
                worker_result.append(result)

        return worker_result

    def _build_messages(self, new_prompt):
        """
        Build the OpenAI-style messages list for workers:
        [
            {"role": "user",      "content": "..."},
            {"role": "assistant", "content": "..."},
            ...
            {"role": "user",      "content": new_prompt}   ← current question
        ]
        The history comes from the DB (passed in via engine_data["history"]).
        The judge is excluded from history because we don't store individual
        worker answers — we only store the judge's final answer as "assistant".
        So the assistant turns in history are the judge verdicts, which is a
        reasonable representation of the conversation from the user's perspective.
        """
        messages = list(self.history)  # copy
        messages.append({"role": "user", "content": new_prompt})
        return messages

    def model_checker(self, models_data):
        for i in models_data.keys():
            if i not in self.models_available.keys():
                return True
        return False

    # ── Provider implementations ──────────────────────────────────────────────
    # All workers now accept `messages` (list) instead of a plain `prompt` string.
    # The judge still passes a plain string via the old `prompt` arg path.

    async def openrouter(self, prompt=None, judge=None, messages=None):
        openrouter_data = judge if judge is not None else self.workers.get("models").get("openrouter")
        if not openrouter_data:
            raise Exception("Openrouter config not found")

        api_key    = openrouter_data.get("Api-key")
        model_name = openrouter_data.get("model_name")

        # Judge passes a plain string; workers pass a messages list
        payload_messages = messages if messages is not None else [{"role": "user", "content": prompt}]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model_name, "messages": payload_messages},
                    timeout=30.0
                )
                result = response.json()
                print(result)
                choice  = result.get("choices", [])[0]
                message = choice.get("message", {})
                return {
                    "model_info": {"model_name": result.get("model"), "provider": "openrouter"},
                    "content": message.get("content"),
                    "status": "success"
                }
        except Exception as e:
            print(e)
            return {"model_info": {"model_name": model_name, "provider": "openrouter"}, "content": None, "status": "failed", "error": "Api limit exceeded"}


    async def gemini(self, prompt=None, judge=None, messages=None):
        gemini_data = judge if judge is not None else self.workers.get("models").get("gemini")
        if not gemini_data:
            raise Exception("Gemini config not found")

        api_key    = gemini_data.get("Api-key")
        model_name = gemini_data.get("model_name")

        # Gemini uses its own "contents" format
        if messages is not None:
            contents = []
            for msg in messages:
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        else:
            contents = [{"parts": [{"text": prompt}]}]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}",
                    headers={"Content-Type": "application/json"},
                    json={"contents": contents},
                    timeout=30.0
                )
                result    = response.json()
                print(result)
                candidate = result.get("candidates", [])[0]
                content   = candidate.get("content", {}).get("parts", [])[0].get("text")
                return {
                    "model_info": {"model_name": result.get("modelVersion"), "provider": "gemini"},
                    "content": content,
                    "status": "success"
                }
        except Exception as e:
            print(e)
            return {"model_info": {"model_name": model_name, "provider": "gemini"}, "content": None, "status": "failed", "error": "Api limit exceeded"}


    async def groq(self, prompt=None, judge=None, messages=None):
        groq_data = judge if judge is not None else self.workers.get("models").get("groq")
        if not groq_data:
            raise Exception("Groq config not found")

        api_key    = groq_data.get("Api-key")
        model_name = groq_data.get("model_name")

        payload_messages = messages if messages is not None else [{"role": "user", "content": prompt}]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model_name, "messages": payload_messages},
                    timeout=30.0
                )
                result  = response.json()
                print(result)
                choice  = result.get("choices", [])[0]
                message = choice.get("message", {})
                return {
                    "model_info": {"model_name": result.get("model"), "provider": "groq"},
                    "content": message.get("content"),
                    "status": "success"
                }
        except Exception as e:
            return {"model_info": {"model_name": model_name, "provider": "groq"}, "content": None, "status": "failed", "error": "Api limit exceeded"}


    async def sambanova(self, prompt=None, judge=None, messages=None):
        sambanova_data = judge if judge is not None else self.workers.get("models").get("sambanova")
        if not sambanova_data:
            raise Exception("Sambanova config not found")

        api_key    = sambanova_data.get("Api-key")
        model_name = sambanova_data.get("model_name")

        payload_messages = messages if messages is not None else [{"role": "user", "content": prompt}]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sambanova.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model_name, "messages": payload_messages},
                    timeout=30.0
                )
                result  = response.json()
                choice  = result.get("choices", [])[0]
                message = choice.get("message", {})
                print("sambanova", result)
                return {
                    "model_info": {"model_name": result.get("model"), "provider": "sambanova"},
                    "content": message.get("content"),
                    "status": "success"
                }
        except Exception as e:
            return {"model_info": {"model_name": model_name, "provider": "sambanova"}, "content": None, "status": "failed", "error": "Api limit exceeded"}


    async def cerebras(self, prompt=None, judge=None, messages=None):
        cerebras_data = judge if judge is not None else self.workers.get("models").get("cerebras")
        if not cerebras_data:
            raise Exception("Cerebras config not found")

        api_key    = cerebras_data.get("Api-key")
        model_name = cerebras_data.get("model_name")

        payload_messages = messages if messages is not None else [{"role": "user", "content": prompt}]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model_name, "messages": payload_messages},
                    timeout=30.0
                )
                result  = response.json()
                choice  = result.get("choices", [])[0]
                message = choice.get("message", {})
                print(result)
                return {
                    "model_info": {"model_name": result.get("model"), "provider": "cerebras"},
                    "content": message.get("content"),
                    "status": "success"
                }
        except Exception as e:
            return {"model_info": {"model_name": model_name, "provider": "cerebras"}, "content": None, "status": "failed", "error": "Api limit exceeded"}


    async def mistral(self, prompt=None, judge=None, messages=None):
        mistral_data = judge if judge is not None else self.workers.get("models").get("mistral")
        if not mistral_data:
            raise Exception("Mistral config not found")

        api_key    = mistral_data.get("Api-key")
        model_name = mistral_data.get("model_name")

        payload_messages = messages if messages is not None else [{"role": "user", "content": prompt}]

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.mistral.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model_name, "messages": payload_messages},
                    timeout=30.0
                )
                result  = response.json()
                choice  = result.get("choices", [])[0]
                message = choice.get("message", {})
                print(result)
                return {
                    "model_info": {"model_name": result.get("model"), "provider": "mistral"},
                    "content": message.get("content"),
                    "status": "success"
                }
        except Exception as e:
            return {"model_info": {"model_name": model_name, "provider": "mistral"}, "content": None, "status": "failed", "error": "Api limit exceeded"}