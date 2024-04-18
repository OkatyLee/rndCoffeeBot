import datetime
import psycopg2
import asyncio
from apscheduler import AsyncScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import dotenv_values
from pathlib import Path



dotenv_path = Path('', '.env')

cfg = dotenv_values(dotenv_path=dotenv_path, encoding='UTF-8')
BOT_TOKEN = cfg['BOT_TOKEN']
CHAT_ID = cfg['CHAT_ID']
BOT_URL = cfg['BOT_URL']
host = cfg['POSTGRES_HOST']
user = cfg['POSTGRES_USER']
password = cfg['POSTGRES_PASSWORD']
db = cfg['POSTGRES_DB']

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

votes_option_1 = set()
poll_is_running: bool = False

TIME_LIMIT = 60  # Время опроса в секундах


async def start_poll():  # Посылаем сообщение в группу и начинаем опрос
    global poll_is_running
    poll_is_running = True
    builder = InlineKeyboardBuilder([
        [types.InlineKeyboardButton(
            text="Выпить кофе",
            url=BOT_URL,
            callback_data="start_dialog")]
    ])

    end_of_poll = (datetime.datetime.now() + datetime.timedelta(minutes=30)).time()
    message = await bot.send_message(
        chat_id=CHAT_ID,
        text=f'Кто хочет выпить кофе в {end_of_poll.hour}:{end_of_poll.minute}?'
             f'',
        reply_markup=builder.as_markup()
    )
    await asyncio.create_task(delete_message(message, TIME_LIMIT))  # удаляем сообщение после опроса

    poll_is_running = False


async def delete_message(message: types.Message, sleep_time: int = 0):
    await asyncio.sleep(sleep_time)
    await message.delete()

@dp.message(Command('pair'))
async def make_pair(message):
    connection = None
    try:
        connection = psycopg2.connect(
            database=db,
            user=user,
            password=password,
            host=host
        )
        cur = connection.cursor()

        cur.execute("""
            SELECT * FROM users
        """)
        users = cur.fetchall()
        if len(users) % 2:
            users = users[:-1]
        if len(users) == 0:
            return
        for usr in users:
            cur.execute("DELETE FROM users WHERE id = %s", (usr[0],))
        connection.commit()
        print(users)
        ind1, ind2 = 0, len(users)//2
        if len(users) < 2:
            await bot.send_message(users[-1][0], f"Тебе повезло выпить кофе с @{users[-1][1]}. Договорись о встрече!")

        for _ in range(len(users)//2):
            await bot.send_message(users[ind1][0], f"Тебе повезло выпить кофе с @{users[ind2][1]}. Договорись о встрече!")
            await bot.send_message(users[ind2][0], f"Тебе повезло выпить кофе с @{users[ind1][1]}. Договорись о встрече!")
            ind1+=1
            ind2+=1

        cur.close()
        users.clear()
    except Exception as _ex:
        print("ERROR: ", _ex)
    finally:
        if connection:
            connection.close()
        else:
            print('connection failed')

@dp.message(Command(commands='coffee'))
async def proces_coffee_cmd(message: types.Message):
    connection = None
    try:
        connection = psycopg2.connect(
            database=db,
            user=user,
            password=password,
            host=host
        )
        connection.autocommit = True
        data = [message.from_user.id, message.from_user.username]
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT EXISTS(SELECT id FROM users WHERE id={data[0]})"
            )
            exist = cursor.fetchone()[0]

            if not exist:
                cursor.execute(
                        "INSERT INTO users (id, username) VALUES (%s, %s)",
                        (data[0], data[1])
                )
                await message.answer('Отлично! Пара будет назначена вам в течении 15 минут')
            else:
                await message.answer('Подождите пока люди проголосуют, пара будет назначена в течении 15 минут')
    except Exception as _ex:
        print("EXCEPTION: ", _ex)
        await message.answer("Упс, сейчас я устал и не могу работать\nНапишите мне через некоторое время")
    finally:
        if connection:
            connection.close()
        else:
            print('connection failed')
        #pass

@dp.message(Command(commands=['poll']))
async def start(message):
    if message.chat.id == message.from_user.id:
        await start_poll()

@dp.message(Command(commands=['help', 'start']))
async def process_start_help_command(message: types.Message):
    await message.answer(
        'Напишите команду /coffee чтобы найти себе случайную пару на кофебрейк\n'
    )

@dp.message()
async def process_any_message(message: types.Message):
    if message.chat.id > 0:
        await message.answer(
            'Напишите команду /coffee чтобы найти себе случайную пару на кофебрейк\n'
        )

async def main():
    async with AsyncScheduler() as scheduler:
        await scheduler.add_schedule(
            make_pair,
            args=[None],
            trigger=CronTrigger(minute='*')
        )
        await scheduler.start_in_background()
        await dp.start_polling(bot)
        await asyncio.sleep(360)
        await dp.stop_polling()
        await scheduler.stop()




while 1:
    asyncio.run(main())


