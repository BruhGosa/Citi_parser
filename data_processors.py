import requests
import logging
import json
from lxml import html
from request_handler import request
from queries import (url, PROPERTIES_QUERY, DOCUMENTS_QUERY, RATING_QUERY, REVIEW_QUERY, 
                     PROPERTIES_OR_DOCUMENTS_VARIABLE, RATING_VARIABLE, REVIEW_VARIABLE)

# Функция для собирание данных об товаре в массив для будущего JSON
def product_answer(product, first_product):

    logging.info(f"Обработка продукта ID: {product['id']}")
    product_id = int(product['id'])
    product_url = f"https://www.citilink.ru/product/{product['slug']}-{product['id']}/"

    product_categories = []
    response = requests.get(product_url)
    if response.status_code == 200:
        tree = html.fromstring(response.content)
        breadcrumbs = tree.xpath("//div[contains(@itemtype, 'BreadcrumbList')]/div/a")

        for breadcrumb in breadcrumbs:
            breadcrumb_url = f"https://www.citilink.ru{breadcrumb.get('href')}"
            breadcrumb_name = breadcrumb.xpath("./span/text()")[0]  # Получаем текст из <span>

            product_categories.append({
                "url": breadcrumb_url,
                "name": breadcrumb_name
            })

    product_name = product['name']
    product_articul = product['id']
    if product['price']['old'] and product['price']['old'] != '':
        product_price = int(product['price']['current'])
        product_price_old = int(product['price']['old'])
    elif product['price']['current'] == '' and product['price']['old'] == '':
        product_price = None
        product_price_old = None
    else:
        product_price = int(product['price']['current'])
        product_price_old = None

    product_images = []

    for images in product['images']['citilink']:
        if images['sources']:
            product_images.append(images['sources'][-1]['url'])

    properties_request_data = request(url, PROPERTIES_QUERY, PROPERTIES_OR_DOCUMENTS_VARIABLE(product['id']), f"характеристик товара ID: {product['id']}")
    product_properties_data = []

    for properties_grop in properties_request_data['data']['product']['propertiesGroup']:
        properties_group_data = []
        properties_group_name = properties_grop['name']

        for properties in properties_grop['properties']:
            properties_grop_info = {
                'name': properties['name'],
                'value': properties['value']
            }
            properties_group_data.append(properties_grop_info)

        properties_info = {
            'name': properties_group_name,
            'properties': properties_group_data
        }
        product_properties_data.append(properties_info)

    document_request_data = request(url, DOCUMENTS_QUERY, PROPERTIES_OR_DOCUMENTS_VARIABLE(product['id']), f"документов товара ID: {product['id']}")
    documents_data = []
    for certificates in document_request_data['data']['product']['documentation']['certificates']:
        documents_data.append(certificates['url'])
    for attachments in document_request_data['data']['product']['documentation']['attachments']:
        documents_data.append(attachments['url'])

    rating_request_data = request(url, RATING_QUERY, RATING_VARIABLE(product['id'], 1), f"рейтинга товара ID: {product['id']}")
    product_rating = rating_request_data['data']['product_b6304_d984e']['opinions_03450_55993']['payload']['summary']['rating']
    product_rating_count = 0
    for rating in rating_request_data['data']['product_b6304_d984e']['opinions_03450_55993']['payload']['summary']['ratingCounters']:
        product_rating_count += rating['count']

    product_info = {
        'id': product_id,
        'url': product_url,
        'categories': product_categories,
        'name': product_name,
        'article': product_articul,
        'price': product_price,
        'price_old': product_price_old,
        'images': product_images,
        'properties': product_properties_data,
        'documents': documents_data,
        'rating': product_rating,
        'reviews': product_rating_count
    }

    # Записываем информацию о продукте
    with open('Товары.json', 'a', encoding='utf-8') as f:
        if not first_product:
            f.write(',\n')
        json.dump(product_info, f, ensure_ascii=False, indent=4)
        first_product = False
    return first_product


# функция для собирание данных об ретинге в массив для будущего JSON
def rating_answer(product_id, first_rating):
    current_page_rating = 1
    has_next_page_rating = True
    while has_next_page_rating: 

        logging.info(f"Обработка страницы с обзорами продукта ID: {product_id} №{current_page_rating}")

        rating_request_data = request(url, RATING_QUERY, RATING_VARIABLE(product_id, current_page_rating), f"рейтинга товара ID: {product_id}")

        for rating in rating_request_data['data']['product_b6304_d984e']['opinions_03450_55993']['payload']['items']:
            rating_info = {
                'product_id': product_id,
                'id': rating['id'],
                'rating': rating['rating'],
                'author': rating['authorNickname'],
                'date': rating['creationDate'],
                'pros': rating['pros'],
                'cons': rating['cons'],
                'comment': rating['text'],
                'likes': rating['voteInfo']['info']['counters']['likes'],
                'dislikes': rating['voteInfo']['info']['counters']['dislikes']
            }

            # Записываем рейтинги продукта
            with open('Отзывы.json', 'a', encoding='utf-8') as f:
                if not first_rating:
                    f.write(',\n')
                json.dump(rating_info, f, ensure_ascii=False, indent=4)
                first_rating = False
        
        has_next_page_rating = rating_request_data['data']['product_b6304_d984e']['opinions_03450_55993']['pageInfo']['hasNextPage']
        current_page_rating += 1
    return first_rating


# функция для собирание данных об обзорах в массив для будущего JSON
def review_answer(product_id, first_review):
    current_page_review = 1
    has_next_page_review = True
    review_data = []
    while has_next_page_review:
        logging.info(f"Обработка страницы с обзорами продукта ID: {product_id} №{current_page_review}")
        review_request_data = request(url, REVIEW_QUERY, REVIEW_VARIABLE(product_id, current_page_review), f"обзоров товара ID: {product_id}")
        for review in review_request_data['data']['product_b6304_839cf']['reviews_b6834_ed052']['items']:
            review_info = {
                'product_id': product_id,
                'id': review['id'],
                'author': review['author']['b2c']['userInfo']['firstName'],
                'date': review['creationDate'],
                'title': review['title'],
                'content': review['content_84701_bf21a'],
                'views': review['viewsCount'],
                'likes': review['voteInfo']['info']['counters']['likes'],
                'dislikes': review['voteInfo']['info']['counters']['dislikes']
            }
            # Записываем рейтинги продукта
            with open('Обзоры.json', 'a', encoding='utf-8') as f:
                if not first_review:
                    f.write(',\n')
                json.dump(review_info, f, ensure_ascii=False, indent=4)
                first_review = False
        has_next_page_review = review_request_data['data']['product_b6304_839cf']['reviews_b6834_ed052']['pageInfo']['hasNextPage']
        current_page_review += 1
    return first_review
