import json
import logging
import os
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup

from constants import MONTHS
from utils import get_schedule

# Логирование.
logger = logging.getLogger(__name__)
BOSS_LIST = json.loads(os.environ['BOSS_LIST'])


def create_notification_list():
    """Создаем список пользователей, у кого завтра смена или дежурство."""
    today = datetime.now().day  # Например: 15
    next_day = datetime.now() + timedelta(days=1)  # Например: 16
    current_month_num = str(datetime.now().month)
    current_month = MONTHS.get(current_month_num)

    # Получаем название следующего месяца.
    if current_month_num == '12':
        next_month = MONTHS['1']  # Январь
    else:
        next_month_num = str(int(current_month_num) + 1)
        next_month = MONTHS[next_month_num]

    # Получаем график:
    schedule = get_schedule(current_month)
    # Если последний день месяца, то берем график следующего месяца.
    if today >= 28 and next_day.day == 1:
        schedule = get_schedule(next_month)

    # Создаем список пользователей, у кого завтра смена:
    next_day_gain_list = []
    for user_name, value in schedule.items():
        for gain in value['смена']:
            if next_day.day in gain:
                next_day_gain_list.append(user_name)

    # Создаем список пользователей, у кого завтра дежурство:
    next_day_duty_list = []
    for user_name, value in schedule.items():
        for duty in value['дежурство']:
            if next_day.day in duty:
                next_day_duty_list.append((user_name, duty))

    return next_day_gain_list, next_day_duty_list


def parse_weather_notification():
    """Парсим сайт погоды."""
    url = 'https://www.gismeteo.ru/weather-shkotovo-189197/'
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            logging.error(
                f'Ошибка при получении страницы: {response.status_code}')
            return None

        soup = BeautifulSoup(response.text, 'lxml')
        # Получаем состояние погоды.
        weather_elements = soup.find_all('div', class_='row-item')
        weather = []

        for elem in weather_elements:
            condition = elem.get('data-tooltip')
            if condition:
                weather.append(condition)
        weather_list = weather[0:8]

        # Получаем температуру.
        temperature_widget = soup.find(
            'div',
            'widget-row widget-row-chart widget-row-chart-temperature-air'
            ' row-with-caption')
        temperature_widget_values = temperature_widget.find(
            'div', 'values')
        temperatures_list = []  # Для заполнения температурами.
        for widget_value in temperature_widget_values:
            temperature_value = widget_value.find('temperature-value')
            if temperature_value:
                temperature = temperature_value.get('value')
                temperatures_list.append(temperature)

        if weather_list and temperatures_list:
            logging.info('Данные о погоде успешно извлечены.')
            return weather_list[2:], temperatures_list[2:]

    except Exception as e:
        logging.error(f'Возникла ошибка: {e}')
        return None
