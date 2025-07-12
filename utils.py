import json
import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

from constants import DUTY_DAY, DUTY_NIGHT, HOLIDAYS, WEEK_DAYS

load_dotenv()
DEPARTMENT = json.loads(os.environ['DEPARTMENT_IDS'])
# Логирование.
logger = logging.getLogger(__name__)


def check_department(user_id) -> bool:
    """
    Проверяем ID пользователя. Возвращаем - True, eсли он разрешен.
    """
    if str(user_id) in DEPARTMENT.keys():
        return True
    return False


def read_xlsx(month_name) -> list:
    """Считываем данные с xlsx файла."""
    current_year = datetime.now().year
    # Путь к файлу с названием вида "Апрель_2025.xlsx"
    filepath = f'schedule/{month_name}_{current_year}.xlsx'

    try:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f'Файл "{filepath}" не найден.')
        df = pd.read_excel(filepath)
        data = df.to_dict('records')
        logging.info(f'График на: {month_name} успешно прочитан.')
    except FileNotFoundError as fe:
        logging.error(fe)
        return []
    except Exception as e:
        logging.error(e)
    return data


def day_of_the_week(input_date) -> str:
    """Получаем название дня недели."""
    date = datetime.strptime(input_date, '%d.%m.%Y')
    # Получаем номер дня недели (0—6), затем название.
    weekday_number = date.weekday()
    weekday = WEEK_DAYS[weekday_number]
    return weekday


def get_holiday(date) -> bool:
    """Проверяем, является ли дата - праздником."""
    current_month = str(datetime.now().month)
    if int(date) in HOLIDAYS[current_month]:
        return True
    return False


def create_schedule(month_name):
    """
    Создаем график.
    - для смен берем только выходные дни.
    """
    file = read_xlsx(month_name)

    if not file:
        logging.error('График на текущий месяц не загружен')
        return {}
    else:
        # Создаем словарь вида:
        schedule = {row['ФИО']: {'смена': [], 'дежурство': [], 'отпуск': []}
                    for row in file}

        for line in file:
            user_name = line.pop('ФИО')
            for column, value in line.items():
                # Приводим столбец к формату даты.
                # Для дальнейшей проверки дня недели.
                if column.isdigit():
                    column_format = datetime(
                        day=int(column),
                        month=datetime.now().month,
                        year=datetime.now().year,
                    ).strftime('%d.%m.%Y')

                    # Ищем смену:
                    if value == '+':
                        # Получаем день недели.
                        gain_weekday = day_of_the_week(column_format)
                        # Добавляем смену в общий список, если она попадает на:
                        # субботу, воскресенье или праздник:
                        if gain_weekday in WEEK_DAYS[5:] or (
                            get_holiday(column)
                        ):
                            schedule[user_name]['смена'].append(
                                (int(column), gain_weekday))

                    # Ищем дежурства:
                    elif value in (DUTY_NIGHT+DUTY_DAY):
                        duty_weekday = day_of_the_week(column_format)
                        if value in DUTY_NIGHT:
                            duty_time = '🌑 в ночь'
                        else:
                            duty_time = '☀️ в день'
                        schedule[user_name]['дежурство'].append(
                                (int(column), duty_weekday, duty_time))

                    # Ищем отпуск:
                    elif 'отпуск' in str(value):
                        schedule[user_name]['отпуск'].append((value))
                else:
                    continue

        return schedule


def get_schedule(month) -> dict:
    """Записываем график в формате JSON в файл и получаем запрашиваемый."""
    # Проверка наличия файла с графиком.
    current_year = datetime.now().year
    SCHEDULE_FILE = f'schedule/json/{month}_{current_year}.json'

    try:
        # Если файл существует
        if Path(SCHEDULE_FILE).is_file():
            with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
                content = f.read()

                # Если файл пуст, создаём новый график и перезаписываем файл
                if len(content.strip()) == 2:  # len({}) == 2
                    schedule_json = create_schedule(month)
                    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as file:
                        json.dump(
                            schedule_json, file, ensure_ascii=False, indent=4)
                else:
                    # Иначе загружаем имеющийся график
                    schedule_json = json.loads(content)
        else:
            # Если файла нет, создаём новый график и записываем его
            schedule_json = create_schedule(month)
            with open(SCHEDULE_FILE, 'w', encoding='utf-8') as file:
                json.dump(schedule_json, file, ensure_ascii=False, indent=4)

        return schedule_json

    except Exception as e:
        logging.error(f'Ошибка: {e}')

    return {}
