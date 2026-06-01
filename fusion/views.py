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
from django import template
import json
from django.http import JsonResponse









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
                username = request.POST.get('username')
                password = request.POST.get('password')
                if not username or not password or len(username) < 5 or len(password) < 5:
                    raise failure(code=422, message="username and password length should be greater than 5")
                user = authenticate(request, username = username, password = password)
                if user is None:
                    raise failure(code=404, message="user not found")
                new_token = self.token_generator(user)
                response = redirect(fusion_routes.chats_dashboard)
                response.set_cookie("refresh_token", new_token.get(refresh_token))
                response.set_cookie("access_token", new_token.get(access_token))
                return response
            except failure as f:
                print(f.err)
                return render(request, fusion_pages.login, f.err)
            except Exception as e:
                return render(request=request, template_name=fusion_pages.login)
        return render(request=request, template_name=fusion_pages.login)


    def register(self, request):
        if request.method == "POST":
            try:
                username = request.POST.get('username')
                password = request.POST.get('password')
                print(type(username), password)
                if not username or not password or len(username) < 5 or len(password) < 5:
                    raise failure(code=422, message="username and password length should be greater than 5")
                if User.objects.filter(username = username).first():
                    raise failure(code=422 ,message="User already exists")
                User.objects.create_user(username = username, password=password)
                return redirect(fusion_routes.login)
            except failure as f:
                print(f.err)
                return render(request, fusion_pages.register, f.err)
            except Exception as e:
                print(e)
                return render(request=request, template_name=fusion_pages.register)
        return render(request=request, template_name=fusion_pages.register)



    def logout(self, request):
        response = redirect(fusion_routes.login)
        response.delete_cookie(access_token)
        response.delete_cookie(refresh_token)
        return response



class fusion(Authentications):
    def chat_dashboard(self, request):
        user = self.token_checker(request)
        print(user)
        if user is None:
            return redirect(fusion_routes.login)
        return render(request, fusion_pages.chats_dashboard)
    
    def chatHistory(self, request):
        return HttpResponse("This is the response")


    

    def apikeys(self, request):
        user = self.token_checker(request)
        if user is None:
            return redirect(fusion_routes.login)
        
        if request.method == "POST":
            try:
                for key, provider in PROVIDERS.items():
                    api_key = request.POST.get(f"{key}_apikey")
                    
                    if api_key:  # only save if user actually pasted something
                        Provider.objects.update_or_create(
                            user=user,
                            name=key,  # "gemini", "groq" etc
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
                 redirect(fusion_routes.login)

        if request.method == "POST":
            try:
                for key, provider in PROVIDERS.items():
                    selected_model = request.POST.get(f"{key}_model")  # single value now (radio)
                    custom_model = request.POST.get(f"{key}_custom_model")

                    provider_obj = Provider.objects.filter(user=user, name=key).first()
                    if provider_obj is None:
                        continue

                    # Clear previous selection for this provider before saving new one
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

        # GET — load saved selections per provider to pre-fill the form
        saved_models = {}
        for key in PROVIDERS:
            provider_obj = Provider.objects.filter(user=user, name=key).first()
            if provider_obj:
                model = LLMModel.objects.filter(provider=provider_obj).first()
                saved_models[key] = model.model_id if model else None
            else:
                saved_models[key] = None

        # fetch saved api keys too
        saved_keys = {}
        for key in PROVIDERS:
            provider_obj = Provider.objects.filter(user=user, name=key).first()
            saved_keys[key] = provider_obj.api_key if provider_obj else None

        return render(request, fusion_pages.setting, {
            "data": PROVIDERS,
            "saved_models": saved_models,
            "saved_keys": saved_keys,  # ← pass this
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
                chat = Chat.objects.filter(user = user, id = id).first()
                chat.delete()
                print("chat deleted")
                return HttpResponse("chat deleted")
            except Exception as e:
                print(e)
                # return HttpResponse("")
        return redirect(fusion_routes.chats_dashboard)
    



    def new_chat(self, request):
        user = self.token_checker(request)
        if user is None:
            return JsonResponse({"error": "unauthorized"}, status=401)
        
        if request.method == "POST":
            chat = Chat.objects.create(
                user=user,
                name="New Chat"  # will be renamed after first message
            )
            return JsonResponse({"id": chat.id, "name": chat.name})
        return JsonResponse({"error": "invalid"}, status=400)
    


    def current_chat(self, request, id):
        user = self.token_checker(request)
        if user is None:
            return redirect(fusion_routes.login)
        test_chat = "this is test chat"
        
        
        return JsonResponse({
            "llms" : {
                "flash" : test_chat,
                "gpt4o" : test_chat,
                "claude" : test_chat
            },
            "judge" : {
                "claude" : test_chat
            }
        })