from datetime import datetime, timedelta
from email.utils import formatdate
import os
import json
import logging
import re
from sqlmodel import select
from urllib.parse import unquote, urlparse
from sqlalchemy.exc import SQLAlchemyError

from collections.abc import Callable
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler
from typing import Self
from typing_extensions import Self 

from pydantic import ValidationError
from sqlmodel import Session

from back.config import (
    engine, TEMPLATE_ENVIRONMENT, STATIC_URL, DEFAULT_URL,
    APPLICATION_JSON, APPLICATION_URLENCODED,
)
from back.models import Admin, AdminToken, User, RegistrationForm
from back.custom_types import Request, Response
from back.utils import BadUserError, UserIsNotAuthenticated, check_admin_token, check_token, clear_cookie, generate_admin_token, generate_login, generate_password, generate_token
from back.validators import RegistrationFormModel

FRONTEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "front"))

class HTTPHandler(BaseHTTPRequestHandler):
    paths = {"GET": {}, "POST": {}, "PUT": {}, "DELETE": {}}
    dynamic_paths = {"GET": {}, "POST": {}, "PUT": {}, "DELETE": {}} 

    def parse_request(self) -> bool:
        result = super().parse_request()
        parse = urlparse(self.path)
        self.original_path = parse.path  # Сохраняем оригинальный путь
        self.path = parse.path
        self.query = parse.query
        self.path_params = {}  # параметры из пути
        return result

    def __init__(self, *args, **kwargs):
        with Session(engine) as self.session:
            super().__init__(*args, **kwargs)

    def req(self) -> Request:
        headers = dict(self.headers)
        cookie = SimpleCookie(headers.get("Cookie", ""))
        length = int(headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        method = self.command
        return Request(
            headers=headers,
            cookie=cookie,
            method=method,
            path=self.path,
            query=self.query,
            body=body,
            params=self.path_params  # параметры пути
        )

    def resp(self, response: Response):
        self.send_response(response.status)
        for name, value in response.headers.items():
            self.send_header(name, value)
        for name in response.cookie:
            response.cookie[name]["path"] = DEFAULT_URL
            self.send_header("Set-Cookie", response.cookie[name].OutputString())
        self.end_headers()
        if response.content:
            if isinstance(response.content, bytes):
                self.wfile.write(response.content)
            else:
                self.wfile.write(response.content.encode())

    def find_dynamic_handler(self, method):
        #Находит обработчик для динамического пути
        for pattern, handler in self.dynamic_paths[method].items():
            path_parts = self.path.split('/')
            pattern_parts = pattern.split('/')
            
            if len(path_parts) != len(pattern_parts):
                continue
                
            match = True
            params = {}
            
            for i, (path_part, pattern_part) in enumerate(zip(path_parts, pattern_parts)):
                if pattern_part.startswith('{') and pattern_part.endswith('}'):
                    # Это параметр
                    param_name = pattern_part[1:-1]
                    params[param_name] = path_part
                elif path_part != pattern_part:
                    match = False
                    break
                    
            if match:
                self.path_params = params
                return handler
                
        return None

    def do_GET(self):
        if self.path.startswith("/front/"):
            self.serve_static()
            return
        try:
            # Сначала проверяем статические маршруты
            if self.path in self.paths["GET"]:
                self.paths["GET"][self.path](self)
            else:
                # Затем проверяем динамические маршруты
                handler = self.find_dynamic_handler("GET")
                if handler:
                    handler(self)
                else:
                    self.send_error(404, explain=f"Page {self.path} not found")
        except Exception as e:
            logging.error(str(e))
            self.send_error(500)

    def do_POST(self):
        if self.path.startswith("/front/"):
            self.send_error(404)
            return
        try:
            if self.path in self.paths["POST"]:
                self.paths["POST"][self.path](self)
            else:
                handler = self.find_dynamic_handler("POST")
                if handler:
                    handler(self)
                else:
                    self.send_error(404, explain="Invalid URL")
        except Exception as e:
            logging.error(str(e))
            self.send_error(500)

    def do_PUT(self):
        if self.path.startswith("/front/"):
            self.send_error(404)
            return
        try:
            if self.path in self.paths["PUT"]:
                self.paths["PUT"][self.path](self)
            else:
                handler = self.find_dynamic_handler("PUT")
                if handler:
                    handler(self)
                else:
                    self.send_error(404, explain="Invalid URL")
        except Exception as e:
            logging.error(str(e))
            self.send_error(500)


    def do_DELETE(self):
        if self.path.startswith("/front/"):
            self.send_error(404)
            return
        try:
            if self.path in self.paths["DELETE"]:
                self.paths["DELETE"][self.path](self)
            else:
                handler = self.find_dynamic_handler("DELETE")
                if handler:
                    handler(self)
                else:
                    self.send_error(404, explain="Invalid URL")
        except Exception as e:
            logging.error(str(e))
            self.send_error(500)

    def serve_static(self):
        relative_path = unquote(self.path.lstrip('/'))
        parts = relative_path.split('/')
        if parts[0] == "front":
            parts = parts[1:]
        full_path = os.path.join(FRONTEND_ROOT, *parts)
        if not os.path.isfile(full_path):
            self.send_error(404, "File not found")
            return
        import mimetypes
        mimetype, _ = mimetypes.guess_type(full_path)
        mimetype = mimetype or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", mimetype)
        self.end_headers()
        with open(full_path, 'rb') as f:
            self.wfile.write(f.read())

    @classmethod
    def route(cls, methods: list[str], path: str, redirect: str = DEFAULT_URL) -> Callable:
        def decorator(function: Callable) -> Callable:
            def inner(self: Self):
                from back.kwargs import get_kwargs, validation_error_response
                try:
                    kwargs = get_kwargs(function, self)
                    response = function(**kwargs)
                except ValidationError as e:
                    response = validation_error_response(self, redirect, e)
                except Exception as e:
                    logging.exception('Internal server error')
                    content_type = self.headers.get("Content-Type", "")
                    if APPLICATION_JSON in content_type:
                        response = Response(
                            status=400,
                            cookie=SimpleCookie(),
                            headers={"Content-Type": "application/json"},
                            content=json.dumps({"form": str(e)}),
                        )
                    else:
                        response = Response(
                            status=500,
                            cookie=SimpleCookie(),
                            headers={"Content-Type": "text/plain"},
                            content="Internal Server Error",
                        )
                self.resp(response)
                return
                
            for method in methods:
                if '{' in path and '}' in path:
                    # Динамический путь
                    cls.dynamic_paths[method][path] = inner
                else:
                    # Статический путь
                    cls.paths[method][path] = inner
            return inner
        return decorator
    

@HTTPHandler.route(["GET"], "/admin/login/")
def admin_redirect(request: Request) -> Response:
    return Response(302, {"Location": "/admin/login"}, SimpleCookie(), "")

@HTTPHandler.route(["GET"], "/")
def main_page(request: Request) -> Response:
    cookie = request.cookie
    form_data = {}
    errors = {}
    success = cookie.get("success", "").value if "success" in cookie else "0"
    login = cookie.get("login", "").value if "login" in cookie else ""
    password = cookie.get("password", "").value if "password" in cookie else ""

    # Очищаем куки только после их использования
    if success == "1" and login and password:
        cleared_cookies = SimpleCookie()
        cleared_cookies["success"] = "0"
        cleared_cookies["login"] = ""
        cleared_cookies["password"] = ""
        for key in cleared_cookies:
            cleared_cookies[key]["expires"] = 0
    else:
        cleared_cookies = cookie

    for field in ["child_name", "child_birthdate", "parent_name", "phone", "email", "comment", "consent"]:
        if field in cookie:
            form_data[field] = cookie[field].value if isinstance(cookie[field], SimpleCookie) else ""
        if field + "_err" in cookie:
            errors[field] = cookie[field + "_err"].value if isinstance(cookie[field + "__err"], SimpleCookie) else ""

    content = TEMPLATE_ENVIRONMENT.get_template("index.html").render(
        form_data=form_data,
        errors=errors,
        success=success,
        login=login,
        password=password,
        STATIC_URL=STATIC_URL,
        DEFAULT_URL=DEFAULT_URL
    )
    return Response(200, {"Content-Type": "text/html"}, cleared_cookies, content)

@HTTPHandler.route(["GET"], "/login")
def login_page(request: Request) -> Response:
    errors = {}
    form_data = {}
    success_message = ""
    
    # Разбираем строку запроса в словарь
    from urllib.parse import parse_qs
    query_params = parse_qs(request.query) if request.query else {}
    
    # Проверяем запрос на наличие параметра deleted
    if "deleted" in query_params and query_params["deleted"][0] == "1":
        success_message = "Ваш аккаунт был успешно удален."
    
    # Проверяем куки на наличие флага delete_success
    if "delete_success" in request.cookie and request.cookie["delete_success"].value == "1":
        success_message = "Ваш аккаунт был успешно удален."
        # Очищаем куки
        cookie = SimpleCookie()
        cookie["delete_success"] = ""
        cookie["delete_success"]["expires"] = 0
        cookie["delete_success"]["path"] = "/"
    
    content = TEMPLATE_ENVIRONMENT.get_template("login.html").render(
        errors=errors,
        form_data=form_data,
        success_message=success_message,
        STATIC_URL=STATIC_URL,
        DEFAULT_URL=DEFAULT_URL
    )
    
    if "delete_success" in request.cookie and request.cookie["delete_success"].value == "1":
        return Response(200, {"Content-Type": "text/html"}, cookie, content)
    else:
        return Response(200, {"Content-Type": "text/html"}, SimpleCookie(), content)

@HTTPHandler.route(["POST"], "/")
def handle_form_submission(request: Request, session: Session) -> Response:
    cookie = request.cookie.copy()
    if not isinstance(cookie, SimpleCookie):
        temp = SimpleCookie()
        temp.load(cookie)
        cookie = temp

    errors = {}
    form_data = {}
    content_type = request.headers.get("Content-Type", "")

    try:
        if APPLICATION_JSON in content_type:
            data = json.loads(request.body.decode())
        elif APPLICATION_URLENCODED in content_type:
            from urllib.parse import parse_qs
            data_raw = request.body.decode()
            data = {k: v[0] for k, v in parse_qs(data_raw).items()}
        else:
            data = {}

        form_data = data.copy()
        reg_form = RegistrationFormModel(**data)

        login = generate_login()
        password_plain = generate_password()
        user = User.create(session, login, password_plain)

        RegistrationForm.create(session, reg_form, user)

        # Сохраняем логин и пароль в куки
        cookie["login"] = login
        cookie["login"]["expires"] = formatdate((datetime.now() + timedelta(days=1)).timestamp(), usegmt=True)
        cookie["password"] = password_plain
        cookie["password"]["expires"] = formatdate((datetime.now() + timedelta(days=1)).timestamp(), usegmt=True)
        cookie["success"] = "1"

        logging.info(f"Куки установлены: login={login}, password={password_plain}")

        if APPLICATION_JSON in content_type:
            response_data = {
                "login": login,
                "password": password_plain,
                "message": "Регистрация прошла успешно",
            }
            return Response(
                200,
                {"Content-Type": APPLICATION_JSON},
                cookie,
                json.dumps(response_data)
            )
        else:
            # Для обычных форм используем 303 See Other, что предотвратит повторную отправку
            return Response(
                303, 
                {"Location": "/#registration-form"},
                cookie,
                ""
            )

    except ValidationError as e:
        # Обработка ошибок валидации
        errors = {}
        for err in e.errors():
            # Получаем имя поля и сообщение об ошибке
            field_name = err["loc"][0]
            error_message = err["msg"]
            
            # Заменяем стандартные сообщения Pydantic
            if "field required" in error_message.lower():
                error_message = "Заполните это поле"
            elif error_message.startswith("Value error, "):
                error_message = error_message[13:]
                
            errors[field_name] = error_message

        if APPLICATION_JSON in content_type:
            return Response(
                400,
                {"Content-Type": "application/json"},
                SimpleCookie(),
                json.dumps({"errors": errors})
            )
        else:
            content = TEMPLATE_ENVIRONMENT.get_template("index.html").render(
                form_data=form_data, errors=errors, STATIC_URL=STATIC_URL, DEFAULT_URL=DEFAULT_URL
            )
            return Response(400, {"Content-Type": "text/html"}, cookie, content)

    except Exception as e:
        logging.exception("CRITICAL ERROR on form submit!")
        if APPLICATION_JSON in content_type:
            return Response(
                400,
                {"Content-Type": APPLICATION_JSON},
                cookie,
                json.dumps({"form": str(e)})
            )
        else:
            content = TEMPLATE_ENVIRONMENT.get_template("index.html").render(
                form_data=form_data, errors={"form": str(e)}, STATIC_URL=STATIC_URL, DEFAULT_URL=DEFAULT_URL
            )
            return Response(400, {"Content-Type": "text/html"}, cookie, content)
        

@HTTPHandler.route(["POST"], "/login")
def login_user(request: Request, session: Session) -> Response:
    content_type = request.headers.get("Content-Type", "")
    data = {}

    if APPLICATION_JSON in content_type:
        data = json.loads(request.body.decode())
    elif APPLICATION_URLENCODED in content_type:
        from urllib.parse import parse_qs
        data_raw = request.body.decode()
        data = {k: v[0] for k, v in parse_qs(data_raw).items()}
    else:
        data = {}

    login = (data.get("login") or "").strip()
    password = data.get("password") or ""

    form_data = {"login": login}
    errors = {}

    user = session.exec(select(User).where(User.login == login)).first()
    if not user or not user.check_password(password):
        errors["form"] = "Неверный логин или пароль"

        if APPLICATION_JSON in content_type:
            return Response(
                401, {"Content-Type": APPLICATION_JSON}, SimpleCookie(),
                json.dumps(errors)
            )
        else:
            content = TEMPLATE_ENVIRONMENT.get_template("login.html").render(
                errors=errors,
                form_data=form_data,
                STATIC_URL=STATIC_URL,
                DEFAULT_URL=DEFAULT_URL
            )
            return Response(
                401, {"Content-Type": "text/html"}, SimpleCookie(), content
            )

    token = generate_token(user.id, session)
    cookie = SimpleCookie()
    cookie["auth_token"] = token
    cookie["auth_token"]["path"] = "/"

    if APPLICATION_JSON in content_type:
        return Response(
            200,
            {"Content-Type": APPLICATION_JSON},
            cookie,
            json.dumps({
                "success": True, 
                "redirect": f"/users/{user.id}/edit", 
                "user_id": user.id
            })
        )
    else:
        return Response(
            303,
            {"Location": f"/users/{user.id}/edit"},
            cookie,
            ""
        )
        
@HTTPHandler.route(["GET"], "/users/{id}/edit")
def edit_form_page(request: Request, session: Session) -> Response:
    # Получаем id из параметров пути
    path_parts = request.path.split('/')
    try:
        user_id = int(path_parts[2]) if len(path_parts) >= 3 else None
    except ValueError:
        return Response(400, {"Content-Type": "text/html"}, SimpleCookie(), "Некорректный ID пользователя")
    
    if user_id is None:
        return Response(400, {"Content-Type": "text/html"}, SimpleCookie(), "ID пользователя не указан")
    
    auth_token = request.cookie.get("auth_token")
    token_user_id = check_token({"Authorization": f"Bearer {auth_token.value}"}, session) if auth_token else None
    
    if not token_user_id or token_user_id != user_id:
        return Response(302, {"Location": "/login"}, SimpleCookie(), "")

    user = session.get(User, user_id)
    if not user:
        return Response(404, {"Content-Type": "text/html"}, SimpleCookie(), "Пользователь не найден")

    # Проверяем наличие флага успеха
    success_message = ""
    response_cookie = SimpleCookie()
    
    if "update_success" in request.cookie and request.cookie["update_success"].value == "1":
        success_message = "Данные успешно обновлены"
        response_cookie["update_success"] = "0"
        response_cookie["update_success"]["path"] = "/"

    try:
        reg_form = session.exec(select(RegistrationForm).where(RegistrationForm.user_id == user_id)).first()
        form_data = reg_form.__dict__ if reg_form else {}
    except Exception:
        form_data = {}

    content = TEMPLATE_ENVIRONMENT.get_template("edit.html").render(
        form_data=form_data, 
        errors={}, 
        STATIC_URL=STATIC_URL, 
        DEFAULT_URL=DEFAULT_URL,
        user_id=user_id,
        success_message=success_message  # Передаем сообщение в шаблон
    )
    return Response(200, {"Content-Type": "text/html"}, response_cookie, content)


@HTTPHandler.route(["PUT", "POST"], "/users/{id}")
def update_user_data(request: Request, session: Session) -> Response:
    # Получаем id из параметров пути
    path_parts = request.path.split('/')
    try:
        user_id = int(path_parts[2]) if len(path_parts) >= 3 else None
    except ValueError:
        return Response(400, {"Content-Type": "text/html"}, SimpleCookie(), "Некорректный ID пользователя")
    
    if user_id is None:
        return Response(400, {"Content-Type": "text/html"}, SimpleCookie(), "ID пользователя не указан")
    
    auth_token = request.cookie.get("auth_token")
    token_user_id = check_token({"Authorization": f"Bearer {auth_token.value}"}, session) if auth_token else None
    
    if not token_user_id or token_user_id != user_id:
        return Response(302, {"Location": "/login"}, SimpleCookie(), "")

    user = session.get(User, user_id)
    if not user:
        return Response(404, {"Content-Type": "text/html"}, SimpleCookie(), "Пользователь не найден")

    content_type = request.headers.get("Content-Type", "")
    is_ajax = APPLICATION_JSON in content_type
    errors = {}
    form_data = {}
    
    # Получаем данные формы из запроса
    try:
        if is_ajax:
            # AJAX запрос с JSON данными
            form_data = json.loads(request.body.decode())
        elif APPLICATION_URLENCODED in content_type:
            # Обычная отправка формы
            from urllib.parse import parse_qs
            data_raw = request.body.decode()
            form_data = {k: v[0] for k, v in parse_qs(data_raw).items()}
        else:
            # Неизвестный формат данных
            form_data = {}
        
        # Если данные пустые, это ошибка
        if not form_data and request.method in ["POST", "PUT"]:
            raise ValueError("Не указаны данные для обновления")
            
        validated_data = RegistrationFormModel(**form_data)
        reg_form = session.exec(select(RegistrationForm).where(RegistrationForm.user_id == user_id)).first()
        if reg_form:
            reg_form.update(session, validated_data)
            
        # Отправляем успешный ответ
        if is_ajax:
            # Для AJAX запросов возвращаем JSON
            return Response(
                200,
                {"Content-Type": APPLICATION_JSON},
                SimpleCookie(),
                json.dumps({"success": True, "message": "Данные успешно обновлены"})
            )
        else:
            # Для обычной отправки формы
            success_cookie = SimpleCookie()
            # Используем числовой флаг вместо текста
            success_cookie["update_success"] = "1"
            success_cookie["update_success"]["path"] = "/"
            return Response(
                303,  # 303 See Other - правильный код для перенаправления после POST
                {"Location": f"/users/{user_id}/edit"},
                success_cookie,
                ""
            )
            
    except ValidationError as e:
        errors = {}
        for err in e.errors():
            # Получаем имя поля и сообщение об ошибке
            field_name = err["loc"][0]
            error_message = err["msg"]
            
            # Заменяем стандартные сообщения Pydantic
            if "field required" in error_message.lower():
                error_message = "Заполните это поле"
            elif error_message.startswith("Value error, "):
                error_message = error_message[13:]
                
            errors[field_name] = error_message
        
        if is_ajax:
            # Для AJAX запросов возвращаем JSON с ошибками
            return Response(
                400,
                {"Content-Type": APPLICATION_JSON},
                SimpleCookie(),
                json.dumps({"errors": errors})
            )
        else:
            content = TEMPLATE_ENVIRONMENT.get_template("edit.html").render(
                form_data=form_data,
                errors=errors,
                STATIC_URL=STATIC_URL,
                DEFAULT_URL=DEFAULT_URL,
                user_id=user_id
            )
            return Response(400, {"Content-Type": "text/html"}, SimpleCookie(), content)
            
    except Exception as e:
        error_message = str(e)
        if error_message.startswith("Value error, "):
            error_message = error_message[13:]
        errors = {"form": error_message}
        
        if is_ajax:
            return Response(
                400,
                {"Content-Type": APPLICATION_JSON},
                SimpleCookie(),
                json.dumps({"errors": errors})
            )
        else:
            content = TEMPLATE_ENVIRONMENT.get_template("edit.html").render(
                form_data=form_data,
                errors=errors,
                STATIC_URL=STATIC_URL,
                DEFAULT_URL=DEFAULT_URL,
                user_id=user_id
            )
            return Response(400, {"Content-Type": "text/html"}, SimpleCookie(), content)
        

@HTTPHandler.route(["DELETE", "POST"], "/users/{id}/delete")
def delete_user(request: Request, session: Session) -> Response:
    # Получаем id из параметров пути
    path_parts = request.path.split('/')
    try:
        user_id = int(path_parts[2]) if len(path_parts) >= 3 else None
    except ValueError:
        if request.method == "DELETE":
            return Response(400, {"Content-Type": "application/json"}, SimpleCookie(), 
                           json.dumps({"success": False, "message": "Некорректный ID пользователя"}))
        else:
            return Response(400, {"Content-Type": "text/html"}, SimpleCookie(), "Некорректный ID пользователя")
    
    # Проверка аутентификации
    auth_token = request.cookie.get("auth_token")
    token_user_id = check_token({"Authorization": f"Bearer {auth_token.value}"}, session) if auth_token else None
    
    if not token_user_id or token_user_id != user_id:
        if request.method == "DELETE":
            return Response(401, {"Content-Type": "application/json"}, SimpleCookie(), 
                           json.dumps({"success": False, "message": "Доступ запрещен"}))
        else:
            return Response(302, {"Location": "/login"}, SimpleCookie(), "")
    
    # Обработка DELETE запроса (от JavaScript)
    if request.method == "DELETE":
        try:
            # Удаляем пользователя и все связанные данные
            User.delete_user(session, user_id)
            
            # Очищаем куки авторизации
            cookie = SimpleCookie()
            cookie["auth_token"] = ""
            cookie["auth_token"]["expires"] = 0
            cookie["auth_token"]["path"] = "/"
            
            return Response(
                200, 
                {"Content-Type": "application/json"}, 
                cookie,
                json.dumps({"success": True, "message": "Аккаунт успешно удален"})
            )
        except Exception as e:
            logging.exception(f"Error deleting user {user_id}: {str(e)}")
            return Response(
                500, 
                {"Content-Type": "application/json"}, 
                SimpleCookie(),
                json.dumps({"success": False, "message": f"Ошибка при удалении: {str(e)}"})
            )
    
    # Обработка POST запроса (без JavaScript)
    else:
        content_type = request.headers.get("Content-Type", "")
        form_data = {}
        
        if APPLICATION_URLENCODED in content_type:
            from urllib.parse import parse_qs
            try:
                data_raw = request.body.decode()
                form_data = {k: v[0] for k, v in parse_qs(data_raw).items()}
            except Exception as e:
                logging.error(f"Error parsing form data: {str(e)}")
        
        # Проверяем наличие параметра подтверждения
        has_confirm = "confirm_delete" in form_data and form_data["confirm_delete"] == "true"
        logging.info(f"Has confirm_delete: {has_confirm}, form_data: {form_data}")
        
        if not has_confirm:
            # Если нет подтверждения, возвращаем форму подтверждения
            content = TEMPLATE_ENVIRONMENT.get_template("delete_confirm.html").render(
                user_id=user_id,
                STATIC_URL=STATIC_URL,
                DEFAULT_URL=DEFAULT_URL
            )
            return Response(200, {"Content-Type": "text/html"}, SimpleCookie(), content)
        
        try:
            # Удаляем пользователя и все связанные данные
            User.delete_user(session, user_id)
            
            # Очищаем куки авторизации
            cookie = SimpleCookie()
            cookie["auth_token"] = ""
            cookie["auth_token"]["expires"] = 0
            cookie["auth_token"]["path"] = "/"
            
            # Устанавливаем куки с сообщением об успешном удалении
            cookie["delete_success"] = "1"
            cookie["delete_success"]["path"] = "/"
            
            return Response(
                302,  # Редирект
                {"Location": "/login"},
                cookie,
                ""
            )
        except Exception as e:
            logging.exception(f"Error deleting user {user_id}: {str(e)}")
            content = TEMPLATE_ENVIRONMENT.get_template("edit.html").render(
                form_data={},
                errors={"form": f"Ошибка при удалении аккаунта: {str(e)}"},
                STATIC_URL=STATIC_URL,
                DEFAULT_URL=DEFAULT_URL,
                user_id=user_id
            )
            return Response(500, {"Content-Type": "text/html"}, SimpleCookie(), content)
        

@HTTPHandler.route(["GET"], "/admin/login")
def admin_login_page(request: Request) -> Response:
    error_message = ""
    
    content = TEMPLATE_ENVIRONMENT.get_template("admin_login.html").render(
        error_message=error_message,
        STATIC_URL=STATIC_URL,
        DEFAULT_URL=DEFAULT_URL
    )
    return Response(200, {"Content-Type": "text/html"}, SimpleCookie(), content)

@HTTPHandler.route(["POST"], "/admin/login")
def admin_login_handler(request: Request, session: Session) -> Response:
    content_type = request.headers.get("Content-Type", "")
    data = {}
    
    if APPLICATION_URLENCODED in content_type:
        from urllib.parse import parse_qs
        data_raw = request.body.decode()
        data = {k: v[0] for k, v in parse_qs(data_raw).items()}
    
    username = data.get("username", "").strip()
    password = data.get("password", "")
    
    try:
        admin = Admin.get_by_username(session, username)
        
        if not admin or not admin.check_password(password):
            content = TEMPLATE_ENVIRONMENT.get_template("admin_login.html").render(
                error_message="Неверное имя пользователя или пароль",
                STATIC_URL=STATIC_URL,
                DEFAULT_URL=DEFAULT_URL
            )
            return Response(401, {"Content-Type": "text/html"}, SimpleCookie(), content)
        
        # Создаем токен для админа
        admin_token = admin.create_token(session)
        
        cookie = SimpleCookie()
        cookie["admin_token"] = admin_token
        cookie["admin_token"]["path"] = "/"
        
        return Response(
            303,
            {"Location": "/admin/dashboard"},
            cookie,
            ""
        )
    except Exception as e:
        logging.exception("Error in admin login")
        content = TEMPLATE_ENVIRONMENT.get_template("admin_login.html").render(
            error_message=f"Ошибка: {str(e)}",
            STATIC_URL=STATIC_URL,
            DEFAULT_URL=DEFAULT_URL
        )
        return Response(500, {"Content-Type": "text/html"}, SimpleCookie(), content)

@HTTPHandler.route(["GET"], "/admin/dashboard")
def admin_dashboard(request: Request, session: Session) -> Response:
    # Проверка аутентификации админа
    admin_token_value = None
    if "admin_token" in request.cookie:
        admin_token_value = request.cookie["admin_token"].value
    
    admin_token = AdminToken.get_by_token(session, admin_token_value) if admin_token_value else None
    
    if not admin_token:
        return Response(302, {"Location": "/admin/login"}, SimpleCookie(), "")
    
    # Получаем список всех пользователей с их регистрационными формами
    users_with_forms = []
    birth_years = set()  # Для списка уникальных годов рождения
    
    user_forms = session.exec(
        select(User, RegistrationForm)
        .join(RegistrationForm, User.id == RegistrationForm.user_id)
    ).all()
    
    for user, form in user_forms:
        # Извлекаем год из даты рождения
        birth_year = ""
        try:
            if form.child_birthdate:
                birth_year = form.child_birthdate.split('-')[0]
                birth_years.add(birth_year)
        except Exception:
            pass
            
        users_with_forms.append({
            "id": user.id,
            "login": user.login,
            "child_name": form.child_name,
            "child_birthdate": form.child_birthdate,
            "birth_year": birth_year,
            "parent_name": form.parent_name,
            "phone": form.phone,
            "email": form.email,
            "comment": form.comment
        })
    
    # Сортируем годы для выпадающего списка
    birth_years = sorted(birth_years, reverse=True)
    
    content = TEMPLATE_ENVIRONMENT.get_template("admin_dashboard.html").render(
        users=users_with_forms,
        birth_years=birth_years,
        STATIC_URL=STATIC_URL,
        DEFAULT_URL=DEFAULT_URL
    )
    return Response(200, {"Content-Type": "text/html"}, SimpleCookie(), content)

@HTTPHandler.route(["GET"], "/admin/logout")
def admin_logout(request: Request, session: Session) -> Response:
    admin_token_value = None
    if "admin_token" in request.cookie:
        admin_token_value = request.cookie["admin_token"].value
    
    if admin_token_value:
        AdminToken.invalidate_token(session, admin_token_value)
    
    # Очищаем куки
    cookie = SimpleCookie()
    cookie["admin_token"] = ""
    cookie["admin_token"]["expires"] = 0
    cookie["admin_token"]["path"] = "/"
    
    return Response(
        303,
        {"Location": "/admin/login"},
        cookie,
        ""
    )