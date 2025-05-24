import json
from collections.abc import Callable
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

from pydantic import BaseModel, ValidationError
from sqlmodel import Session

from back.config import *
from back.handler import HTTPHandler
from back.models import User
from back.custom_types import Request, UserNoneType, Response
from back.utils import  get_user, get_user_or_none
from back.validators import RegistrationFormModel


def urlencoded(content: str) -> dict:
    formdata = {}
    for name, value in parse_qs(content).items():
        if name.endswith("[]"):
            formdata[name[:-2]] = value
        else:
            formdata[name] = value[0]
    return formdata


def get_data(request: Request, rfile):
    headers = request.headers

    content_type = headers.get("Content-Type", "")
    if content_type not in APPLICATION_CONTENT_TYPE:
        raise Exception("invalid Content-Type")

    content_length = int(headers.get("Content-Length", 0))
    if content_length == 0:
        raise Exception("invalid Content-Length")

    content = rfile.read(content_length).decode()
    if content_type == APPLICATION_URLENCODED:
        data = urlencoded(content)
    elif content_type == APPLICATION_JSON:
        data = json.loads(content)
    else:
        data = {}
    return data


def get_kwargs(function: Callable, handler: HTTPHandler) -> dict:
    annotations = function.__annotations__.copy()
    if "return" in annotations:
        annotations.pop("return")

    request = handler.req()
    query = urlencoded(request.query)
    kwargs = {}
    
    for name, _type in annotations.items():
        if _type == Session:
            kwargs[name] = handler.session
        elif _type == Request:
            kwargs[name] = request
        elif _type == UserNoneType:
            kwargs[name] = get_user_or_none(request, handler.session)
        elif _type == User:
            kwargs[name] = get_user(request, handler.session)
        elif issubclass(_type, BaseModel):
            data = get_data(request, handler.rfile)
            setattr(handler, "request_data", data)
            kwargs[name] = _type(**data)
        elif name in request.params:
            # Параметр из пути
            try:
                kwargs[name] = _type(request.params[name])
            except ValueError:
                raise Exception(f"Invalid path parameter: {name}")
        else:
            kwargs[name] = _type(query[name])
    return kwargs

def validation_error_response(
    handler: HTTPHandler, url: str, e: ValidationError,
) -> Response:
    content_type = handler.headers.get("Content-Type", "")

    cookie = SimpleCookie()
    if content_type == APPLICATION_URLENCODED:
        for field in e.model.__fields__:
            cookie[field] = getattr(handler, "request_data").get(field, "")

        for err in e.errors():
            location, msg = err["loc"][0], err["msg"]
            cookie[f"{location}_err"] = msg.capitalize()
        return Response(
            status=303, headers={"Location": url},
            cookie=cookie, content="",
        )

    # AJAX: возвращаем словарь полей-ошибок
    errors = {}
    for err in e.errors():
        location, msg = err["loc"][0], err["msg"]
        errors[location] = msg.capitalize()
    return Response(
        status=400, headers={"Content-Type": APPLICATION_JSON},
        cookie=cookie, content=json.dumps(errors),
    )