import json
import logging
import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from constants import (
    DUTY_EMOJI,
    GAIN_EMOJI,
    MONTHS,
    VACATION_EMOJI,
    WEATHER_TIMES
)
from notification import create_notification_list, parse_weather_notification
from utils import get_schedule

load_dotenv()
DEPARTMENT = json.loads(os.environ['DEPARTMENT_IDS'])
BOSS_LIST = json.loads(os.environ['BOSS_LIST'])


def create_gain_message(user_id) -> str:
    """Создаем сообщение по сменам."""
    today = datetime.now().day
    current_month = MONTHS.get(str(datetime.now().month))
    schedule = get_schedule(current_month)

    # Получаем Ф.И.О пользователя, который написал боту:
    user_name = DEPARTMENT.get(str(user_id))
    user_gains = []
    if schedule:
        user_gains = schedule[user_name]['смена']
        boss_gains = {}  # Создали словарь смен босов.
        for boss in BOSS_LIST:
            boss_gains[boss] = schedule[boss]['смена']
    else:
        message = f'График на {current_month} не загружен'
        return message

    # Составляем сообщение:
    future_gains = False  # Флаг для определения будущих смен.
    message = f'{GAIN_EMOJI} Cмены на {current_month}:\n'

    if user_gains:
        for [date, weekday] in user_gains:
            formated_date = f'- {int(date)} ({weekday}) '

            if int(date) >= today:  # Прошедшие дни не учитываем.
                future_gains = True
                message += f'\n{formated_date}, ответственный: '
                for boss, gains in boss_gains.items():
                    if [date, weekday] in gains:
                        message += f'{boss}, '
                # Убираем: ", " у крайнего ответственного.
                message = message[:-2]

    else:
        future_gains = False

    if not future_gains:
        message += '✅ закончились.'
    return message


def create_duty_message(user_id) -> str:
    """Создаем сообщение по дежурствам."""
    today = datetime.now().day
    current_month = MONTHS.get(str(datetime.now().month))
    schedule = get_schedule(current_month)

    # Получаем Ф.И.О пользователя, который написал боту:
    user_name = DEPARTMENT.get(str(user_id))
    user_duties = []
    if schedule:
        user_duties = schedule[user_name]['дежурство']
    else:
        message = f'График на {current_month} не загружен'
        return message

    # Составляем сообщение:
    future_duties = False  # Флаг для определения будущих смен.
    message = f'{DUTY_EMOJI} Дежурства на {current_month}:\n\n'

    if user_duties:
        for (date, weekday, time) in user_duties:
            formated_date = f'- {int(date)} ({weekday}), {time} '

            if int(date) >= today:  # Прошедшие дни не учитываем.
                future_duties = True
                message += f'{formated_date}\n'
    else:
        future_duties = False

    if not future_duties:
        message += '✅ закончились.'
    return message


def create_vacation_message(user_id) -> str:
    """Создаем сообщение с информацией об отпуске."""
    current_month = MONTHS.get(str(datetime.now().month))
    schedule = get_schedule(current_month)

    # Получаем Ф.И.О пользователя, который написал боту:
    user_name = DEPARTMENT.get(str(user_id))
    if schedule:
        user_vacation = schedule[user_name]['отпуск']
    else:
        message = f'График на {current_month} не загружен'
        return message

    # Формируем сообщение:
    message = str()
    if not user_vacation:
        message += f'{current_month}: 😔 отпуска нет.'
    else:
        for vacation in user_vacation:
            message += f'{VACATION_EMOJI} {vacation.capitalize()}\n'

    return message


def create_month_message(user_id, month):
    """
    Создаем сообщение с графиком текущего месяца.
    """
    schedule = get_schedule(month)  # Получаем график.
    if not schedule:
        message = f'График на {month} еще не подготовлен'
        return message

    # Получаем Ф.И.О пользователя, который написал боту:
    user_name = DEPARTMENT.get(str(user_id))
    user_shedule = schedule[user_name]

    message = f'График на {month}:\n'

    # Перебираем смены:
    gain_list = user_shedule['смена']
    if gain_list:
        message += f'\n{GAIN_EMOJI} Cмены:\n'
        for (date, weekday) in gain_list:
            formated_date = f'- {int(date)} ({weekday}) '
            message += f'{formated_date}\n'
    else:
        message += f'{GAIN_EMOJI} Cмены:✅ отсутствуют\n\n'

    # Перебираем дежурства:
    duty_list = user_shedule['дежурство']
    if duty_list:
        message += f'\n{DUTY_EMOJI} Дежурства:\n'
        for (date, weekday, time) in duty_list:
            formated_date = f'- {int(date)} ({weekday}), {time} '
            message += f'{formated_date}\n'
    else:
        message += f'\n{DUTY_EMOJI} Дежурства:✅ отсутствуют\n'

    # Перебираем отпуска:
    vacation_list = user_shedule['отпуск']
    if vacation_list:
        for vacation in vacation_list:
            message += f'\n{VACATION_EMOJI} {vacation.capitalize()}\n'
    else:
        message += '\n😔 отпуска нет.'

    return message


def create_gain_notification_message():
    """
    Создаем сообщение для уведомления о смене.
    """
    next_day = datetime.now() + timedelta(days=1)  # Например: 16
    next_day_format = next_day.strftime('%d.%m.%Y')  # Например: 16.04.2025
    # Получаем список у кого завтра смена.
    user_list, _ = create_notification_list()

    # Cообщение c ответственным:
    boss_list = []
    employee_list = []
    for user in user_list:
        if user in BOSS_LIST:
            boss_list.append(user)
        else:
            employee_list.append(user)
    message_with_boss = ', '.join(boss_list)

    # Основное сообщение:
    message = (f'{GAIN_EMOJI} Завтра {next_day_format}\n\n'
               'Cмена у следующих лиц:\n')
    message += '\n'.join(f'- {name}' for name in employee_list)
    message += f'\n\nОтветственный: {message_with_boss}'
    return message, user_list


def create_duty_notification_message():
    """
    Создаем сообщение для уведомления о дежурстве.
    """
    next_day = datetime.now() + timedelta(days=1)  # Например: 16
    next_day_format = next_day.strftime('%d.%m.%Y')  # Например: 16.04.2025
    # Получаем список у кого завтра дежурство.
    _, user_list = create_notification_list()

    # Основное сообщение:
    message = (f'{DUTY_EMOJI} Завтра {next_day_format}\n\n '
               'У тебя запланировано дежурство: ')
    return message, user_list


def create_weather_notification_message():
    """
    Создаем сообщение для уведомления о погоде.
    """
    today = datetime.now().strftime("%d.%m.%Y")

    weather_list, temperatures_list = parse_weather_notification()
    message = ''
    if weather_list and temperatures_list:
        message = (
            f'Сегодня: {today}\n\n'
            '💫Погода за окном:\n\n'
        )

        for index in range(len(WEATHER_TIMES)):
            time = WEATHER_TIMES[index]
            description = weather_list[index]
            temperature = temperatures_list[index]
            temperature_mess = f't={temperature} °C'
            # Редактируем вывод информации в тлг.
            if len(temperature_mess) == 6:
                temperature_mess += '   '
            elif len(temperature_mess) == 7:
                temperature_mess += ' '
            message += (
                f'{time}:        {temperature_mess}       {description}\n'
            )

    return message
