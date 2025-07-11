import json
import logging
import os
import threading
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from telebot import TeleBot
from telebot.types import KeyboardButton, ReplyKeyboardMarkup

from constants import (
    CURRENT_MONTH,
    DUTY_EMOJI,
    GAIN_EMOJI,
    MONTHS,
    NEXT_MONTH,
    NOTIFICATION_TIME,
    VACATION_EMOJI,
    WEATHER_NOTIFICATION_TIME
)
from message import (
    create_duty_message,
    create_duty_notification_message,
    create_gain_message,
    create_gain_notification_message,
    create_month_message,
    create_vacation_message,
    create_weather_notification_message
)
from utils import check_department

load_dotenv()
bot_token = os.getenv('TOKEN')
bot = TeleBot(bot_token)

GROUP_ID = os.getenv('GROUP_CHAT_ID')
DEPARTMENT = json.loads(os.environ['DEPARTMENT_IDS'])
exit_flag = False  # Флаг для остановки потоков.


def create_keyboard():
    """
    Оформление клавиатуры.
    Параметр exlude - строка с названием кнопки, которую надо исключить.
    """
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    button_gain = KeyboardButton(GAIN_EMOJI)
    button_duty = KeyboardButton(DUTY_EMOJI)
    button_vacation = KeyboardButton(VACATION_EMOJI)
    button_current_month = KeyboardButton(CURRENT_MONTH)
    button_next_month = KeyboardButton(NEXT_MONTH)
    keyboard.row(button_gain, button_duty, button_vacation)
    keyboard.row(button_current_month, button_next_month)

    return keyboard


@bot.message_handler(commands=['start'])
def start_command(message):
    """Вывод сообщения и создание клавиатуры, если пользователь "одобрен"."""
    # Если сообщение пришло из группы.
    if message.chat.type in ['group', 'supergroup']:
        group_id = message.chat.id
        response = (
            'Привет! 👋\n'
            '🤖: Мои возможности в групповом чате ограничены.\n\n'
            '⏱️ Если завтра на работу, то пришлю тебе уведомление '
            f'в {NOTIFICATION_TIME.strftime("%H:%M")}\n'
            f'⏱️ Утром, в {WEATHER_NOTIFICATION_TIME.strftime("%H:%M")} '
            'пришлю текущую погоду.\n\n'
            'Чтобы посмотреть личную информацию из графика,\n'
            'напишите мне в личном сообщении: 📲 @grafik_4o_bot'
        )
        bot.send_message(group_id, response)
    # Если сообщение написано лично боту.
    elif message.chat.type == 'private':
        user_id = message.chat.id
        if check_department(user_id):
            response = (
                '👋 Добро пожаловать в главный интерфейс бота.\n\n'

                'Вот список доступных команд:\n'
                f'- {GAIN_EMOJI} Узнать когда будущие смены\n'
                f'- {DUTY_EMOJI} Посмотреть данные о планируемом дежурстве\n'
                f'- {VACATION_EMOJI} Проверить наличие отпуска в этом месяце\n'
                f'- {CURRENT_MONTH} Увидеть свой график на текущий месяц\n'
                f'- {NEXT_MONTH} И на следующий месяц, если он подготовлен\n'
            )
            bot.send_message(user_id, response, reply_markup=create_keyboard())
        else:
            bot.send_message(
                user_id,
                text=(
                    'Этот 🤖 бот доступен только ограниченному кругу лиц.'
                    'Чтобы тебя авторизовали, обратись к @Zulfat_Gafurzyanov'
                )
            )


@bot.message_handler(func=lambda message: message.text == GAIN_EMOJI)
def get_gain(message):
    """Выдаем данные по сменам."""
    user_id = message.chat.id
    text = create_gain_message(user_id)

    bot.send_message(
        user_id,
        text,
        reply_markup=create_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == DUTY_EMOJI)
def get_duty(message):
    """Выдаем данные по дежурству."""
    user_id = message.chat.id
    text = create_duty_message(user_id)

    bot.send_message(
        user_id,
        text,
        reply_markup=create_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == VACATION_EMOJI)
def get_vacation(message):
    """Выдаем данные по отпуску."""
    user_id = message.chat.id
    text = create_vacation_message(user_id)

    bot.send_message(
        user_id,
        text,
        reply_markup=create_keyboard()
    )


@bot.message_handler(
        func=lambda message: message.text == CURRENT_MONTH)
def get_current_month_info(message):
    """Выдаем всю информацию по текущему месяцу."""
    current_month = MONTHS.get(str(datetime.now().month))
    user_id = message.chat.id
    text = create_month_message(user_id, current_month)

    bot.send_message(
        user_id,
        text,
        reply_markup=create_keyboard()
    )


@bot.message_handler(
        func=lambda message: message.text == NEXT_MONTH)
def get_next_month_info(message):
    """Выдаем всю информацию по следующему месяцу."""
    current_month_num = str(datetime.now().month)
    if current_month_num == '12':
        next_month = MONTHS['1']  # Январь
    else:
        next_month_num = str(int(current_month_num) + 1)
        next_month = MONTHS[next_month_num]

    user_id = message.chat.id
    text = create_month_message(user_id, next_month)

    bot.send_message(
        user_id,
        text,
        reply_markup=create_keyboard()
    )


