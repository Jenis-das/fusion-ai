from django.shortcuts import render, redirect
from django.http import HttpResponse
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .config import fusion_pages, failure
from .config import fusion_response, fusion_routes
from rest_framework import response
from .model_providers import PROVIDERS
from .models import Provider, LLMModel, Chat, Message
from .engine import llms
from django import template
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


access_token = "access_token"
refresh_token = "refresh_token"

# For All routing and Template pages see config
def initialView(request):
    return render(request=request, template_name=fusion_pages.landing , context={})


class Authentications:
    def token_generator(self, user):
        new_token = RefreshToken.for_user(user=user)
        return {
            "refresh_token" : str(new_token),
            "access_token" : str(new_token.access_token)
        }
        

    def token_checker(self, request):
        try:
            token = request.COOKIES.get(access_token)
            if not token:
                raise failure(message="token not found in cookie")
            user_id = AccessToken(token).get("user_id")
            return User.objects.filter(id=user_id).first()
        except failure as f:
            print(f.err)
            return None
        except Exception as e:
            print(e)
            return None

    
    def login(self, request):
        if request.method == "POST":
            try:
                email    = request.POST.get('email', '').strip().lower()
                password = request.POST.get('password', '')

                if not email or not password or len(password) < 5:
                    raise failure(code=422, message="Valid email and password (min 5 chars) are required.")

                # Look up user by email (email is stored on the User model and must be unique)
                user_obj = User.objects.filter(email=email).first()
                if user_obj is None:
                    raise failure(code=404, message="No account found with that email.")

                # Authenticate using the username Django stores internally
                user = authenticate(request, username=user_obj.username, password=password)
                if user is None:
                    raise failure(code=401, message="Incorrect password.")

                new_token = self.token_generator(user)
                resp = redirect(fusion_routes.chats_dashboard)
                resp.set_cookie("refresh_token", new_token.get(refresh_token))
                resp.set_cookie("access_token",  new_token.get(access_token))
                return resp

            except failure as f:
                print(f.err)
                return render(request, fusion_pages.login, {"error": f.err.get("message", "Login failed.")})
            except Exception as e:
                print(e)
                return render(request, fusion_pages.login, {"error": "Something went wrong. Please try again."})

        return render(request=request, template_name=fusion_pages.login)


    def register(self, request):
        if request.method == "POST":
            try:
                email    = request.POST.get('email', '').strip().lower()
                password = request.POST.get('password', '')

                if not email or not password:
                    raise failure(code=422, message="Email and password are required.")

                if len(password) < 5:
                    raise failure(code=422, message="Password must be at least 5 characters.")

                # Basic email format guard
                if '@' not in email or '.' not in email.split('@')[-1]:
                    raise failure(code=422, message="Please enter a valid email address.")

                if User.objects.filter(email=email).exists():
                    raise failure(code=422, message="An account with this email already exists.")

                # Use the local part of the email as the username (Django still needs one).
                # Append a numeric suffix if there's a collision.
                base_username = email.split('@')[0][:30]   # max_length=150 but keep it short
                username      = base_username
                suffix        = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{suffix}"
                    suffix  += 1

                User.objects.create_user(username=username, email=email, password=password)
                return redirect(fusion_routes.login)

            except failure as f:
                print(f.err)
                return render(request, fusion_pages.register, {"error": f.err.get("message", "Registration failed.")})
            except Exception as e:
                print(e)
                return render(request, fusion_pages.register, {"error": "Something went wrong. Please try again."})

        return render(request=request, template_name=fusion_pages.register)


    def logout(self, request):
        response = redirect(fusion_routes.login)
        response.delete_cookie(access_token)
        response.delete_cookie(refresh_token)
        return response



