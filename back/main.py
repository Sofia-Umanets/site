from http.server import HTTPServer
from sqlmodel import SQLModel, Session
import logging
from back.handler import HTTPHandler
from back.config import HOST, PORT, engine
from back.models import init_admin
from back.utils import cleanup_expired_tokens, delete_inactive_tokens
from back.db_utils import wait_for_db

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    
    wait_for_db(max_retries=60, retry_interval=2)
    
    SQLModel.metadata.create_all(engine)
    
    #init_admin()
    
    with Session(engine) as session:
        # Деактивируем просроченные токены
        expired = cleanup_expired_tokens(session)
        if expired > 0:
            logging.info(f"Деактивировано {expired} просроченных токенов")
        
        # Удаляем все неактивные токены без ожидания
        deleted = delete_inactive_tokens(session)
        if deleted > 0:
            logging.info(f"Удалено {deleted} неактивных токенов")
    
    # Запуск сервера
    httpd = HTTPServer((HOST, PORT), HTTPHandler)
    print(f"Server started at http://{HOST}:{PORT}")
    httpd.serve_forever()

if __name__ == "__main__":
    main()