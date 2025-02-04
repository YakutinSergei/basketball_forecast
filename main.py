import asyncio
import aiosqlite
import aiohttp
import json
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation

# 🔹 Константы
TOKEN = "8079892130:AAEPo5Kzmks8m_6YfIG_fnyd8FeLPsyL6kY"  # Токен бота
CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"  # ID группы для сообщений
URL = 'https://odds.stagbet.site/v1/events/3/0/sub/100/live/ru'
HEADERS = {'Package': 'Ilgiz12yvO71nYehsWkc23JgdobL'}
DATABASE = "bets.db"
FILENAME = "data.json"

# 🔹 Создаем бота и диспетчер
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())


# 🔹 Функция создания базы данных
async def setup_database():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS bets (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            game_id INTEGER UNIQUE,
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
    print(result)
    # async with aiosqlite.connect(DATABASE) as db:
    #     async with db.execute("SELECT game_id FROM bets") as cursor:
    #         existing_games = {row[0] async for row in cursor}
    #
    for item in result:
        for element in item.get('events_list', []):
            if element.get('timer') in [1200, 1440] and element.get('period_name') == '3 Четверть':

                get_total = 0
                for search_total in element.get('game_oc_list', []):
                    if search_total.get('oc_group_name') == 'Тотал' and 'М' in search_total.get('oc_name', ''):
                        get_total = float(search_total['oc_name'].replace('М', ''))

                score_1, score_2 = map(int, element.get('score_full', '0:0').split(':'))
                result_total = get_total - (score_1 + score_2) * 2

                if result_total < 0:
                    game_id = element.get('game_id')

                    # # 🔹 Проверяем, нет ли уже этой игры в базе
                    # if game_id in existing_games:
                    #     continue

                    country = element.get('country_name')
                    league = element.get('tournament_name_ru')
                    team_1 = element.get('opp_1_name_ru')
                    team_2 = element.get('opp_2_name_ru')
                    score = element.get('score_period')
                    bet = f'ТБ{get_total}'
                    coefficient = 1.8

                    message_text = (f"🏆 {country} - {league}\n"
                                    f"⚽ {team_1} - {team_2}\n"
                                    f"📊 Счет: ({score})\n"
                                    f"🎯 Ставка: {bet} - КФ {coefficient}\n"
                                    f"⏳ Результат: ⏳⏳⏳")
                    print(message_text)

                        #await bot.send_message(CHAT_ID, message_text)

                        # await db.execute(
                        #     "INSERT INTO bets (game_id, country, league, team_1, team_2, score, bet, coefficient, message_id, status) "
                        #     "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        #     (game_id, country, league, team_1, team_2, score, bet, coefficient, msg.message_id, 'pending')
                        # )
                        # await db.commit()


# 🔹 Функция обновления результатов
async def update_results():
    async with aiosqlite.connect(DATABASE) as db:
        async with db.execute("SELECT game_id, message_id FROM bets WHERE status = 'pending'") as cursor:
            pending_bets = [(row[0], row[1]) async for row in cursor]

        result = await get_api()
        games = {item['game_id']: item for sublist in result for item in sublist.get('events_list', [])}

        for game_id, message_id in pending_bets:
            game = games.get(game_id)
            if game:
                final_score = game.get('score_full', '0:0')
                if game.get('finale'):
                    outcome = '✅✅✅' if int(final_score.split(':')[0]) + int(final_score.split(':')[1]) > 130 else '⛔⛔⛔'
                    new_text = f"📊 Итоговый счет: ({final_score})\n🎯 Результат: {outcome}"
                    await bot.edit_message_text(new_text, CHAT_ID, message_id)
                    await db.execute("UPDATE bets SET status = 'closed' WHERE game_id = ?", (game_id,))
        await db.commit()


# 🔹 Основной цикл мониторинга
async def monitoring():
    print('я тут')
    while True:

        await search_game()  # Поиск игр и публикация сообщений
        await update_results()  # Проверка результатов
        await asyncio.sleep(60)  # Повторяем через 60 секунд


# 🔹 Обработчик команды /start (чтобы бот не падал в aiogram 3.x)
@dp.message()
async def start_handler(message: Message):
    await message.answer("Привет! Бот работает и отслеживает ставки. 🔥")


# 🔹 Главная асинхронная функция
async def main():
    #await bot.delete_webhook(drop_pending_updates=True)
    print('[jxe')
    #await setup_database()  # Создаем БД
    asyncio.create_task(monitoring())  # Запускаем мониторинг ставок
    await dp.start_polling(bot)


# 🔹 Запуск бота
if __name__ == "__main__":
    asyncio.run(main())
