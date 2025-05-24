import secrets
import binascii
from datetime import datetime, timedelta
from email.utils import formatdate
from http.cookies import SimpleCookie
from typing import Optional

from sqlalchemy.exc import NoResultFound
from sqlmodel import Session, select, update

from back.config import ALPHABET, EPOCH
from back.models import AdminToken, Token, User
from back.custom_types import Request, UserNoneType
from back.validators import RegistrationFormModel

class UserIsNotAuthenticated(Exception):
    pass

class BadPasswordError(Exception):
    pass

class BadUserError(Exception):
    pass

def generate_login(length: int = 8) -> str:
    return secrets.token_hex(length // 2)  # 8 символов hex = 4 байта

def generate_password(length: int = 8) -> str:
    return secrets.token_urlsafe(length)

#озвращает пользователя по данным из запроса
def get_user(request: Request, session: Session) -> User:
    try:
        authorization = request.headers["Authorization"].strip().split(" ")
        login, password = binascii.a2b_base64(authorization[-1]).decode().split(":")
        user = User.get_by_login(session, login)
        if not user.check_password(password):
            raise BadPasswordError("Bad password")
        return user
    except KeyError:
        raise UserIsNotAuthenticated("User is not authenticated")
    except (
        ValueError,
        binascii.Error,
        NoResultFound,
        BadPasswordError,
    ):
        raise BadUserError("Bad user")

#Возвращает пользователя или None, если аутентификация не удалась
def get_user_or_none(request: Request, session: Session) -> UserNoneType:
    try:
        return get_user(request, session)
    except UserIsNotAuthenticated:
        return None

#Устанавливает куки с данными формы регистрации
def set_cookie(cookie: SimpleCookie, data: RegistrationFormModel):
    expires = (datetime.now() + timedelta(days=365)).timestamp()
    for field in RegistrationFormModel.model_fields:
        if field == "comment": 
            continue
        if field in data.model_dump():
            value = data.model_dump()[field]
            cookie[field] = str(value)
            cookie[field]["expires"] = formatdate(expires, usegmt=True)
        else:
            cookie[field] = str(getattr(data, field))
            cookie[field]["expires"] = formatdate(expires, usegmt=True)

def clear_cookie(
    request_cookie: SimpleCookie, keys: tuple[str, ...]
) -> SimpleCookie:
    """Очищает указанные куки."""
    cookie = SimpleCookie()
    for name in request_cookie:
        if name.endswith("_err") or name in keys:
            cookie[name] = request_cookie[name]
            cookie[name]["expires"] = EPOCH
    return cookie

def generate_token(user_id: int, session: Session, expiration_time: int = 3600, max_tokens: int = 3) -> str:

    # Получаем все активные токены пользователя, отсортированные по времени создания
    user_tokens = session.exec(
        select(Token)
        .where(Token.user_id == user_id, Token.active == True)
        .order_by(Token.expiration_time.desc())
    ).all()
    
    # Если токенов больше лимита, удаляем самые старые
    if len(user_tokens) >= max_tokens:
        tokens_to_delete = user_tokens[max_tokens-1:]
        for old_token in tokens_to_delete:
            session.delete(old_token)
    
    # Создаем новый токен
    token = secrets.token_urlsafe(32)
    token_entry = Token(
        user_id=user_id, 
        token=token, 
        expiration_time=datetime.now() + timedelta(seconds=expiration_time),
        active=True
    )
    session.add(token_entry)
    session.commit()
    
    return token

def check_token(request: dict, session: Session) -> Optional[int]:
    token = request.get("Authorization", "").split(" ")[-1]
    
    token_entry = session.exec(select(Token).where(
        Token.token == token,
        Token.active == True
    )).first()
    
    if token_entry:
        if token_entry.expiration_time > datetime.now():
            return token_entry.user_id
        else:
            token_entry.active = False
            session.commit()
    
    return None

# Добавьте новые функции для управления токенами
def cleanup_expired_tokens(session: Session) -> int:
    now = datetime.now()
    
    expired_tokens = session.exec(
        select(Token)
        .where(Token.expiration_time < now, Token.active == True)
    ).all()
    
    count = 0
    for token in expired_tokens:
        token.active = False
        count += 1
    
    if count > 0:
        session.commit()
        
    return count

def delete_old_inactive_tokens(session: Session, max_age_days: int = 30) -> int:
    cutoff_date = datetime.now() - timedelta(days=max_age_days)
    
    # Находим старые неактивные токены
    old_tokens = session.exec(
        select(Token)
        .where(Token.expiration_time < cutoff_date, Token.active == False)
    ).all()
    
    # Удаляем их
    count = 0
    for token in old_tokens:
        session.delete(token)
        count += 1
    
    if count > 0:
        session.commit()
        
    return count

def delete_inactive_tokens(session: Session) -> int:
    """Удаляет все неактивные токены, независимо от их возраста"""
    
    # Находим все неактивные токены
    inactive_tokens = session.exec(
        select(Token)
        .where(Token.active == False)
    ).all()
    
    # Удаляем их
    count = 0
    for token in inactive_tokens:
        session.delete(token)
        count += 1
    
    if count > 0:
        session.commit()
        
    return count

def invalidate_all_user_tokens(session: Session, user_id: int) -> int:
    """Деактивирует все токены пользователя"""
    user_tokens = session.exec(
        select(Token)
        .where(Token.user_id == user_id, Token.active == True)
    ).all()
    
    count = 0
    for token in user_tokens:
        token.active = False
        count += 1
    
    if count > 0:
        session.commit()
        
    return count


def generate_admin_token(admin_id: int, session: Session) -> str:
    """Generates a token for an admin user"""
    token_value = secrets.token_urlsafe(32)
    expiration = datetime.now() + timedelta(hours=8)
    
    # Создаем запись в таблице токенов
    admin_token = AdminToken(
        admin_id=admin_id,
        token=token_value, 
        expiration_time=expiration,
        active=True
    )
    session.add(admin_token)
    session.commit()
    return token_value

def check_admin_token(headers: dict, session: Session) -> Optional[int]:
    """Checks if admin token is valid and returns admin_id if it is"""
    auth_header = headers.get("Authorization", "")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    
    token_value = auth_header[7:]
    
    # Проверяем и инвалидируем просроченные токены
    session.exec(
        update(AdminToken)
        .where(AdminToken.expiration_time < datetime.now())
        .where(AdminToken.active == True)
        .values(active=False)
    )
    
    # Ищем активный токен
    token = session.exec(
        select(AdminToken)
        .where(AdminToken.token == token_value)
        .where(AdminToken.active == True)
    ).first()
    
    return token.admin_id if token else None