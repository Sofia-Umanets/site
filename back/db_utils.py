import time
import os
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

def wait_for_db(max_retries=30, retry_interval=2):
    
    username = os.environ.get('DB_USERNAME')
    password = os.environ.get('DB_PASSWORD')
    database = os.environ.get('DB_NAME')
    host = os.environ.get('MYSQL_HOST', 'db')
    
    conn_str = f"mysql+pymysql://{username}:{password}@{host}/{database}"
    engine = create_engine(conn_str)
    
    retry_count = 0
    connected = False
    last_error = None
    
    print(f"Пытаемся подключиться к MySQL на {host}...")
    
    while not connected and retry_count < max_retries:
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            connected = True
            print(f"Успешное подключение к базе данных {database} на {host}")
        except Exception as e:
            retry_count += 1
            last_error = str(e)
            print(f"Попытка {retry_count}/{max_retries}: Не удалось подключиться к базе данных. Ошибка: {last_error}")
            time.sleep(retry_interval)
    
    if not connected:
        raise Exception(f"Не удалось подключиться к базе данных после {max_retries} попыток. Последняя ошибка: {last_error}")
    
    return engine