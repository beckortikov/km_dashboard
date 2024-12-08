import json
from datetime import datetime, timedelta
import os
import pandas as pd
from logger_config import setup_logger

logger = setup_logger('cache_manager')

class CacheManager:
    def __init__(self, cache_file="cache/yesterday_data.json"):
        self.cache_file = cache_file
        try:
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            logger.info(f"Инициализирован CacheManager с файлом: {cache_file}")
        except Exception as e:
            logger.error(f"Ошибка при создании директории кэша: {str(e)}")
            raise

    def save_data(self, data):
        """Сохраняет данные за текущий день как вчерашние"""
        try:
            logger.info("Начало сохранения данных в кэш")

            def convert_timestamps(obj):
                if isinstance(obj, (pd.Timestamp, datetime)):
                    return obj.strftime('%Y-%m-%d %H:%M:%S')
                if isinstance(obj, pd.Series):
                    return obj.to_dict()
                if isinstance(obj, pd.DataFrame):
                    return obj.to_dict(orient='records')
                return obj

            # Преобразуем DataFrame в словарь
            if isinstance(data, pd.DataFrame):
                data = data.to_dict(orient='list')

            # Конвертируем все временные метки
            processed_data = {}
            for key, value in data.items():
                if isinstance(value, list):
                    processed_data[key] = [convert_timestamps(item) for item in value]
                else:
                    processed_data[key] = convert_timestamps(value)

            cache_data = {
                'date': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'data': processed_data
            }

            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False)

            logger.info("Данные успешно сохранены в кэш")

        except Exception as e:
            logger.error(f"Ошибка при сохранении данных в кэш: {str(e)}")
            raise

    def get_yesterday_data(self):
        """Получает данные за вчерашний день из кэша"""
        try:
            logger.info("Попытка получения данных из кэша")

            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                cache_date = datetime.strptime(cache_data['date'], '%Y-%m-%d').date()
                yesterday = (datetime.now() - timedelta(days=1)).date()

                if cache_date == yesterday:
                    logger.info("Найдены актуальные данные в кэше")
                    data = cache_data['data']
                    # Преобразуем строки дат обратно в datetime
                    if 'Дата' in data:
                        try:
                            data['Дата'] = [pd.to_datetime(d) if d is not None else None for d in data['Дата']]
                            logger.info("Даты успешно преобразованы в datetime")
                        except Exception as e:
                            logger.error(f"Ошибка при преобразовании дат: {str(e)}")
                            # Если не удалось преобразовать даты, возвращаем None
                            return None
                    return data
                else:
                    logger.info(f"Данные в кэше устарели. Дата кэша: {cache_date}, требуется: {yesterday}")
                    return None

        except FileNotFoundError:
            logger.warning("Файл кэша не найден")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка декодирования JSON: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Непредвиденная ошибка при получении данных из кэша: {str(e)}")
            return None