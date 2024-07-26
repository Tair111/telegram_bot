import asyncio
import logging
import sys
import sqlite3
import requests
import json
import aioschedule

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.filters.callback_data import CallbackData
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

TOKEN = "7254987749:AAFO94pcp2DPNrvyICeJXaEZuAEzIzUgiAg"
API_Weather = "5dd749b2f141ddbfd300a8b434132de1"

dp = Dispatcher()


class Form(StatesGroup):
    name = State()
    age = State()


class MyCallback(CallbackData, prefix="my"):
    foo: str
    bar: str


def create_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(
        text="Выбор 1",
        callback_data=MyCallback(foo="Выбор", bar="Выбор 1")
    )
    builder.button(
        text="Выбор 2",
        callback_data=MyCallback(foo="Выбор", bar="Выбор 2")
    )
    return builder.as_markup()


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(f"Добро пожаловать в наш бот!", reply_markup=create_keyboard())


@dp.message(F.photo)
async def photo_handler(message: Message) -> None:
    photo_data = message.photo[-1]
    await message.answer(f'Размер картинки {photo_data.width} x {photo_data.height} пикселей')


@dp.callback_query(MyCallback.filter(F.foo == "Выбор"))
async def my_callback_foo(query: CallbackQuery, callback_data: MyCallback):
    if callback_data.bar == 'Выбор 1':
        await query.message.answer(f'Вы выбрали {callback_data.bar}')
    elif callback_data.bar == 'Выбор 2':
        await query.message.answer(f'Вы выбрали {callback_data.bar}')


@dp.message(Command('help'))
async def command_help_handler(message: Message) -> None:
    await message.answer(f'Доступные команды: /start, /help, /echo, /photo')


@dp.message(Command('register'))
async def command_register_handler(message: Message, state: FSMContext) -> None:
    try:
        conn = sqlite3.connect('tg.sql')
        cur = conn.cursor()
        cur.execute('CREATE TABLE IF NOT EXISTS users (id int auto_increment primary key, user_id int UNIQUE, name varchar(50), age int)')
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
async def process_age(message: Message, bot: Bot, state: FSMContext) -> None:
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
async def command_weather_handler(message: Message, command: CommandObject) -> None:
    city = command.args
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
    conn = sqlite3.connect('tg.sql')
    cur = conn.cursor()
    cur.execute('SELECT * FROM users')
    users = cur.fetchall()
    cur.close()
    conn.close()

    user_id = ''
    for el in users:
        user_id = f'{el[1]}'
    await bot.send_message(user_id, f'Не забудьте проверить уведомления!')


async def scheduler(bot: Bot):
    aioschedule.every().minutes.do(schedule_handler, bot)
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)


@dp.message(F.text.lower() == 'привет')
async def hello_handler(message: Message) -> None:
    await message.answer(f'И тебе привет')


@dp.message()
async def echo_handler(message: Message) -> None:
    try:
        await message.send_copy(chat_id=message.chat.id)
    except TypeError:
        await message.answer("Nice try!")


async def main() -> None:
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    asyncio.create_task(scheduler(bot))
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
