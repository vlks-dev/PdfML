#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Пример извлечения данных из форм с использованием LayoutLM
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Добавляем родительскую директорию в sys.path для импорта pdfml
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdfml.models.form_extractor import FormExtractor


def extract_form_fields(pdf_path, output_dir):
    """
    Извлечение полей формы из PDF-документа
    """
    print(f"Извлечение полей формы из {pdf_path}")
    
    # Инициализируем экстрактор форм
    extractor = FormExtractor()
    
    # Извлекаем поля формы
    form_fields = extractor.extract_form_fields(pdf_path)
    
    # Подсчитываем количество найденных полей
    total_fields = sum(len(fields) for fields in form_fields.values())
    print(f"Найдено полей формы: {total_fields}")
    
    # Выводим примеры найденных полей
    for page_num, fields in form_fields.items():
        print(f"\nСтраница {page_num + 1}:")
        
        # Выводим до 5 полей для примера
        for i, field in enumerate(fields[:5]):
            print(f"  Поле {i+1}: {field['field_name']} = {field['field_value']}")
            
        if len(fields) > 5:
            print(f"  ... и еще {len(fields) - 5} полей")
    
    # Сохраняем результаты в JSON
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "form_fields.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(form_fields, f, ensure_ascii=False, indent=2)
        
    print(f"\nРезультаты сохранены в {output_file}")
    
    # Извлекаем пары ключ-значение из текста каждой страницы
    # для дополнительного контекста
    for page_num, fields in form_fields.items():
        if not fields:
            continue
            
        # Объединяем весь текст полей
        all_text = " ".join([
            f"{field['field_name']} {field['field_value']}"
            for field in fields
        ])
        
        # Извлекаем пары ключ-значение
        key_value_pairs = extractor.extract_key_value_pairs(all_text, fields)
        
        # Сохраняем результаты
        kv_file = os.path.join(output_dir, f"key_value_page_{page_num}.json")
        with open(kv_file, 'w', encoding='utf-8') as f:
            json.dump(key_value_pairs, f, ensure_ascii=False, indent=2)
    
    print("\nИзвлечение полей завершено")


def parse_arguments():
    """Разбор аргументов командной строки"""
    parser = argparse.ArgumentParser(description="Пример извлечения данных из форм")
    
    parser.add_argument("pdf_path", help="Путь к PDF-файлу для анализа")
    parser.add_argument("--output", "-o", default="output/forms", 
                      help="Директория для сохранения результатов")
    
    return parser.parse_args()


def main():
    """Основная функция примера"""
    args = parse_arguments()
    
    # Проверяем наличие файла
    if not os.path.exists(args.pdf_path):
        print(f"Ошибка: Файл {args.pdf_path} не найден")
        return 1
    
    # Извлекаем поля формы
    extract_form_fields(args.pdf_path, args.output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 