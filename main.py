import time
import logging
import os
from lxml import html
from dotenv import load_dotenv
from request_handler import request
from queries import (url, PRODUCTS_QUERY, PRODUCT_VARIABLE)
from data_processors import product_answer, rating_answer, review_answer

load_dotenv()

# Переменая для выбора категории
category = os.getenv('CATEGORY')

# В начале файла добавляем настройку логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parser.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Основная функция
def fetch_products():
    logging.info(f"Начало парсинга категории: {category}")

    # Очищаем файлы перед записью
    for filename in ['Товары.json', 'Отзывы.json', 'Обзоры.json']:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('[\n')

    # Счетчики для отслеживания первых элементов
    first_product = True
    first_rating = True
    first_review = True

    current_page_products = 1
    has_next_page_products = True

    while has_next_page_products:

        logging.info(f"Обработка страницы продукта №{current_page_products}")

        product_request_data = request(url, PRODUCTS_QUERY, PRODUCT_VARIABLE(category, current_page_products), "всех продуктов")
        
        # Проверка на наличие следующей страницы
        has_next_page_products = product_request_data['data']['productsFilter']['record']['pageInfo']['hasNextPage']
        current_page_products += 1

        for product in product_request_data['data']['productsFilter']['record']['products']:

            first_product = product_answer(product, first_product)
            first_rating = rating_answer(product['id'], first_rating)
            first_review = review_answer(product['id'], first_review)
            
            logging.info(f"Продукт {int(product['id'])} успешно обработан")
            time.sleep(2)

    for filename in ['Товары.json', 'Отзывы.json', 'Обзоры.json']:
        with open(filename, 'a', encoding='utf-8') as f:
            f.write('\n]')
    logging.info(f"Программа успешно завершена")


if __name__ == "__main__":
    fetch_products()