from datetime import datetime, timedelta
import logging
from typing import List, Optional
import hashlib
import secrets

from sqlalchemy import Engine
from sqlmodel import SQLModel, Field, Relationship, Session, delete, select, update
from back.validators import RegistrationFormModel

def hash_password(password: str, salt: bytes = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_bytes(16)
    hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 100000)
    return hashed.hex(), salt.hex()

def check_password(plain_password: str, password_hash: str, salt_hex: str) -> bool:
    salt = bytes.fromhex(salt_hex)
    hashed = hashlib.pbkdf2_hmac('sha256', plain_password.encode(), salt, 100000)
    return hashed.hex() == password_hash

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    login: str = Field(unique=True)
    password_hash: str
    password_salt: str

    registration: Optional["RegistrationForm"] = Relationship(back_populates="user")

    @classmethod
    def create(cls, session: Session, login: str, plain_password: str) -> "User":
        password_hash, salt = hash_password(plain_password)
        user = cls(login=login, password_hash=password_hash, password_salt=salt)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @classmethod
    def get_by_login(cls, session: Session, login: str) -> "User":
        return session.exec(select(User).where(User.login == login)).one()
    
    @classmethod
    def delete_user(cls, session: Session, user_id: int) -> None:
        user = session.get(cls, user_id)
        if user:
            # Удаление связанных данных
            RegistrationForm.delete_registration(session, user_id)
            session.exec(delete(Token).where(Token.user_id == user_id))
            session.delete(user)
            session.commit()


    def check_password(self, password: str) -> bool:
        return check_password(password, self.password_hash, self.password_salt)

class RegistrationForm(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    child_name: str
    child_birthdate: str
    parent_name: str
    phone: str
    email: str
    comment: Optional[str] = Field(default=None, max_length=200)
    consent: bool

    user_id: int = Field(foreign_key="user.id")
    user: User = Relationship(back_populates="registration")

    @classmethod
    def create(cls, session: Session, data: RegistrationFormModel, user: User) -> "RegistrationForm":
        form = cls(**data.model_dump(), user=user)
        session.add(form)
        session.commit()
        session.refresh(form)
        return form

    def update(self, session: Session, data: RegistrationFormModel) -> "RegistrationForm":
        for key, value in data.model_dump().items():
            setattr(self, key, value)
        session.add(self)
        session.commit()
        session.refresh(self)
        return self
    
    @classmethod
    def delete_registration(cls, session: Session, user_id: int) -> None:
        registration = session.exec(select(cls).where(cls.user_id == user_id)).first()
        if registration:
            session.delete(registration)
            session.commit()

class Token(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    token: str
    expiration_time: datetime
    active: bool = True


class Admin(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True)
    password_hash: str
    password_salt: str
    
    admin_tokens: List["AdminToken"] = Relationship(back_populates="admin")
    
    @classmethod
    def create(cls, session: Session, username: str, plain_password: str) -> "Admin":
        password_hash, salt = hash_password(plain_password)
        admin = cls(username=username, password_hash=password_hash, password_salt=salt)
        session.add(admin)
        session.commit()
        session.refresh(admin)
        return admin
    
    @classmethod
    def get_by_username(cls, session: Session, username: str) -> Optional["Admin"]:
        return session.exec(select(Admin).where(Admin.username == username)).first()
    
    def check_password(self, password: str) -> bool:
        return check_password(password, self.password_hash, self.password_salt)
    
    def create_token(self, session: Session) -> str:
        token_value = secrets.token_urlsafe(32)
        expiration = datetime.now() + timedelta(hours=8)  # 8 часов валидности для токенов админа
        
        # Создаем запись в таблице токенов
        admin_token = AdminToken(
            admin_id=self.id,
            token=token_value, 
            expiration_time=expiration,
            active=True,
            admin=self
        )
        session.add(admin_token)
        session.commit()
        return token_value


class AdminToken(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    admin_id: int = Field(foreign_key="admin.id")
    token: str
    expiration_time: datetime
    active: bool = True
    
    admin: Admin = Relationship(back_populates="admin_tokens")
    
    @classmethod
    def invalidate_expired(cls, session: Session) -> None:
        """Инвалидирует просроченные токены"""
        session.exec(
            update(AdminToken)
            .where(AdminToken.expiration_time < datetime.now())
            .where(AdminToken.active == True)
            .values(active=False)
        )
        session.commit()
    
    @classmethod
    def get_by_token(cls, session: Session, token_value: str) -> Optional["AdminToken"]:
        """Получает токен по его значению"""
        cls.invalidate_expired(session)
        return session.exec(
            select(AdminToken)
            .where(AdminToken.token == token_value)
            .where(AdminToken.active == True)
        ).first()
    
    @classmethod
    def invalidate_token(cls, session: Session, token_value: str) -> None:
        """Инвалидирует токен"""
        token = cls.get_by_token(session, token_value)
        if token:
            token.active = False
            session.add(token)
            session.commit()


def init_admin():
    """Initialize admin user if it doesn't exist"""
    from back.config import engine
    
    with Session(engine) as session:
        try:
            admin = session.exec(select(Admin).where(Admin.username == "admin")).first()
            if not admin:
                Admin.create(session, "admin", "admin")
                logging.info("Admin user created")
        except Exception as e:
            logging.error(f"Error initializing admin: {str(e)}")