from enum import Enum

class fusion_routes(Enum):
    register = "register"
    login = "login"
    chat_dashboard = "chats"


class fusion_pages(Enum):
    landing = "index.html"
    chat = "chat.html"
    login = "login.html"
    register = "register.html"




class fusion_response:
    @staticmethod
    def failure(code, message, data = {}):
        return {
            "code" : code,
            "status" : "error",
            "message" : message,
            "data" : data 
        }
    
    @staticmethod
    def success(code, message, data = {}):
        return {
            "code": code,
            "status" : "error",
            "message" : message,
            "data" : data 
        }

    