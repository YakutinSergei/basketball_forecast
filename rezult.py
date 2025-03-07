import aiosqlite
import logging
from environs import Env
import aiohttp

env = Env()
env.read_env()
DATABASE = 'bets.db'  # Замените на ваш путь к базе данных

HEADERS = {
    'Package': env('KEY_REZ')
}


async def get_pending_bets():
    try:
        async with aiosqlite.connect(DATABASE) as db:
            cursor = await db.execute("SELECT * FROM bets WHERE status = 'pending'")
            pending_bets = await cursor.fetchall()
            return pending_bets
    except Exception as e:
        logging.error(f"Ошибка при получении записей с 'pending' статусом: {e}")
        return None


async def get_rezult():
    games_get = await get_pending_bets()
    if games_get:
        for game in games_get:
            print(f'Обрабатываем игру: {game}')

            URLink = f'https://rez.odds24.online/v1/rez/getgame/en/{game[2]}/{game[1]}'
            print(f'Запрос к API: {URLink}')

            rez_game = await get_api_rez(URLink)
            print(f'Ответ API: {rez_game}')

            if not rez_game or 'Score' not in rez_game:
                print('Ошибка: Пустой или некорректный ответ API')
                continue  # Пропускаем итерацию

            score_games = rez_game['Score'].split(' ')[0].split(':')
            total_score = sum(int(score) for score in score_games if score.isdigit())

            print(f'{total_score=}')


async def get_api_rez(URLink: str):
    """
    Функция выполняет асинхронный HTTP-запрос к API, сохраняет результат в JSON-файл
    и возвращает данные в формате JSON.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URLink, headers=HEADERS) as response:
                result = await response.json()

                # # Сохранение в JSON-файл
                # with open(FILENAME, "w", encoding="utf-8") as file:
                #     json.dump(result, file, ensure_ascii=False, indent=4)
                # print(result)

                return result.get('body', [])  # Возвращаем тело ответа или пустой список

        except Exception as e:
            print(f"Ошибка при запросе API: {e}")
            return []
