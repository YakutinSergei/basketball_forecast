import asyncio
import traceback

import aiosqlite
import aiohttp
import json
import logging
import re

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from environs import Env


env = Env()
env.read_env()

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("bot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# 🔹 Константы
TOKEN = env('BOT_TOKEN')  # Токен бота
CHAT_ID = env('CHAT_ID')  # ID группы для сообщений
URL = 'https://odds.stagbet.site/v1/events/3/0/sub/100/live/ru'
HEADERS = {'Package': f'{env('KEY')}'}
DATABASE = "bets.db"
FILENAME = "data.json"


# 🔹 Создаем бота и диспетчер
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())


def contains_forbidden_word(sentence):
    report_list = ['IPBL', 'Альтернативные матчи', 'eSports', '2K24', '2K25', '2K26', '2K27']
    words_in_sentence = set(re.findall(r'\b\w+\b', sentence))  # Извлекаем отдельные слова
    return any(word in words_in_sentence for word in report_list)

# 🔹 Функция создания базы данных
async def setup_database():
    try:
        async with aiosqlite.connect(DATABASE) as db:
            await db.execute('''CREATE TABLE IF NOT EXISTS bets (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                game_id INTEGER UNIQUE,
                                game_start INTEGER,
                                country TEXT,
                                league TEXT,
                                team_1 TEXT,
                                team_2 TEXT,
                                score TEXT,
                                bet TEXT,
                                coefficient REAL,
                                message_id INTEGER,
                                status TEXT)''')
            await db.commit()
    except Exception as e:
        logging.error(f"Ошибка при создании базы данных: {e}")


# 🔹 Функция получения данных с API
async def get_api():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL, headers=HEADERS) as response:
                result = await response.json()

                # 🔹 Сохранение в JSON-файл (для отладки)
                with open(FILENAME, "w", encoding="utf-8") as file:
                    json.dump(result, file, ensure_ascii=False, indent=4)

                return result.get('body', [])
        except Exception as e:
            print(f"❌ Ошибка API: {e}")
            return []


# 🔹 Функция поиска игр
async def search_game():
    result = await get_api()
    logging.info(f"длина {len(result)}")
    chat_id = env('CHAT_ID')


    try:

        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute("SELECT game_id FROM bets") as cursor:
                existing_games = {row[0] async for row in cursor}

            for item in result:
                for element in item.get('events_list', []):
                    if element.get('timer') in [1200, 1440] and element.get('period_name') == '3 Четверть':

                        # Поиск тотала среди коэффициентов 
                        for search_total in element.get('game_oc_list', []):
                            if search_total.get('oc_group_name') == 'Тотал' and 'М' in search_total.get('oc_name', ''):
                                get_total = float(search_total['oc_name'].replace('М', ''))

                        score_1, score_2 = map(int, element.get('score_full', '0:0').split(':'))
                        result_total = get_total - (score_1 + score_2) * 2
                        game_id = element.get('game_id')
                        # 🔹 Проверяем, нет ли уже этой игры в базе
                        if game_id in existing_games:
                            continue

                        country = element.get('country_name')
                        league = element.get('tournament_name_ru')
                        team_1 = element.get('opp_1_name_ru')
                        team_2 = element.get('opp_2_name_ru')
                        score = element.get('score_period')

                        if result_total > 16.5 and contains_forbidden_word(league):
                            for total in element.get('game_oc_list', []):
                                if total.get('oc_group_name') == 'Тотал' and total.get("oc_name").split(' ')[-1] == 'М':
                                    coefficient = total.get("oc_rate")
                                    get_total = float(total['oc_name'].replace('М', ''))
                                    bet = f'ТМ{get_total}'
                                    print(f'{total.get("oc_name")}, {total.get("oc_rate")}')
                        else:
                            bet = (f'{get_total} \n'
                                   f'Разница {result_total}')
                            coefficient = ''
                            chat_id = 6451994483





                        game_start = element.get('game_start')
                        #await bot.send_message(text=message_text, chat_id=6451994483)
                        time_1 = score.split(';')[0]
                        time_2 = score.split(';')[1]

                        sum_cont_1 = time_1.split(':')[0] + time_2.split(':')[0]
                        sum_cont_2 = time_1.split(':')[1] + time_2.split(':')[1]
                        message_text = (f"🏆 {country} - {league}\n"
                                        f"🏀 {team_1} - {team_2}\n"
                                        f"📊 Счет: {sum_cont_1}:{sum_cont_2} ({score})\n"
                                        f"🎯 Ставка: {bet} - КФ {coefficient}\n"
                                        f"⏳ Результат: ⏳⏳⏳\n"
                                        )

                        msg = await bot.send_message(text=message_text, chat_id=chat_id)

                        await db.execute(
                            "INSERT INTO bets (game_id, country, league, team_1, team_2, score, bet, coefficient, message_id, status, game_start) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (game_id, country, league, team_1, team_2, score, bet, coefficient, msg.message_id, 'pending', game_start)
                        )
                        await db.commit()
    except Exception as e:
        print('Ошибка!!!')
        tb = traceback.extract_tb(e.__traceback__)  # Получаем информацию об ошибке
        filename, lineno, func, text = tb[-1]  #
        print(filename, lineno, func, text)


# 🔹 Функция обновления результатов
async def update_results():
    try:
        async with aiosqlite.connect(DATABASE) as db:
            async with db.execute("SELECT game_id, message_id FROM bets WHERE status = 'pending'") as cursor:
                pending_bets = [(row[0], row[1]) async for row in cursor]

        result = await get_api()
        games = {item['game_id']: item for sublist in result for item in sublist.get('events_list', [])}

        for game_id, message_id in pending_bets:
            game = games.get(game_id)
            if game and game.get('finale'):
                outcome = '✅ Победа!' if int(game['score_full'].split(':')[0]) > int(game['score_full'].split(':')[1]) else '❌ Поражение'
                new_text = f"Итог: {outcome}"
                await bot.edit_message_text(new_text, CHAT_ID, message_id)
                async with aiosqlite.connect(DATABASE) as db:
                    await db.execute("UPDATE bets SET status = 'closed' WHERE game_id = ?", (game_id,))
                    await db.commit()
    except Exception as e:
        logging.error(f"Ошибка в update_results: {e}")



# 🔹 Основной цикл мониторинга
async def monitoring():
    while True:
        try:
            await search_game()
            await update_results()
            await asyncio.sleep(60)
        except Exception as e:
            logging.error(f"Ошибка в monitoring: {e}")


# 🔹 Обработчик команды /start (чтобы бот не падал в aiogram 3.x)
@dp.message()
async def start_handler(message: Message):
    await message.answer("Привет! Бот работает и отслеживает ставки. 🔥")


# 🔹 Главная асинхронная функция
async def main():
    #chat_id = env('CHAT_ID')
    #await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Запуск бота...")
    await bot.send_message(text='Бот запущен', chat_id=CHAT_ID)
    await setup_database()
    asyncio.create_task(monitoring())
    await dp.start_polling(bot)
    # await setup_database()  # Создаем БД
    # asyncio.create_task(monitoring())  # Запускаем мониторинг ставок
    # await dp.start_polling(bot)


# 🔹 Запуск бота
if __name__ == "__main__":

    asyncio.run(main())

