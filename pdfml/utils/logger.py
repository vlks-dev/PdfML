"""
Модуль для настройки логгирования
"""

import logging
import os
import sys
from datetime import datetime


def get_logger(name, level=logging.INFO):
    """
    Создание и настройка логгера.
    
    Args:
        name (str): Имя логгера
        level (int): Уровень логгирования
        
    Returns:
        logging.Logger: Настроенный логгер
    """
    logger = logging.getLogger(name)
    
    # Если логгер уже был настроен, возвращаем его
    if logger.handlers:
        return logger
    
    logger.setLevel(level)
    
    # Создаем обработчик для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Определяем формат сообщений
    formatter = logging.Formatter(
        '[%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Добавляем обработчик к логгеру
    logger.addHandler(console_handler)
    
    # Создаем обработчик для записи в файл
    logs_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(logs_dir, f'pdfml_{current_date}.log')
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    return logger 