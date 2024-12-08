from ftplib import FTP
import pandas as pd
from io import BytesIO
import tempfile
import os
from datetime import datetime
from logger_config import setup_logger
from dotenv import load_dotenv

load_dotenv()

logger = setup_logger('ftp_excel_reader')

class FTPExcelReader:
    def __init__(self):
        self.host = os.getenv("FTP_HOST")
        self.username = os.getenv("FTP_USERNAME")
        self.password = os.getenv("FTP_PASSWORD")
        self.filename = os.getenv("FTP_FILENAME")
        logger.info("Инициализирован FTPExcelReader")

    def download_excel(self):
        """Скачивает Excel файл с FTP сервера"""
        logger.info("Начало загрузки файла с FTP")
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as temp_file:
                with FTP(self.host) as ftp:
                    logger.info(f"Подключение к FTP серверу: {self.host}")
                    ftp.login(user=self.username, passwd=self.password)

                    logger.debug(f"Текущая директория: {ftp.pwd()}")
                    files = ftp.nlst()
                    logger.debug(f"Список файлов: {files}")

                    with BytesIO() as bio:
                        try:
                            logger.info(f"Попытка скачать файл: {self.filename}")
                            ftp.retrbinary(f"RETR {self.filename}", bio.write)
                            bio.seek(0)
                            temp_file.write(bio.read())
                            logger.info(f"Файл {self.filename} успешно скачан")
                        except Exception as e:
                            logger.warning(f"Ошибка при скачивании основного файла: {str(e)}")
                            excel_files = [f for f in files if f.endswith(".xlsx")]

                            if excel_files:
                                logger.info(f"Найдены альтернативные Excel файлы: {excel_files}")
                                self.filename = excel_files[0]
                                ftp.retrbinary(f"RETR {self.filename}", bio.write)
                                bio.seek(0)
                                temp_file.write(bio.read())
                                logger.info(f"Альтернативный файл {self.filename} успешно скачан")
                            else:
                                logger.error(f"Excel файлы не найдены. Доступные файлы: {files}")
                                raise Exception(f"Excel файлы не найдены. Доступные файлы: {files}")

                return temp_file.name

        except Exception as e:
            logger.error(f"Ошибка при скачивании файла с FTP: {str(e)}")
            raise

    def _convert_date(self, date_str):
        """Конвертирует строку даты в нужный формат"""
        if pd.isna(date_str):
            return None

        if isinstance(date_str, (pd.Timestamp, datetime)):
            return date_str

        logger.debug(f"Попытка конвертации даты: {date_str}")
        try:
            # Если это строка из Google таблицы (2024-06-19 11:25:42)
            if isinstance(date_str, str) and len(date_str) == 19 and date_str[4] == '-':
                try:
                    return pd.to_datetime(date_str, format='%Y-%m-%d %H:%M:%S')
                except:
                    pass

            # Если это строка из Excel (12/8/2024 9:42:48 AM)
            if isinstance(date_str, str) and 'AM' in date_str.upper() or 'PM' in date_str.upper():
                try:
                    # Преобразуем 12-часовой формат в 24-часовой
                    return pd.to_datetime(date_str, format='%m/%d/%Y %I:%M:%S %p')
                except:
                    pass

            # Пробуем другие форматы
            date_formats = [
                '%d.%m.%Y %H:%M:%S',     # 08.12.2024 09:37:03
                '%Y-%m-%d %H:%M:%S',     # 2024-12-08 09:37:03
                '%m/%d/%Y %H:%M:%S',     # 12/8/2024 09:37:03
            ]

            for date_format in date_formats:
                try:
                    return datetime.strptime(date_str, date_format)
                except ValueError:
                    continue

            # Если ни один формат не подошел, пробуем автоматическое определение
            try:
                return pd.to_datetime(date_str)
            except:
                logger.error(f"Не удалось преобразовать дату: {date_str}")
                raise ValueError(f"Неподдерживаемый формат даты: {date_str}")

        except Exception as e:
            logger.error(f"Ошибка при конвертации даты '{date_str}': {str(e)}")
            raise

    def _normalize_branch_name(self, branch_name):
        """Нормализует названия филиалов"""

        if not isinstance(branch_name, str):

            return branch_name

        # Словарь соответствия названий

        branch_mapping = {
            "нохияи Спитамен": "Спитамен",
            "нохиаи Спитамен": "Спитамен",
            "нохияи Ч. Расулов": "Ч. Расулов",
            "нохиаи Ч. Расулов": "Ч. Расулов",
            "шахри Панчакент": "Панчакент",
            "шаҳри Панчакент": "Панчакент",
        }

        # Приводим к нижнему регистру для поиска

        branch_name_lower = branch_name.lower()

        # Ищем соответствие в маппинге

        for key, value in branch_mapping.items():

            if key.lower() in branch_name_lower:

                return value

        return branch_name

    def read_excel(self):
        """Читает и обрабатывает Excel файл"""
        logger.info("Начало чтения Excel файла")
        try:
            temp_file_path = self.download_excel()
            logger.info(f"Временный файл создан: {temp_file_path}")

            if not os.path.exists(temp_file_path):
                logger.error("Временный файл не создан")
                raise Exception("Временный файл не создан")

            file_size = os.path.getsize(temp_file_path)
            logger.info(f"Размер файла: {file_size} байт")

            if file_size == 0:
                logger.error("Скачанный файл пуст")
                raise Exception("Скачанный файл пуст")

            df = pd.read_excel(temp_file_path)
            logger.info(f"Прочитано строк: {len(df)}")
            logger.debug(f"Колонки: {df.columns.tolist()}")

            # Переименовываем колонки
            column_mapping = {
                "Дата": "Дата",
                "Номер": "Номер",
                "Организация": "Филиал",
                "Партнер": "Клиент",
            }

            df = df.rename(columns=column_mapping)

            # Конвертируем даты
            logger.info("Конвертация дат...")
            try:
                # Сначала пробуем прямое преобразование
                df["Дата"] = pd.to_datetime(df["Дата"])
            except Exception as e:
                logger.warning(f"Не удалось напрямую преобразовать даты: {str(e)}")
                try:
                    # Если не получилось, пробуем через apply
                    df["Дата"] = df["Дата"].apply(self._convert_date)
                    logger.info("Даты успешно преобразованы через _convert_date")
                except Exception as e:
                    logger.error(f"Ошибка при преобразовании дат через _convert_date: {str(e)}")
                    raise

            # Проверяем успешность конвертации
            if not pd.api.types.is_datetime64_any_dtype(df["Дата"]):
                logger.error("Не удалось преобразовать колонку 'Дата' в datetime")
                raise ValueError("Не удалось преобразовать даты в правильный формат")

            logger.info(f"Тип данных колонки 'Дата': {df['Дата'].dtype}")
            logger.debug(f"Пример даты после конвертации: {df['Дата'].iloc[0] if len(df) > 0 else 'нет данных'}")

            # Нормализуем названия филиалов
            logger.info("Нормализация названий филиалов...")
            df["Филиал"] = df["Филиал"].apply(self._normalize_branch_name)

            logger.info("Обработка данных завершена")

            try:
                os.unlink(temp_file_path)
                logger.info("Временный файл удален")
            except Exception as e:
                logger.warning(f"Ошибка при удалении временного файла: {str(e)}")

            return df

        except Exception as e:
            logger.error(f"Ошибка при чтении Excel файла: {str(e)}")
            raise
