import os
import string

from email.utils import formatdate
from jinja2 import Environment, FileSystemLoader
from sqlmodel import create_engine
from dotenv import load_dotenv 


load_dotenv()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

DEFAULT_URL = "/"
STATIC_URL = "/front/"

# Настройки шаблонизатора
TEMPLATE_ENVIRONMENT = Environment(
    loader=FileSystemLoader("back/templates"),
    autoescape=True,
)

DB_CONFIG = {
    'host': os.getenv('MYSQL_HOST', os.getenv('DB_HOST', 'db')),
    'database': os.getenv('MYSQL_DATABASE', os.getenv('DB_NAME', 'sportscool')),
    'user': os.getenv('MYSQL_USER', os.getenv('DB_USERNAME', 'sofiaumanets')),
    'password': os.getenv('MYSQL_PASSWORD', os.getenv('DB_PASSWORD')),
    'port': int(os.getenv('MYSQL_PORT', os.getenv('DB_PORT', 3306))),
}

if not DB_CONFIG['user'] or not DB_CONFIG['password'] or not DB_CONFIG['database']:
    raise ValueError(
        "Missing database configuration. Please make sure DB_USERNAME/MYSQL_USER, "
        "DB_PASSWORD/MYSQL_PASSWORD, and DB_NAME/MYSQL_DATABASE are set in your "
        ".env file or environment."
    )

DATABASE_URL = f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"

engine = create_engine(DATABASE_URL, echo=True)

EPOCH = formatdate(0, usegmt=True)
ALPHABET = string.ascii_letters + string.digits

APPLICATION_URLENCODED = "application/x-www-form-urlencoded"
APPLICATION_JSON = "application/json"
APPLICATION_CONTENT_TYPE = (APPLICATION_URLENCODED, APPLICATION_JSON)