import asyncio
import aiohttp
import json
# URL API, с которого получаем данные
URL = 'https://odds.stagbet.site/v1/events/3/0/sub/100/live/ru'
#URL = 'https://odds.stagbet.site/v1/rez/getsports/ru/0'

HEADERS = {
    'Package': 'Ilgiz12yvO71nYehsWkc23JgdobL'
}

# Глобальный список для хранения информации об играх
information_game = []

FILENAME = "data.json"

async def get_api():
    """
    Функция выполняет асинхронный HTTP-запрос к API, сохраняет результат в JSON-файл
    и возвращает данные в формате JSON.
    """
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(URL, headers=HEADERS) as response:
                result = await response.json()

                # # Сохранение в JSON-файл
                # with open(FILENAME, "w", encoding="utf-8") as file:
                #     json.dump(result, file, ensure_ascii=False, indent=4)
                print(result)

                return result.get('body', [])  # Возвращаем тело ответа или пустой список

        except Exception as e:
            print(f"Ошибка при запросе API: {e}")
            return []


async def search_game(get_data):
    """
    Функция анализирует полученные данные, выбирает нужные игры и добавляет их в список.
    """

    result = await get_data  # Дожидаемся выполнения асинхронного запроса
    for item in result:
        for element in item.get('events_list', []):  # Перебираем список событий

            # Проверяем, идет ли третья четверть и таймер на 1200 или 1400
            if element.get('timer') in [1200, 1400] and element.get('period_name') == '3 Четверть':
                print(f'{element.get('timer')=}')

                get_total = 0  # Переменная для хранения тотала
                set_game = {}  # Словарь с информацией об игре

                # Поиск тотала среди коэффициентов
                for search_total in element.get('game_oc_list', []):
                    if search_total.get('oc_group_name') == 'Тотал' and 'М' in search_total.get('oc_name', ''):
                        get_total = float(search_total['oc_name'].replace('М', ''))

                # Получаем общий счет команд
                score_1, score_2 = map(int, element.get('score_full', '0:0').split(':'))

                # Вычисляем разницу тотала
                result_total = get_total - (score_1 + score_2) * 2
                print(f"Рассчитанный результат тотала: {result_total}")
                print(f"Исходный тотал: {get_total}")
                print(f"Счет первой команды: {score_1}")
                print(f"Счет второй команды: {score_2}")

                # Если рассчитанный тотал меньше 0, добавляем игру в список
                if result_total < 0:
                    set_game['tournament_name'] = element.get('tournament_name_ru')
                    set_game['idGame'] = element.get('game_id')
                    set_game['command_1'] = element.get('opp_1_name_ru')
                    set_game['command_2'] = element.get('opp_2_name_ru')
                    set_game['score_full_command_1'] = score_1
                    set_game['score_full_command_2'] = score_2
                    set_game['score_period'] = element.get('score_period')
                    set_game['total'] = get_total

                    # Проверяем, есть ли уже такая игра в списке
                    if set_game not in information_game:
                        information_game.append(set_game)

    print("Исходные данные:", result)
    print("Сохраненные игры:", information_game)


# Запуск функции в асинхронном режиме
asyncio.run(search_game(get_api()))