@bot.message_handler(func=lambda message: True)
def response_for_message(message):
    """Обработчик любого текста от пользователя."""
    bot.send_message(
        message.chat.id,
        '🤖: Я могу отвечать только на команды, которые есть в меню.'
    )


def scheduler_gain_thread():
    """
    Настройка потока на отправку сообщений.

    Уведомление о смене направляется в общую группу.
    Уведомление о дежурстве направляется лично пользователю.
    """
    while not exit_flag:
        now = datetime.now().time()
        # Проверяем, наступило ли время отправки уведомлений
        # о смене или дежурстве.
        if now >= NOTIFICATION_TIME:
            try:
                (gain_message,
                 user_gain_list) = create_gain_notification_message()
                (duty_message,
                 user_duty_list) = create_duty_notification_message()

                # Если есть пользователи, у кого завтра смена:
                if user_gain_list:
                    bot.send_message(
                        GROUP_ID,
                        gain_message
                    )
                    logging.info(
                        f'В группу {GROUP_ID} отправлено '
                        'уведомление о сменах!'
                    )

                # Если есть пользователь, у кого завтра дежурство:
                if user_duty_list:
                    # Ищем его id и направляем сообщение.
                    for user in user_duty_list:
                        message = duty_message
                        for key, value in DEPARTMENT.items():
                            if user[0] == value:
                                user_id = int(key)
                                # Дополнили сообщение о дежурстве: в день/ночь
                                message += user[1][2]
                                bot.send_message(
                                    user_id,
                                    message
                                )
                                logging.info(
                                    f'Пользователю {user_id} отправлено '
                                    'уведомление о дежурстве!'
                                )

            except Exception as e:
                logging.error(f'Ошибка при отправке уведомлений: {e}')

            next_day = datetime.now() + timedelta(days=1)
            # Комбинируем дату и время:
            next_send_time = datetime.combine(
                next_day.date(), NOTIFICATION_TIME)
            # Задержка до следующей проверки (в секундах):
            delay_seconds = (next_send_time - datetime.now()
                             ).total_seconds()
            time.sleep(delay_seconds)

        else:
            # Если время ещё не пришло, делаем паузу перед следующей проверкой.
            time.sleep(1)


def scheduler_weather_thread():
    """Настройка потока на отправку сообщений о погоде."""
    while not exit_flag:
        now = datetime.now().time()
        # Проверяем, наступило ли время отправки информации о погоде.
        if now >= WEATHER_NOTIFICATION_TIME:
            try:
                weather_message = create_weather_notification_message()
                if weather_message:
                    bot.send_message(
                        GROUP_ID,
                        weather_message
                    )
                    logging.info('Уведомление о погоде отправлено')
            except Exception as e:
                logging.error(f'Ошибка при отправке погоды: {e}')

            next_day = datetime.now() + timedelta(days=1)
            # Комбинируем дату и время:
            next_send_time = datetime.combine(
                next_day.date(), WEATHER_NOTIFICATION_TIME)
            # Задержка до следующей проверки (в секундах):
            delay_seconds = (next_send_time - datetime.now()
                             ).total_seconds()
            time.sleep(delay_seconds)
        else:
            # Если время ещё не пришло, делаем паузу перед следующей проверкой.
            time.sleep(1)


def main_polling_thread():
    """Настройка потока на обработку сообщений от пользователей."""
    global exit_flag  # По умолчанию False.
    try:
        while not exit_flag:
            bot.infinity_polling(timeout=20, long_polling_timeout=60)
    except Exception as e:
        logging.error(f'Ошибка polling: {e}')


if __name__ == "__main__":
    bot_dir = os.path.dirname(os.path.abspath(__file__))
    log_path = os.path.join(bot_dir, 'main.log')
    # Настройки логирования:
    logging.basicConfig(
        format=(
            '%(asctime)s - '
            '%(levelname)s - '
            '%(message)s - '
            '%(name)s - '
            '%(funcName)s - '
            '%(lineno)d'
        ),
        level=logging.INFO,
        filename=log_path,
        filemode='w',
        encoding='utf-8',
    )

    # Создание потоков.
    thread_gain_scheduler = threading.Thread(target=scheduler_gain_thread)
    thread_weather_scheduler = threading.Thread(
         target=scheduler_weather_thread)
    thread_polling = threading.Thread(target=main_polling_thread)

    # Формируем демон-потоки, которые будут завершены автоматически.
    thread_gain_scheduler.daemon = True
    thread_weather_scheduler.daemon = True
    thread_polling.daemon = True

    # Запуск потоков.
    thread_gain_scheduler.start()
    thread_weather_scheduler.start()
    thread_polling.start()

    try:
        # Программа ожидает ввода от пользователя для продолжения.
        input('Нажмите Enter для остановки...\n')
    except KeyboardInterrupt:
        pass  # Игнорируем прерывание
    finally:
        # Устанавливаем флаг завершения и ждем завершения потоков.
        exit_flag = True
        # thread_gain_scheduler.join(timeout=5)
        # thread_weather_scheduler.join(timeout=5)
        thread_polling.join(timeout=5)
        logging.info('Работа завершена.')
