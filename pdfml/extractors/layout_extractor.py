"""
Модуль для распознавания макета PDF-документа
"""

import cv2
import numpy as np
import fitz
from PIL import Image
import layoutparser as lp

from ..utils.logger import get_logger
from ..utils.visualization import visualize_layout

logger = get_logger(__name__)


class LayoutExtractor:
    """
    Класс для распознавания макета PDF-документа и извлечения
    структурированных элементов (текст, таблицы, изображения).
    """
    
    def __init__(self, model_type="detectron2"):
        """
        Инициализация экстрактора макета.
        
        Args:
            model_type (str): Тип модели для распознавания макета.
                Поддерживаемые значения: "detectron2", "paddleocr"
        """
        self.model_type = model_type
        self.model = self._load_model(model_type)
        
    def _load_model(self, model_type):
        """
        Загрузка модели для распознавания макета.
        
        Args:
            model_type (str): Тип модели
            
        Returns:
            Модель Layout Parser
        """
        try:
            if model_type == "detectron2":
                # Используем предобученную модель для распознавания макета
                model = lp.Detectron2LayoutModel( # TODO: Нет такого класса, как правильно использовать Detectron2LayoutModel?
                    'lp://PubLayNet/mask_rcnn_X_101_32x8d_FPN_3x/config',
                    extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.8],
                    label_map={
                        0: "Text",
                        1: "Title",
                        2: "List",
                        3: "Table",
                        4: "Figure"
                    }
                )
                logger.info("Загружена модель Detectron2 для распознавания макета")
                return model
            elif model_type == "paddleocr":
                # Альтернативный вариант с использованием PaddleOCR
                model = lp.PaddleDetectionLayoutModel(config_path="lp://PubLayNet/ppyolov2_r50vd_dcn_365e/config",
                                                  threshold=0.5,
                                                  label_map={
                                                      0: "Text",
                                                      1: "Title",
                                                      2: "List",
                                                      3: "Table",
                                                      4: "Figure"
                                                  })
                logger.info("Загружена модель PaddleOCR для распознавания макета")
                return model
            else:
                raise ValueError(f"Неподдерживаемый тип модели: {model_type}")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}")
            raise
    
    def extract_layout(self, page, return_image=False):
        """
        Распознавание макета страницы.
        
        Args:
            page: Страница PDF (объект PyMuPDF)
            return_image (bool): Возвращать ли также изображение страницы
            
        Returns:
            dict: Словарь с распознанными элементами макета
            или кортеж (dict, Image), если return_image=True
        """
        # Конвертируем страницу в изображение
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        img_np = np.array(img)
        
        # Распознаем макет
        layout = self.model.detect(img_np)
        
        # Группируем результаты по типам элементов
        result = {
            "text_blocks": [],
            "titles": [],
            "lists": [],
            "tables": [],
            "figures": []
        }
        
        for block in layout:
            # Получаем координаты блока
            bbox = block.block.bbox
            coords = {
                "x1": int(bbox.x_1),
                "y1": int(bbox.y_1),
                "x2": int(bbox.x_2),
                "y2": int(bbox.y_2)
            }
            
            block_type = block.type
            confidence = block.score
            
            # Добавляем блок в соответствующую категорию
            if block_type == "Text":
                result["text_blocks"].append({
                    "coords": coords,
                    "confidence": confidence
                })
            elif block_type == "Title":
                result["titles"].append({
                    "coords": coords,
                    "confidence": confidence
                })
            elif block_type == "List":
                result["lists"].append({
                    "coords": coords,
                    "confidence": confidence
                })
            elif block_type == "Table":
                result["tables"].append({
                    "coords": coords,
                    "confidence": confidence
                })
            elif block_type == "Figure":
                result["figures"].append({
                    "coords": coords,
                    "confidence": confidence
                })
        
        if return_image:
            return result, img
        return result
    
    def visualize(self, page, output_path=None):
        """
        Визуализация распознанного макета.
        
        Args:
            page: Страница PDF (объект PyMuPDF)
            output_path (str): Путь для сохранения визуализации
            
        Returns:
            Image: Визуализация макета
        """
        result, img = self.extract_layout(page, return_image=True)
        
        # Подготовка данных для визуализации
        layout_data = []
        for category, blocks in result.items(): # TODO: Нет такого атрибута items
            for block in blocks:
                coords = block["coords"]
                layout_data.append({
                    "category": category.replace("_", " ").title(),
                    "bbox": [coords["x1"], coords["y1"], coords["x2"], coords["y2"]],
                    "score": block["confidence"]
                })
        
        # Визуализация
        viz_img = visualize_layout(img, layout_data)
        
        if output_path:
            viz_img.save(output_path)
            
        return viz_img 