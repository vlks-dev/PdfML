"""
Модуль для визуализации результатов
"""

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from PIL import Image, ImageDraw, ImageFont, ImageColor
import os
import random


def visualize_layout(image, layout_data, colors=None):
    """
    Визуализация распознанного макета PDF-страницы.
    
    Args:
        image (PIL.Image): Изображение страницы
        layout_data (list): Список элементов макета
            [{"category": "Text", "bbox": [x1, y1, x2, y2], "score": 0.95}, ...]
        colors (dict): Словарь с цветами для разных категорий
        
    Returns:
        PIL.Image: Изображение с визуализацией
    """
    # Копируем изображение, чтобы не изменять оригинал
    img = image.copy()
    draw = ImageDraw.Draw(img)
    
    # Определяем цвета по умолчанию для категорий
    if colors is None:
        colors = {
            "Text Blocks": "#3498db",  # синий
            "Titles": "#e74c3c",       # красный
            "Lists": "#2ecc71",        # зеленый
            "Tables": "#f39c12",       # оранжевый
            "Figures": "#9b59b6"       # фиолетовый
        }
    
    # Для неуказанных категорий генерируем случайный цвет
    for item in layout_data:
        category = item["category"]
        if category not in colors:
            colors[category] = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    
    # Рисуем рамки и подписи
    for item in layout_data:
        category = item["category"]
        bbox = item["bbox"]
        score = item.get("score", 1.0)
        
        color = colors[category]
        
        # Рисуем рамку
        draw.rectangle(
            [(bbox[0], bbox[1]), (bbox[2], bbox[3])],
            outline=color,
            width=3
        )
        
        # Добавляем подпись
        label = f"{category}: {score:.2f}" if score is not None else category
        draw.text((bbox[0] + 5, bbox[1] + 5), label, fill=color)
    
    return img


def visualize_entities(text, entities, output_path=None, highlight_colors=None):
    """
    Визуализация найденных именованных сущностей в тексте.
    
    Args:
        text (str): Исходный текст
        entities (list): Список найденных сущностей
        output_path (str): Путь для сохранения HTML-файла
        highlight_colors (dict): Словарь с цветами для разных типов сущностей
        
    Returns:
        str: HTML-код с визуализацией
    """
    if not entities:
        return f"<p>{text}</p>"
        
    # Определяем цвета по умолчанию для типов сущностей
    if highlight_colors is None:
        highlight_colors = {
            "PERSON": "#ffcccc",       # светло-красный
            "ORG": "#ccffcc",          # светло-зеленый
            "GPE": "#ccccff",          # светло-синий
            "LOC": "#ccccff",          # светло-синий
            "DATE": "#ffffcc",         # светло-желтый
            "TIME": "#ffffcc",         # светло-желтый
            "MONEY": "#ffccff",        # светло-фиолетовый
            "PERCENT": "#ffccff",      # светло-фиолетовый
            "PRODUCT": "#ccffff",      # светло-голубой
            "EVENT": "#ffeecc",        # светло-оранжевый
            "WORK_OF_ART": "#eeccff",  # светло-лиловый
            "LAW": "#eeffcc",          # светло-желто-зеленый
            "LANGUAGE": "#cceeff",     # светло-голубой
            "PER": "#ffcccc",          # светло-красный (alias для PERSON)
            "NRP": "#ccffcc",          # светло-зеленый (alias для ORG)
            "MISC": "#ccffff"          # светло-голубой
        }
    
    # Сортируем сущности по начальной позиции
    sorted_entities = sorted(entities, key=lambda x: x["start_char"])
    
    # Создаем HTML для визуализации
    html = []
    last_end = 0
    
    for entity in sorted_entities:
        start = entity["start_char"]
        end = entity["end_char"]
        label = entity["label"]
        
        # Текст до сущности
        if start > last_end:
            html.append(text[last_end:start])
        
        # Определяем цвет для типа сущности
        color = highlight_colors.get(label, "#cccccc")  # серый по умолчанию
        
        # Отображаем сущность с подсветкой и всплывающей подсказкой
        entity_text = text[start:end]
        html.append(f'<mark style="background-color: {color};" title="{label}">{entity_text}</mark>')
        
        last_end = end
    
    # Добавляем оставшийся текст
    if last_end < len(text):
        html.append(text[last_end:])
    
    # Собираем полный HTML
    result = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Распознанные сущности</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }}
            .legend {{ margin-bottom: 20px; }}
            .legend span {{ display: inline-block; margin-right: 15px; }}
            .legend .color-box {{ display: inline-block; width: 15px; height: 15px; margin-right: 5px; vertical-align: middle; }}
        </style>
    </head>
    <body>
        <div class="legend">
            <h3>Типы сущностей:</h3>
            {"".join([f'<span><span class="color-box" style="background-color: {color};"></span>{label}</span>' for label, color in highlight_colors.items() if any(e["label"] == label for e in entities)])}
        </div>
        <div class="text">
            {"".join(html)}
        </div>
    </body>
    </html>
    """
    
    # Сохраняем HTML, если указан путь
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
    
    return result


def visualize_table(df, output_path=None):
    """
    Визуализация таблицы в виде HTML.
    
    Args:
        df (pandas.DataFrame): Таблица для визуализации
        output_path (str): Путь для сохранения HTML-файла
        
    Returns:
        str: HTML-код с таблицей
    """
    table_html = df.to_html(classes='dataframe', border=1, index=False)
    
    result = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Таблица</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; }}
            table.dataframe {{ border-collapse: collapse; margin: 10px 0; width: 100%; }}
            table.dataframe th {{ background-color: #f2f2f2; }}
            table.dataframe th, table.dataframe td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            table.dataframe tr:nth-child(even) {{ background-color: #f9f9f9; }}
            table.dataframe tr:hover {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h2>Извлеченная таблица</h2>
        {table_html}
    </body>
    </html>
    """
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(result)
    
    return result 