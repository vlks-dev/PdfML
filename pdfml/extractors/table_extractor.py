`"""
Модуль для извлечения таблиц из PDF-документов
"""

import camelot
import pandas as pd
import numpy as np
import os
import tempfile
from PIL import Image

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TableExtractor:
    """
    Класс для извлечения таблиц из PDF-документов.
    """
    
    def __init__(self, flavor="lattice"):
        """
        Инициализация экстрактора таблиц.
        
        Args:
            flavor (str): Метод извлечения таблиц.
                'lattice': для таблиц с видимыми линиями.
                'stream': для таблиц без видимых линий.
        """
        self.flavor = flavor
        
    def extract_tables(self, pdf_path, pages="all", **kwargs):
        """
        Извлечение таблиц из PDF-документа.
        
        Args:
            pdf_path (str): Путь к PDF-файлу
            pages (str или list): Страницы для извлечения таблиц.
                                'all' для всех страниц или список номеров страниц.
            **kwargs: Дополнительные параметры для camelot.read_pdf
            
        Returns:
            dict: Словарь {номер_страницы: список_таблиц}
        """
        try:
            # Устанавливаем параметры по умолчанию, если не указаны
            kwargs.setdefault("flavor", self.flavor)
            
            logger.info(f"Извлечение таблиц из {pdf_path} (страницы: {pages})")
            tables = camelot.read_pdf(pdf_path, pages=pages, **kwargs)
            
            logger.info(f"Найдено {len(tables)} таблиц")
            
            # Группируем таблицы по страницам
            result = {}
            for i, table in enumerate(tables._tables):
                page_num = table.page
                
                if page_num not in result:
                    result[page_num] = []
                    
                # Преобразуем в DataFrame для удобства работы
                df = table.df
                
                # Добавляем метаданные таблицы
                table_data = {
                    "dataframe": df,
                    "accuracy": table.accuracy,
                    "whitespace": table.whitespace,
                    "order": i,
                    "shape": df.shape
                }
                
                result[page_num].append(table_data)
                
            return result
            
        except Exception as e:
            logger.error(f"Ошибка при извлечении таблиц: {e}")
            return {}
    
    def extract_tables_from_regions(self, pdf_path, regions, **kwargs):
        """
        Извлечение таблиц из определенных регионов документа.
        
        Args:
            pdf_path (str): Путь к PDF-файлу
            regions (dict): Словарь {номер_страницы: список_координат_регионов}
                           Формат координат: [x1, y1, x2, y2]
            **kwargs: Дополнительные параметры для camelot.read_pdf
            
        Returns:
            dict: Словарь {номер_страницы: список_таблиц}
        """
        result = {}
        
        for page_num, region_list in regions.items():
            result[page_num] = []
            
            for i, region in enumerate(region_list):
                try:
                    # Устанавливаем параметры по умолчанию
                    kwargs.setdefault("flavor", self.flavor)
                    
                    # Добавляем координаты области
                    kwargs["table_areas"] = [region]
                    
                    logger.info(f"Извлечение таблицы из региона {region} на странице {page_num}")
                    tables = camelot.read_pdf(pdf_path, pages=str(page_num), **kwargs)
                    
                    if len(tables) > 0:
                        table = tables[0]
                        df = table.df
                        
                        table_data = {
                            "dataframe": df,
                            "accuracy": table.accuracy,
                            "whitespace": table.whitespace,
                            "region": region,
                            "shape": df.shape
                        }
                        
                        result[page_num].append(table_data)
                    else:
                        logger.warning(f"Таблица не найдена в регионе {region} на странице {page_num}")
                
                except Exception as e:
                    logger.error(f"Ошибка при извлечении таблицы из региона {region}: {e}")
        
        return result
    
    def tables_to_csv(self, tables, output_dir):
        """
        Сохранение извлеченных таблиц в CSV файлы.
        
        Args:
            tables (dict): Словарь с извлеченными таблицами
            output_dir (str): Путь для сохранения CSV файлов
            
        Returns:
            list: Список путей к созданным файлам
        """
        os.makedirs(output_dir, exist_ok=True)
        file_paths = []
        
        for page_num, table_list in tables.items():
            for i, table in enumerate(table_list):
                df = table["dataframe"]
                
                file_name = f"page_{page_num}_table_{i}.csv"
                file_path = os.path.join(output_dir, file_name)
                
                df.to_csv(file_path, index=False)
                file_paths.append(file_path)
                
                logger.info(f"Таблица сохранена в {file_path}")
        
        return file_paths 