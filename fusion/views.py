from django.shortcuts import render, redirect
from django.http import HttpResponse
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .config import fusion_pages
from .config import fusion_response

# For All routing and Template pages see config


def initialView(request):
    return render(request=request, template_name=fusion_pages.landing_page , context={})




class Authentications:
    def token_generator(self, user):
        new_token = RefreshToken.for_user(user=user)
        return {
            "refresh_token" : str(new_token),
            "access_token" : str(new_token.access_token)
        }
        

    def token_checker(self, request):
        try:
            token = request.COOKIES.get("refresh_token")
            if token is None:
                raise Exception("token Not found in the cookie")
            user_id = AccessToken(token).get("user_id")
            return User.objects.filter(username = user_id).first()
        except Exception as e:
            return None

    
    def login(self, request):
        if request.method == "POST":
            username = request.POST.get('username')
            password = request.POST.get('password')
            if username is None or password is None:
                return render(request, fusion_pages.login, fusion_response.failure(code=422, message="please fill the details"))
            user = authenticate(request, username = username, password = password)
            if user is None:
                return render(request, fusion_pages.login, fusion_response.failure(code=404, message="user not available"))
            new_token = self.token_generator(user)
            response = redirect(fusion_pages.chat)
            response.set_cookie("refresh_token", new_token.get("refresh_token"))
            response.set_cookie("access_token", new_token.get("access_token"))
            return response
        return render(request=request, template_name=fusion_pages.login, context={})

    def register(self, request):
        if request.method == "POST":
            username = request.POST.get('username')
            password = request.POST.get('password')
            if username is None or password is None:
                return render(request, fusion_pages.register_page,fusion_response.failure(code=422, message="please fill the details"))
            if User.objects.filter(username = username).first():
                return render(request, fusion_pages.register_page, fusion_response.failure(code=409, message="user already exists"))
            User.objects.create_user(email = username, password=password)
            return redirect(fusion_pages.login_page)
        return render(request=request, template_name=fusion_pages.register_page)
    


    def chats_dashboard(self, request):
        user = self.token_checker(request)
        if user is None:
            return redirect(fusion_pages.login)
        return render(request, fusion_pages.chat, context={})


    def logout(self, request):
        response = redirect(fusion_pages.login)
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return response

    
