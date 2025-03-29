#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Пример базового использования библиотеки PdfML
"""

import os
import sys
import argparse
from pathlib import Path

# Добавляем родительскую директорию в sys.path для импорта pdfml
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pdfml.core.pdf_analyzer import PDFAnalyzer
from pdfml.core.pdf_processor import PDFProcessor
from pdfml.extractors.table_extractor import TableExtractor


def extract_text_example(pdf_path, output_dir):
    """Пример извлечения текста из PDF"""
    print(f"Извлечение текста из {pdf_path}")
    
    with PDFProcessor(pdf_path) as processor:
        text_dict = processor.extract_text()
        
        # Выводим первые 200 символов из каждой страницы
        for page_num, text in text_dict.items():
            print(f"\nСтраница {page_num + 1}:")
            preview = text[:200] + "..." if len(text) > 200 else text
            print(preview)
            
    print("\nИзвлечение текста завершено")


def extract_tables_example(pdf_path, output_dir):
    """Пример извлечения таблиц из PDF"""
    print(f"Извлечение таблиц из {pdf_path}")
    
    extractor = TableExtractor()
    tables = extractor.extract_tables(pdf_path)
    
    print(f"Найдено таблиц: {sum(len(page_tables) for page_tables in tables.values())}")
    
    # Сохраняем таблицы в CSV
    csv_dir = os.path.join(output_dir, "tables")
    csv_files = extractor.tables_to_csv(tables, csv_dir)
    
    print(f"Таблицы сохранены в {csv_dir}")
    print("Список созданных файлов:")
    for file_path in csv_files:
        print(f"  - {os.path.basename(file_path)}")
        
    print("\nИзвлечение таблиц завершено")


def full_analysis_example(pdf_path, output_dir):
    """Пример полного анализа PDF-документа"""
    print(f"Запуск полного анализа {pdf_path}")
    
    with PDFAnalyzer(pdf_path) as analyzer:
        # Выполняем полный анализ
        results = analyzer.analyze_all()
        
        # Печатаем краткую информацию о результатах
        num_pages = len(results["text"])
        print(f"\nОбработано страниц: {num_pages}")
        
        num_tables = sum(len(page_tables) for page_tables in results["tables"].values())
        print(f"Найдено таблиц: {num_tables}")
        
        num_entities = sum(len(page_entities) for page_entities in results["entities"].values())
        print(f"Найдено именованных сущностей: {num_entities}")
        
        if results["form_fields"]:
            num_fields = sum(len(page_fields) for page_fields in results["form_fields"].values())
            print(f"Найдено полей формы: {num_fields}")
        
        # Сохраняем результаты анализа
        result_dir = analyzer.save_results(output_dir)
        print(f"\nРезультаты сохранены в {result_dir}")
        
    print("\nАнализ завершен")


def parse_arguments():
    """Разбор аргументов командной строки"""
    parser = argparse.ArgumentParser(description="Примеры использования библиотеки PdfML")
    
    parser.add_argument("pdf_path", help="Путь к PDF-файлу для анализа")
    parser.add_argument("--output", "-o", default="output", help="Директория для сохранения результатов")
    parser.add_argument("--mode", "-m", choices=["text", "tables", "full"], default="full",
                        help="Режим работы: text - только текст, tables - только таблицы, full - полный анализ")
    parser.add_argument("--ocr", action="store_true", help="Использовать OCR для извлечения текста")
    
    return parser.parse_args()


def main():
    """Основная функция примера"""
    args = parse_arguments()
    
    # Проверяем наличие файла
    if not os.path.exists(args.pdf_path):
        print(f"Ошибка: Файл {args.pdf_path} не найден")
        return 1
        
    # Создаем директорию для вывода, если не существует
    os.makedirs(args.output, exist_ok=True)
    
    # Запускаем пример в соответствии с выбранным режимом
    if args.mode == "text":
        extract_text_example(args.pdf_path, args.output)
    elif args.mode == "tables":
        extract_tables_example(args.pdf_path, args.output)
    elif args.mode == "full":
        full_analysis_example(args.pdf_path, args.output)
        
    return 0


if __name__ == "__main__":
    sys.exit(main()) 