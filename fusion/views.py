from django.shortcuts import render, redirect
from django.http import HttpResponse
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .config import fusion_pages, failure
from .config import fusion_response, fusion_routes
from rest_framework import response


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
    def chats(self, request):
        return HttpResponse("chats")

    def current_chat(self, request, id):
        return HttpResponse("current chats")

    def chat_dashboard(self, request):
        user = self.token_checker(request)
        print(user)
        if user is None:
            return redirect(fusion_routes.login)
        return render(request, fusion_pages.chats_dashboard)
    
    def chatHistory(self, request):
        return HttpResponse("This is the response")

