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
        self.history = data.get("history", [])

        if self.model_checker(self.workers.get("models")):
            raise Exception("Model Not available")

        self.judge_data = data.get("judge")
        self.all_ai_result = None
        self.judge_result = None
        asyncio.run(self.run())

    async def run(self):
        self.all_ai_result = await self.call_worker(self.workers)
        self.judge_result = await self.judge(self.judge_data)

    # ─────────────────────────────────────────────────────────────────────────
    # ERROR PARSER
    # Each provider has a different error shape. We handle all of them here.
    #
    # GROQ:
    #   {"error": {"message": "Rate limit reached...", "type": "tokens", "code": "rate_limit_exceeded"}}
    #
    # GEMINI:
    #   {"error": {"code": 429, "message": "Resource has been exhausted...", "status": "RESOURCE_EXHAUSTED"}}
    #   also sometimes has "errors": [{"reason": "rateLimitExceeded"}]
    #
    # OPENROUTER:
    #   {"error": {"code": 429, "message": "Rate limit exceeded: limit_rpd/...", "type": "rate_limit_error"}}
    #   also: {"error": {"message": "Provider returned error", "code": 429, "metadata": {...}}}
    #
    # MISTRAL:
    #   {"object": "error", "message": "Rate limit exceeded", "type": "rate_limited", "param": null, "code": "1300"}
    #   also: {"message": "Requests rate limit exceeded"}  (flat, no "error" wrapper)
    #
    # SAMBANOVA:
    #   OpenAI-compatible: {"error": {"message": "...", "type": "...", "code": "..."}}
    #   429 Too Many Requests for url: https://api.sambanova.ai/v1/...
    #
    # CEREBRAS:
    #   OpenAI-compatible: {"error": {"message": "...", "type": "...", "code": "..."}}
    #   429 status code (sometimes no body)
    # ─────────────────────────────────────────────────────────────────────────

    # Keywords that mean "rate limit / quota exceeded" across all providers
    _RATE_LIMIT_CODES = {
        "rate_limit_exceeded",   # groq, openrouter
        "rate_limited",          # mistral type field
        "1300",                  # mistral numeric code
        "resource_exhausted",    # gemini status (lowercased)
        "ratelimitexceeded",     # gemini reason (lowercased, no underscore)
        "too_many_requests",
        "insufficient_quota",
        "quota_exceeded",
        "429",
    }

    _RATE_LIMIT_PHRASES = (
        "rate limit",        # groq, openrouter, mistral
        "rate_limit",
        "rate limited",
        "resource exhausted",   # gemini
        "resource_exhausted",
        "quota",
        "too many requests",
        "limit exceeded",
        "ratelimit",
    )

    def _is_rate_limit(self, code: str, status: str, message: str) -> bool:
        code_lower    = str(code).lower().strip()
        status_lower  = str(status).lower().replace(" ", "_")
        message_lower = str(message).lower()

        if code_lower in self._RATE_LIMIT_CODES:
            return True
        if status_lower in self._RATE_LIMIT_CODES:
            return True
        if any(p in message_lower for p in self._RATE_LIMIT_PHRASES):
            return True
        return False

    def _parse_error(self, result: dict, provider: str) -> str:
        """
        Extract a clean error string from any provider's JSON error response.
        Returns "Api limit exceeded" for rate-limit errors, or the real message otherwise.
        """

        # ── MISTRAL flat shape (no "error" wrapper) ───────────────────────────
        # {"object": "error", "message": "Rate limit exceeded", "type": "rate_limited", "code": "1300"}
        if result.get("object") == "error":
            msg  = result.get("message", "")
            typ  = result.get("type", "")
            code = str(result.get("code", ""))
            if self._is_rate_limit(code, typ, msg):
                return "Api limit exceeded"
            return msg or f"Unknown error from {provider}"

        # Also handle Mistral's other flat shape: {"message": "Requests rate limit exceeded"}
        if "message" in result and "error" not in result:
            msg = result.get("message", "")
            if self._is_rate_limit("", "", msg):
                return "Api limit exceeded"
            return msg or f"Unknown error from {provider}"

        # ── Standard nested shape: {"error": {...}} ───────────────────────────
        error_obj = result.get("error")

        if isinstance(error_obj, dict):
            msg    = error_obj.get("message", "")
            code   = str(error_obj.get("code", ""))
            status = str(error_obj.get("status", ""))    # gemini uses "RESOURCE_EXHAUSTED"
            typ    = str(error_obj.get("type",   ""))    # openrouter/mistral use "rate_limit_error"

            # Gemini also has nested errors list with "reason"
            reasons = [
                e.get("reason", "")
                for e in error_obj.get("errors", [])
                if isinstance(e, dict)
            ]
            reason_str = " ".join(reasons)

            if self._is_rate_limit(code, status, msg) or self._is_rate_limit("", typ, reason_str):
                return "Api limit exceeded"

            # OpenRouter sometimes embeds the real provider error in metadata
            metadata = error_obj.get("metadata", {})
            if isinstance(metadata, dict):
                raw = metadata.get("raw", "")
                if raw and self._is_rate_limit("", "", str(raw)):
                    return "Api limit exceeded"

            return msg or f"Unknown error from {provider}"

        # ── Gemini plain string error ─────────────────────────────────────────
        if isinstance(error_obj, str):
            if self._is_rate_limit("", "", error_obj):
                return "Api limit exceeded"
            return error_obj

        return f"Unknown error from {provider}"

    # ── Judge: stateless, sees only current question + worker answers ─────────
    # engine.py

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

        # ✅ Judge gets NO history — just the combined worker answers
        judge_result = await self.models_available[judge_provider](
            prompt=combiner, judge=judge_data   # no messages= arg
        )
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
                # ✅ Workers get history (judge replies only) + new user prompt
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
        # ✅ self.history already contains only judge-selected messages (from views.py)
        messages = list(self.history)
        messages.append({"role": "user", "content": new_prompt})
        return messages

    def model_checker(self, models_data):
        for i in models_data.keys():
            if i not in self.models_available.keys():
                return True
        return False

    # ── Provider implementations ──────────────────────────────────────────────

    async def openrouter(self, prompt=None, judge=None, messages=None):
        """
        Error shape:
          {"error": {"code": 429, "message": "Rate limit exceeded: limit_rpd/...", "type": "rate_limit_error"}}
          {"error": {"message": "Provider returned error", "code": 429, "metadata": {"raw": "...", "provider_name": "..."}}}
        """
        openrouter_data = judge if judge is not None else self.workers.get("models").get("openrouter")
        if not openrouter_data:
            raise Exception("Openrouter config not found")

        api_key    = openrouter_data.get("Api-key")
        model_name = openrouter_data.get("model_name")
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
                # print(result)

                if "error" in result:
                    return {
                        "model_info": {"model_name": model_name, "provider": "openrouter"},
                        "content": None, "status": "failed",
                        "error": self._parse_error(result, "openrouter")
                    }

                choice  = result.get("choices", [])[0]
                message = choice.get("message", {})
                return {
                    "model_info": {"model_name": result.get("model"), "provider": "openrouter"},
                    "content": message.get("content"),
                    "status": "success"
                }

        except httpx.TimeoutException:
            return {"model_info": {"model_name": model_name, "provider": "openrouter"},
                    "content": None, "status": "failed", "error": "Request timed out"}
        except httpx.RequestError as e:
            return {"model_info": {"model_name": model_name, "provider": "openrouter"},
                    "content": None, "status": "failed", "error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"model_info": {"model_name": model_name, "provider": "openrouter"},
                    "content": None, "status": "failed", "error": str(e)}


    async def gemini(self, prompt=None, judge=None, messages=None):
        """
        Error shape:
          {"error": {"code": 429, "message": "Resource has been exhausted (e.g. check quota).", "status": "RESOURCE_EXHAUSTED"}}
          {"error": {"code": 429, "message": "...", "status": "RESOURCE_EXHAUSTED",
                     "errors": [{"message": "...", "domain": "global", "reason": "rateLimitExceeded"}]}}
        """
        gemini_data = judge if judge is not None else self.workers.get("models").get("gemini")
        if not gemini_data:
            raise Exception("Gemini config not found")

        api_key    = gemini_data.get("Api-key")
        model_name = gemini_data.get("model_name")

        if messages is not None:
            contents = []
            for msg in messages:
                role = "model" if msg["role"] == "assistant" else "user"
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
        else:
            contents = [{"parts": [{"text": prompt}]}]
        print(contents)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}",
                    headers={"Content-Type": "application/json"},
                    json={"contents": contents},
                    timeout=30.0
                )
                result = response.json()
                # print(result)

                if "error" in result:
                    return {
                        "model_info": {"model_name": model_name, "provider": "gemini"},
                        "content": None, "status": "failed",
                        "error": self._parse_error(result, "gemini")
                    }

                candidate = result.get("candidates", [])[0]
                content   = candidate.get("content", {}).get("parts", [])[0].get("text")
                return {
                    "model_info": {"model_name": result.get("modelVersion"), "provider": "gemini"},
                    "content": content,
                    "status": "success"
                }

        except httpx.TimeoutException:
            return {"model_info": {"model_name": model_name, "provider": "gemini"},
                    "content": None, "status": "failed", "error": "Request timed out"}
        except httpx.RequestError as e:
            return {"model_info": {"model_name": model_name, "provider": "gemini"},
                    "content": None, "status": "failed", "error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"model_info": {"model_name": model_name, "provider": "gemini"},
                    "content": None, "status": "failed", "error": str(e)}


    async def groq(self, prompt=None, judge=None, messages=None):
        """
        Error shape:
          {"error": {"message": "Rate limit reached for model `llama3-70b` ... TPM: Limit 7000 ...",
                     "type": "tokens", "code": "rate_limit_exceeded"}}
        """
        groq_data = judge if judge is not None else self.workers.get("models").get("groq")
        if not groq_data:
            raise Exception("Groq config not found")

        api_key    = groq_data.get("Api-key")
        model_name = groq_data.get("model_name")
        payload_messages = messages if messages is not None else [{"role": "user", "content": prompt}]
        print(payload_messages)
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={"model": model_name, "messages": payload_messages},
                    timeout=30.0
                )
                result = response.json()
                # print(result)

                if "error" in result:
                    return {
                        "model_info": {"model_name": model_name, "provider": "groq"},
                        "content": None, "status": "failed",
                        "error": self._parse_error(result, "groq")
                    }

                choice  = result.get("choices", [])[0]
                message = choice.get("message", {})
                return {
                    "model_info": {"model_name": result.get("model"), "provider": "groq"},
                    "content": message.get("content"),
                    "status": "success"
                }

        except httpx.TimeoutException:
            return {"model_info": {"model_name": model_name, "provider": "groq"},
                    "content": None, "status": "failed", "error": "Request timed out"}
        except httpx.RequestError as e:
            return {"model_info": {"model_name": model_name, "provider": "groq"},
                    "content": None, "status": "failed", "error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"model_info": {"model_name": model_name, "provider": "groq"},
                    "content": None, "status": "failed", "error": str(e)}


    async def sambanova(self, prompt=None, judge=None, messages=None):
        """
        Error shape (OpenAI-compatible):
          {"error": {"message": "...", "type": "...", "code": "..."}}
          HTTP 429 with "Too Many Requests" in status text
        """
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

                # SambaNova may return 429 with no JSON body, so check status code first
                if response.status_code == 429:
                    try:
                        result = response.json()
                        error_msg = self._parse_error(result, "sambanova")
                    except Exception:
                        error_msg = "Api limit exceeded"
                    return {
                        "model_info": {"model_name": model_name, "provider": "sambanova"},
                        "content": None, "status": "failed", "error": error_msg
                    }

                result = response.json()
                # print("sambanova", result)

                if "error" in result:
                    return {
                        "model_info": {"model_name": model_name, "provider": "sambanova"},
                        "content": None, "status": "failed",
                        "error": self._parse_error(result, "sambanova")
                    }

                choice  = result.get("choices", [])[0]
                message = choice.get("message", {})
                return {
                    "model_info": {"model_name": result.get("model"), "provider": "sambanova"},
                    "content": message.get("content"),
                    "status": "success"
                }

        except httpx.TimeoutException:
            return {"model_info": {"model_name": model_name, "provider": "sambanova"},
                    "content": None, "status": "failed", "error": "Request timed out"}
        except httpx.RequestError as e:
            return {"model_info": {"model_name": model_name, "provider": "sambanova"},
                    "content": None, "status": "failed", "error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"model_info": {"model_name": model_name, "provider": "sambanova"},
                    "content": None, "status": "failed", "error": str(e)}


    async def cerebras(self, prompt=None, judge=None, messages=None):
        """
        Error shape (OpenAI-compatible):
          {"error": {"message": "...", "type": "...", "code": "..."}}
          429 status code — sometimes with no body at all ("429 status code (no body)")
        """
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

                # Cerebras can return 429 with no body
                if response.status_code == 429:
                    try:
                        result = response.json()
                        error_msg = self._parse_error(result, "cerebras")
                    except Exception:
                        error_msg = "Api limit exceeded"
                    return {
                        "model_info": {"model_name": model_name, "provider": "cerebras"},
                        "content": None, "status": "failed", "error": error_msg
                    }

                result = response.json()
                # print(result)

                if "error" in result:
                    return {
                        "model_info": {"model_name": model_name, "provider": "cerebras"},
                        "content": None, "status": "failed",
                        "error": self._parse_error(result, "cerebras")
                    }

                choice  = result.get("choices", [])[0]
                message = choice.get("message", {})
                return {
                    "model_info": {"model_name": result.get("model"), "provider": "cerebras"},
                    "content": message.get("content"),
                    "status": "success"
                }

        except httpx.TimeoutException:
            return {"model_info": {"model_name": model_name, "provider": "cerebras"},
                    "content": None, "status": "failed", "error": "Request timed out"}
        except httpx.RequestError as e:
            return {"model_info": {"model_name": model_name, "provider": "cerebras"},
                    "content": None, "status": "failed", "error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"model_info": {"model_name": model_name, "provider": "cerebras"},
                    "content": None, "status": "failed", "error": str(e)}


    async def mistral(self, prompt=None, judge=None, messages=None):
        """
        Error shape A (nested):
          {"object": "error", "message": "Rate limit exceeded", "type": "rate_limited",
           "param": null, "code": "1300"}

        Error shape B (flat — no "error" wrapper):
          {"message": "Requests rate limit exceeded"}

        Mistral docs: all errors return {"object": "error", "message": "...", "type": "...", "param": "...", "code": "..."}
        """
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
                result = response.json()
                # print(result)

                # Mistral wraps errors as {"object": "error", ...} — no "error" key
                # Also check for flat {"message": "..."} shape
                is_mistral_error = (
                    result.get("object") == "error"
                    or ("message" in result and "choices" not in result)
                )
                if is_mistral_error:
                    return {
                        "model_info": {"model_name": model_name, "provider": "mistral"},
                        "content": None, "status": "failed",
                        "error": self._parse_error(result, "mistral")
                    }

                # Standard nested error just in case
                if "error" in result:
                    return {
                        "model_info": {"model_name": model_name, "provider": "mistral"},
                        "content": None, "status": "failed",
                        "error": self._parse_error(result, "mistral")
                    }

                choice  = result.get("choices", [])[0]
                message = choice.get("message", {})
                return {
                    "model_info": {"model_name": result.get("model"), "provider": "mistral"},
                    "content": message.get("content"),
                    "status": "success"
                }

        except httpx.TimeoutException:
            return {"model_info": {"model_name": model_name, "provider": "mistral"},
                    "content": None, "status": "failed", "error": "Request timed out"}
        except httpx.RequestError as e:
            return {"model_info": {"model_name": model_name, "provider": "mistral"},
                    "content": None, "status": "failed", "error": f"Network error: {str(e)}"}
        except Exception as e:
            return {"model_info": {"model_name": model_name, "provider": "mistral"},
                    "content": None, "status": "failed", "error": str(e)}