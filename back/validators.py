import re
from typing import Optional
from typing_extensions import Annotated
from datetime import date

from pydantic import BaseModel, EmailStr, validator, Field, field_validator


class RegistrationFormModel(BaseModel):
    child_name: str = Field(..., description="ФИО ребёнка")
    child_birthdate: str = Field(..., description="Дата рождения ребёнка")
    parent_name: str = Field(..., description="ФИО родителя")
    phone: str = Field(..., description="Телефон")
    email: EmailStr = Field(..., description="Email")
    comment: Optional[str] = Field(None, description="Комментарий")
    consent: bool = Field(..., description="Согласие на обработку данных")

    @validator("child_name", "parent_name")
    def valid_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Заполните это поле")
        v = v.strip()
        if not re.match(r"^[A-Za-zА-Яа-яЁё\s\-]+$", v):
            raise ValueError("Имя должно содержать только буквы")
        return v

    @validator("child_birthdate")
    def valid_birthdate(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Заполните это поле")
        try:
            parts = v.split("-")
            if len(parts) != 3:
                raise ValueError()
            year, month, day = map(int, parts)
            bdate = date(year, month, day)
        except Exception:
            raise ValueError("Неверный формат даты рождения. Используйте ГГГГ-ММ-ДД")
        today = date.today()
        age = (today - bdate).days // 365
        if age < 6 or age > 8:
            raise ValueError("Возраст ребёнка должен быть от 6 до 8 лет")
        return v

    @validator("phone")
    def valid_phone(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Заполните это поле")
        # Очищаем от всех не-цифр
        digits_only = ''.join(filter(str.isdigit, v))
        
        # Проверяем общую длину
        if len(digits_only) != 11:
            return "Номер телефона должен содержать 11 цифр"
        
        # Проверяем начало номера (должен начинаться с 7 или 8)
        if not (digits_only.startswith('7') or digits_only.startswith('8')):
            return "Номер должен начинаться с 7 или 8"
        
        # Допустим несколько форматов записи для удобства
        pattern = r'^(\+7|7|8)[\s\-]?\(?[9]\d{2}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}$'
        if not re.match(pattern, v):
            return "Неверный формат телефона. Пример: +7 (999) 123-45-67"
        
        return v
    
    @validator("email")
    def valid_email(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Заполните это поле")
        return v

    @validator("consent")
    def consent_must_be_true(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("Требуется согласие на обработку данных")
        return v
    
    @validator("comment")
    def validate_comment_length(cls, v: Optional[str]) -> Optional[str]:
        if v and len(v) > 200:
            raise ValueError("Комментарий не может превышать 200 символов")
        return v