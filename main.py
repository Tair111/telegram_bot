import asyncio
import logging
import sys
import sqlite3
import requests
import json


from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = "7254987749:AAFO94pcp2DPNrvyICeJXaEZuAEzIzUgiAg"
API_Weather = "5dd749b2f141ddbfd300a8b434132de1"

dp = Dispatcher()


class Form(StatesGroup):
    name = State()
    age = State()


class City(StatesGroup):
    name = State()


def create_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text='Выбор 1', callback_data='vybor_1'),
         InlineKeyboardButton(text='Выбор 2', callback_data='vybor_2'),
         ],
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=buttons,
    )


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Добро пожаловать в наш бот!", reply_markup=create_keyboard())


@dp.message(F.photo)
async def photo_handler(message: Message) -> None:
    photo_data = message.photo[-1]
    await message.answer(f'Размер картинки {photo_data.width} x {photo_data.height} пикселей')


@dp.callback_query(F.data == "vybor_1")
async def vybor_1_callback(callback: CallbackQuery):
    await callback.message.edit_text('Выбор 1') \


@dp.callback_query(F.data == "vybor_2")
async def vybor_2_callback(callback: CallbackQuery):
    await callback.message.edit_text('Выбор 2')


@dp.message(Command('help'))
async def command_help_handler(message: Message) -> None:
    await message.answer(f'Доступные команды: /start, /help, /echo, /photo')


@dp.message(Command('register'))
async def command_register_handler(message: Message, state: FSMContext) -> None:
    try:
        conn = sqlite3.connect('tg.sql')
        cur = conn.cursor()
        cur.execute(
            'CREATE TABLE IF NOT EXISTS users (id int auto_increment primary key, user_id int UNIQUE, name varchar(50), age int)')
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        print('База не создана')

    await message.answer(f'Регистрация пользователя. Введите имя: ')
    await state.set_state(Form.name)


@dp.message(Form.name)
async def process_name(message: Message, state: FSMContext) -> None:
    name = message.text
    await state.update_data(name=name)
    await state.set_state(Form.age)
    await message.answer(f'Введите возраст: ')


@dp.message(Form.age)
async def process_age(message: Message, state: FSMContext) -> None:
    age = message.text
    await state.update_data(age=age)
    current_state = await state.get_data()
    await state.clear()
    user_id = message.from_user.id

    try:
        conn = sqlite3.connect('tg.sql')
        cur = conn.cursor()
        cur.execute("INSERT INTO users (user_id, name, age) VALUES ('%s', '%s', '%s')"
                    % (user_id, current_state['name'], current_state['age']))
        conn.commit()
        cur.close()
        conn.close()

        await message.answer(f'Данные записаны {current_state}')
    except Exception as ex:
        print(ex)
        await message.answer(f'Такой пользователь уже зарегистрирован')


@dp.message(Command('users'))
async def command_register_handler(message: Message) -> None:
    conn = sqlite3.connect('tg.sql')
    cur = conn.cursor()
    cur.execute('SELECT * FROM users')
    users = cur.fetchall()
    cur.close()
    conn.close()

    info = ''
    for el in users:
        info += f'Имя: {el[2]}, возраст {el[3]}, user_id {el[1]}\n'

    await message.answer(f'В базе зарегистрированы следующие люди {info}')


@dp.message(Command('weather'))
async def command_weather_handler(message: Message, state: FSMContext) -> None:
    await message.answer(f'В каком городе хотите узнать погоду?')
    await state.set_state(City.name)


@dp.message(City.name)
async def get_weather(message: Message, state: FSMContext):
    city = message.text
    await state.update_data(city=city)
    await state.clear()
    try:
        res = requests.get(
            f'https://api.openweathermap.org/data/2.5/find?q={city}&type=like&APPID={API_Weather}&units=metric')
        data = json.loads(res.text)
        term = data['list'][1]['main']['temp']
        await message.answer(f'Сейчас в {city} температура {term} градусов')
    except Exception as ex:
        print(ex)
        await message.answer(f'Неудалось узнать погоду в {city}')


async def schedule_handler(bot: Bot) -> None:
    try:
        conn = sqlite3.connect('tg.sql')
        cur = conn.cursor()
        cur.execute('SELECT * FROM users')
        users = cur.fetchall()
        cur.close()
        conn.close()

        for el in users:
            user_id = f'{el[1]}'
            await bot.send_message(user_id, f'Не забудьте проверить уведомления!')
    except Exception as ex:
        print(ex)


@dp.message(F.text)
async def echo_handler(message: Message) -> None:
    await message.reply(message.text)


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    scheduler_task = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler_task.add_job(schedule_handler, 'cron', hour='9', minute='00', kwargs={'bot': bot})
    scheduler_task.start()

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        logging.basicConfig(level=logging.INFO, stream=sys.stdout)
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')