class fusion(Authentications):
    def chat_dashboard(self, request):
        user = self.token_checker(request)
        if user is None:
            return redirect(fusion_routes.login)
        return render(request, fusion_pages.chats_dashboard)


    def apikeys(self, request):
        user = self.token_checker(request)
        if user is None:
            return redirect(fusion_routes.login)
        
        if request.method == "POST":
            try:
                for key, provider in PROVIDERS.items():
                    api_key = request.POST.get(f"{key}_apikey")
                    
                    if api_key:
                        Provider.objects.update_or_create(
                            user=user,
                            name=key,
                            defaults={
                                "api_key": api_key,
                            }
                        )
                return HttpResponse("saved")
            except Exception as e:
                return HttpResponse(f"save failed: {e}")
        
        return redirect(fusion_routes.setting)


    def settings(self, request):
        user = self.token_checker(request)
        if user is None:
            return redirect(fusion_routes.login)

        if request.method == "POST":
            try:
                for key, provider in PROVIDERS.items():
                    selected_model = request.POST.get(f"{key}_model")
                    custom_model = request.POST.get(f"{key}_custom_model")

                    provider_obj = Provider.objects.filter(user=user, name=key).first()
                    if provider_obj is None:
                        continue

                    LLMModel.objects.filter(provider=provider_obj).delete()

                    if selected_model:
                        model_name = next(
                            (m["name"] for m in provider["models"] if m["model_id"] == selected_model),
                            selected_model
                        )
                        LLMModel.objects.create(
                            provider=provider_obj,
                            model_id=selected_model,
                            name=model_name,
                            is_custom=False
                        )
                    elif custom_model:
                        LLMModel.objects.create(
                            provider=provider_obj,
                            model_id=custom_model,
                            name=custom_model,
                            is_custom=True
                        )

                return HttpResponse("models saved")
            except Exception as e:
                return HttpResponse(f"save failed: {e}")

        saved_models = {}
        for key in PROVIDERS:
            provider_obj = Provider.objects.filter(user=user, name=key).first()
            if provider_obj:
                model = LLMModel.objects.filter(provider=provider_obj).first()
                saved_models[key] = model.model_id if model else None
            else:
                saved_models[key] = None

        saved_keys = {}
        for key in PROVIDERS:
            provider_obj = Provider.objects.filter(user=user, name=key).first()
            saved_keys[key] = provider_obj.api_key if provider_obj else None

        return render(request, fusion_pages.setting, {
            "data": PROVIDERS,
            "saved_models": saved_models,
            "saved_keys": saved_keys,
        })


    def history(self, request):
        user = self.token_checker(request)
        if user is None:
            return JsonResponse({"error": "unauthorized"}, status=401)
        
        chats = Chat.objects.filter(user=user).order_by('-created_at')
        data = [
            {
                "id": chat.id,
                "name": chat.name,
                "created_at": chat.created_at.strftime("%d %b, %I:%M %p")
            }
            for chat in chats
        ]
        return JsonResponse({"chats": data})


    def delete_chat(self, request, id):
        user = self.token_checker(request)
        if user is None:
            return redirect(fusion_routes.login)
        if request.method == "GET":
            try:
                chat = Chat.objects.filter(user=user, id=id).first()
                chat.delete()
                return JsonResponse({"status": "deleted"})
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=400)
        return redirect(fusion_routes.chats_dashboard)


    def new_chat(self, request):
        user = self.token_checker(request)
        if user is None:
            return JsonResponse({"error": "unauthorized"}, status=401)
        
        if request.method == "POST":
            chat = Chat.objects.create(
                user=user,
                name="New Chat"
            )
            return JsonResponse({"id": chat.id, "name": chat.name})
        return JsonResponse({"error": "invalid"}, status=400)


    def current_chat(self, request, id):
        """
        GET  → returns all messages for a chat (for reloading history)
        """
        user = self.token_checker(request)
        if user is None:
            return JsonResponse({"error": "unauthorized"}, status=401)
 
        chat = Chat.objects.filter(user=user, id=id).first()
        if chat is None:
            return JsonResponse({"error": "chat not found"}, status=404)
 
        messages = Message.objects.filter(chat=chat).order_by('time_stamp')
        data = []
        for msg in messages:
            entry = {
                "role":      msg.role,
                "content":   msg.content,
                "is_judge":  msg.is_judge_selected,
                "timestamp": msg.time_stamp.strftime("%I:%M %p"),
            }
            if msg.llm_model:
                entry["model"]    = msg.llm_model.name
                entry["provider"] = msg.llm_model.provider.name
            else:
                entry["model"]    = None
                entry["provider"] = None
            data.append(entry)
 
        return JsonResponse({"messages": data, "chat_name": chat.name})


    def send_message(self, request, id):
        user = self.token_checker(request)
        if user is None:
            return JsonResponse({"error": "unauthorized"}, status=401)

        if request.method != "POST":
            return JsonResponse({"error": "POST required"}, status=405)

        chat = Chat.objects.filter(user=user, id=id).first()
        if chat is None:
            return JsonResponse({"error": "chat not found"}, status=404)

        try:
            body = json.loads(request.body)
        except Exception:
            return JsonResponse({"error": "invalid JSON"}, status=400)

        prompt = body.get("prompt", "").strip()
        if not prompt:
            return JsonResponse({"error": "prompt is required"}, status=400)

        past_messages = Message.objects.filter(chat=chat).order_by('time_stamp')
        
        history = []
        for msg in past_messages:
            if msg.role == "user":
                history.append({"role": "user", "content": msg.content})
            elif msg.role == "assistant" and msg.is_judge_selected:
                history.append({"role": "assistant", "content": msg.content})
        
        providers_qs = Provider.objects.filter(user=user).prefetch_related('models')
        
        worker_models = {}
        judge_candidate = None
        
        for prov in providers_qs:
            model_obj = prov.models.filter(is_active=True).first()
            if model_obj is None:
                continue
            entry = {
                "Api-key": prov.api_key,
                "model_name": model_obj.model_id,
            }
            worker_models[prov.name] = entry
            if judge_candidate is None:
                judge_candidate = prov.name
        
        requested_judge = body.get("judge_provider", None)
        if requested_judge and requested_judge in worker_models:
            judge_provider_name = requested_judge
        else:
            for preferred in ["groq", "gemini", "mistral", "cerebras", "sambanova", "openrouter"]:
                if preferred in worker_models:
                    judge_provider_name = preferred
                    break
            else:
                judge_provider_name = judge_candidate
        
        if not judge_provider_name or not worker_models:
            return JsonResponse(
                {"error": "No providers configured. Please add API keys in Settings."},
                status=400
            )
        
        judge_config = {
            "provider": judge_provider_name,
            **worker_models[judge_provider_name],
            "prompt": (
                # "You are a judge AI. Multiple AI assistants have answered the same question. "
                # "Carefully evaluate each response for accuracy, completeness, and clarity. "
                # "Then provide the single best, synthesized answer. "
                # "Start with '## Best Answer' followed by your verdic"
                # "section explaining which responses were strongest and why.",

                "You are a judge AI. Multiple AI assistants have answered the same question. "
                "Your task is to synthesize the best possible answer from all responses. "
                "Do NOT provide any evaluation, reasoning, or explanation. "
                "Only output the synthesized answer, starting with '## Best Answer' followed by the answer itself."
            )
        }
        
        engine_data = {
            "judge": judge_config,
            "history": history,
            "workers": {
                "prompt": prompt,
                "models": worker_models,
            }
        }

        try:
            result = llms(engine_data)
        except Exception as e:
            return JsonResponse({"error": f"Engine error: {str(e)}"}, status=500)

        Message.objects.create(
            chat=chat,
            role="user",
            content=prompt,
        )

        if chat.name == "New Chat":
            chat.name = prompt[:60] + ("…" if len(prompt) > 60 else "")
            chat.save()

        worker_responses = []
        for worker_data in (result.all_ai_result or []):
            model_info = worker_data.get("model_info", {})
            provider_name = model_info.get("provider", "unknown")
            model_name = model_info.get("model_name", "unknown")
            content = worker_data.get("content") or ""
            status = worker_data.get("status", "failed")
            error = worker_data.get("error", "")

            prov_obj = Provider.objects.filter(user=user, name=provider_name).first()
            model_obj = None
            if prov_obj:
                model_obj = prov_obj.models.filter(is_active=True).first()

            if content:
                Message.objects.create(
                    chat=chat,
                    role="assistant",
                    content=content,
                    llm_model=model_obj,
                    is_judge_selected=False,
                )

            worker_responses.append({
                "provider": provider_name,
                "model_name": model_name,
                "content": content,
                "status": status,
                "error": error,
            })

        judge_result = result.judge_result or {}
        judge_content = ""
        if isinstance(judge_result.get("result"), dict):
            judge_content = judge_result["result"].get("content") or ""
        elif isinstance(judge_result.get("result"), str):
            judge_content = judge_result["result"]

        judge_prov_obj = Provider.objects.filter(user=user, name=judge_provider_name).first()
        judge_model_obj = None
        if judge_prov_obj:
            judge_model_obj = judge_prov_obj.models.filter(is_active=True).first()

        if judge_content:
            Message.objects.create(
                chat=chat,
                role="assistant",
                content=judge_content,
                llm_model=judge_model_obj,
                is_judge_selected=True,
            )

        return JsonResponse({
            "chat_name": chat.name,
            "user_prompt": prompt,
            "workers": worker_responses,
            "judge": {
                "provider": judge_provider_name,
                "content": judge_content,
            }
        })