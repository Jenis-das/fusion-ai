
class fusion_routes():
    register = "register"
    login = "login"
    logout = "logout"
    chats_dashboard = "chats_dashboard"




class fusion_pages():
    landing = "index.html"
    chats_dashboard = "chats_dashboard.html"
    login = "login.html"
    register = "register.html"

    def __str__(self):
        return self.value


class failure(Exception):
    def __init__(self, message, code = 0, data = None, status = "error"):
        self.message = message
        super().__init__(self.message)
        self.err = {
            'status': status, 
            'code' : code,
            'message' : message,
            'data' : data if data is not None else {},
        }




class fusion_response:
    @staticmethod
    def success(code, message, data = {}):
        return {
            "code": code,
            "status" : "success",
            "message" : message,
            "data" : data 
        }

    