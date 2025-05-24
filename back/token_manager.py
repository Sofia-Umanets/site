import logging
import threading
import time
from datetime import datetime, timedelta
from typing import Optional

from back.utils import cleanup_expired_tokens, delete_old_inactive_tokens
from sqlmodel import Session, select
from back.models import Token

def start_token_cleanup_task(engine, interval: int = 3600):
    def cleanup_task():
        while True:
            try:
                with Session(engine) as session:
                    expired_count = cleanup_expired_tokens(session)
                    if expired_count > 0:
                        logging.info(f"Периодическая очистка: деактивировано {expired_count} просроченных токенов")
                    
                    deleted_count = delete_old_inactive_tokens(session, max_age_days=7)
                    if deleted_count > 0:
                        logging.info(f"Периодическая очистка: удалено {deleted_count} старых неактивных токенов")
            except Exception as e:
                logging.error(f"Ошибка при очистке токенов: {e}")
            
            time.sleep(interval)
            
    cleanup_thread = threading.Thread(target=cleanup_task, daemon=True)
    cleanup_thread.start()
    logging.info(f"Запущена задача периодической очистки токенов (интервал: {interval} сек)")
    
    return cleanup_thread