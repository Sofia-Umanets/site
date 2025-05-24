from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from typing import TypeAlias

from back.models import User

UserNoneType: TypeAlias = User | None


@dataclass
class Request:
    headers: dict[str, str]
    cookie: SimpleCookie
    method: str
    path: str
    query: str
    body: bytes
    params: dict[str, str] = field(default_factory=dict)

@dataclass
class Response:
    status: int
    headers: dict[str, str]
    cookie: SimpleCookie
    content: str