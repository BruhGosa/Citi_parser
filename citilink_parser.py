import requests
import json
import time
import logging
from lxml import html

# Переменая для выбора категории
category = "stiralnye-mashiny"

# Кол-во продуктов для прасинга
count_product = 20

# Кол-во отзывов для каждого продукта
count_comment = 5

# Кол-во обзоров для каждого продукта
count_review = 5


# В начале файла добавляем настройку логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('parser.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)


# Функция которая отправляет запрос с последующей записью в json файл
def request(url, query, variables, name_request):
    while True:
        try:
            logging.info(f"Отправка запроса к {url}, для получения данных об {name_request}")
            response = requests.post(url=url, json={"query": query, "variables": variables})

            if response.status_code == 200:
                logging.info("Запрос успешно выполнен")
                data = response.json()
                return data
            elif response.status_code == 429:
                logging.warning("Слишком много запросов. Ожидание перед повторной попыткой...")
                time.sleep(5)
            else:
                logging.error(f"Ошибка HTTP: {response.status_code}, Ответ: {response.text}")
        except Exception as e:
            logging.error(f"Произошла ошибка при выполнении запроса: {str(e)}")
            raise


# Функция для собирание данных об товаре в массив для будущего JSON
def product_answer(product, properties_request_data, document_request_data, rating_request_data):
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
    else:
        product_price = int(product['price']['current'])
        product_price_old = None

    product_images = []

    for images in product['images']['citilink']:
        if images['sources']:
            product_images.append(images['sources'][-1]['url'])

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

    documents_data = []
    for certificates in document_request_data['data']['product']['documentation']['certificates']:
        documents_data.append(certificates['url'])
    for attachments in document_request_data['data']['product']['documentation']['attachments']:
        documents_data.append(attachments['url'])

    product_rating = rating_request_data['data']['product_b6304_d984e']['opinions_03450_55993']['payload']['summary'][
        'rating']
    product_rating_count = 0
    for rating in rating_request_data['data']['product_b6304_d984e']['opinions_03450_55993']['payload']['summary'][
        'ratingCounters']:
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
    return product_info


# функция для собирание данных об ретинге в массив для будущего JSON
def rating_answer(rating_request_data, product_id):
    rating_data = []
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
        rating_data.append(rating_info)
    return rating_data


# функция для собирание данных об обзорах в массив для будущего JSON
def review_answer(review_request_data, product_id):
    review_data = []
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
        review_data.append(review_info)
    return review_data


# Основная функция
def fetch_products():
    logging.info(f"Начало парсинга категории: {category}")
    logging.info(f"Количество продуктов для парсинга: {count_product}")

    url = "https://www.citilink.ru/graphql/"
    query = """query GetSubcategoryProductsFilter($subcategoryProductsFilterInput:CatalogFilter_ProductsFilterInput!,$categoryFilterInput:Catalog_CategoryFilterInput!,$categoryCompilationFilterInput:Catalog_CategoryCompilationFilterInput!){productsFilter(filter:$subcategoryProductsFilterInput){record{...SubcategoryProductsFilter},error{... on CatalogFilter_ProductsFilterInternalError{__typename,message},... on CatalogFilter_ProductsFilterIncorrectArgumentsError{__typename,message}}},category(filter:$categoryFilterInput){...SubcategoryCategoryInfo}}fragment SubcategoryProductsFilter on CatalogFilter_ProductsFilter{__typename,products{...ProductSnippetFull},sortings{id,name,slug,directions{id,isSelected,name,slug,isDefault}},groups{...SubcategoryProductsFilterGroup},compilations{popular{...SubcategoryProductCompilationInfo},brands{...SubcategoryProductCompilationInfo},carousel{...SubcategoryProductCompilationInfo}},pageInfo{...Pagination},searchStrategy}fragment ProductSnippetFull on Catalog_Product{...ProductSnippetShort,propertiesShort{...ProductProperty},rating,counters{opinions,reviews}}fragment ProductSnippetShort on Catalog_Product{...ProductSnippetBase,labels{...ProductLabel},delivery{__typename,self{__typename,availabilityByDays{__typename,deliveryTime,storeCount},availableInFavoriteStores{store{id,shortName},productsCount}}},stock{countInStores,maxCountInStock},yandexPay{withYandexSplit}}fragment ProductSnippetBase on Catalog_Product{id,name,shortName,slug,isAvailable,images{citilink{...Image}},price{...ProductPrice},category{id,name},brand{name},multiplicity,quantityInPackageFromSupplier}fragment Image on Image{sources{url,size}}fragment ProductPrice on Catalog_ProductPrice{current,old,club,clubPriceViewType,discount{percent}}fragment ProductLabel on Catalog_Label{id,type,title,description,target{...Target},textColor,backgroundColor,expirationTime}fragment Target on Catalog_Target{action{...TargetAction},url,inNewWindow}fragment TargetAction on Catalog_TargetAction{id}fragment ProductProperty on Catalog_Property{name,value}fragment SubcategoryProductsFilterGroup on CatalogFilter_FilterGroup{id,isCollapsed,isDisabled,name,filter{... on CatalogFilter_ListFilter{__typename,isSearchable,logic,filters{id,isDisabled,isInShortList,isInTagList,isSelected,name,total,childGroups{id,isCollapsed,isDisabled,name,filter{... on CatalogFilter_ListFilter{__typename,isSearchable,logic,filters{id,isDisabled,isInShortList,isInTagList,name,isSelected,total}},... on CatalogFilter_RangeFilter{__typename,fromValue,isInTagList,maxValue,minValue,serifValues,scaleStep,toValue,unit}}}}},... on CatalogFilter_RangeFilter{__typename,fromValue,isInTagList,maxValue,minValue,serifValues,scaleStep,toValue,unit}}}fragment SubcategoryProductCompilationInfo on CatalogFilter_CompilationInfo{__typename,compilation{...SubcategoryProductCompilation},isSelected}fragment SubcategoryProductCompilation on Catalog_ProductCompilation{__typename,id,type,name,slug,parentSlug,seo{h1,title,text,description}}fragment Pagination on PageInfo{hasNextPage,hasPreviousPage,perPage,page,totalItems,totalPages}fragment SubcategoryCategoryInfo on Catalog_CategoryResult{... on Catalog_Category{...Category,seo{h1,title,text,description},compilation(filter:$categoryCompilationFilterInput){... on Catalog_CategoryCompilation{__typename,id,name,seo{h1,title,description,text}},... on Catalog_CategoryCompilationIncorrectArgumentError{__typename,message},... on Catalog_CategoryCompilationNotFoundError{__typename,message}},defaultSnippetType},... on Catalog_CategoryIncorrectArgumentError{__typename,message},... on Catalog_CategoryNotFoundError{__typename,message}}fragment Category on Catalog_Category{__typename,id,name,slug}"""
    variables = {
        "subcategoryProductsFilterInput": {
            "categorySlug": category,
            "compilationPath": [],
            "pagination": {
                "page": 1,
                "perPage": count_product,
            },
            "conditions": [],
            "sorting": {
                "id": "",
                "direction": "SORT_DIRECTION_DESC",
            },
            "popularitySegmentId": "THREE",
        },
        "categoryFilterInput": {
            "slug": category,
        },
        "categoryCompilationFilterInput": {
            "slug": "",
        },
    }
    product_request_data = request(url, query, variables, "всех продуктов")

    # Очищаем файлы перед записью
    for filename in ['Товары.json', 'Отзывы.json', 'Обзоры.json']:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('[\n')

    # Счетчики для отслеживания первых элементов
    first_product = True
    first_rating = True
    first_review = True

    for product in product_request_data['data']['productsFilter']['record']['products']:

        logging.info(f"Обработка продукта ID: {product['id']}")

        # Запрос для характеристики товара
        query = """query GetProductTabProperties($filter:Catalog_ProductFilterInput!){product(filter:$filter){...ProductTabProperties}}fragment ProductTabProperties on Catalog_Product{propertiesGroup{...PropertyGroup}}fragment PropertyGroup on Catalog_PropertyGroup{id,name,properties{...Property}}fragment Property on Catalog_Property{id,name,description,value,measure}"""
        variables = {
            "filter": {
                "id": product['id'],
            },
        }
        properties_request_data = request(url, query, variables, f"характеристик товара ID: {product['id']}")

        # Запрос для документов товара
        query = """query GetProductTabDocumentation($filter:Catalog_ProductFilterInput!){product(filter:$filter){...ProductTabDocumentation}}fragment ProductTabDocumentation on Catalog_Product{documentation{certificates{...Document},attachments{...Document}}}fragment Document on Catalog_ProductDocument{size,title,url}"""
        variables = {
            "filter": {
                "id": product['id']
            }
        }
        document_request_data = request(url, query, variables, f"документов товара ID: {product['id']}")

        # Запрос для рейтинга товара
        query = """query($filter1:Catalog_ProductFilterInput!$input2:UGC_OpinionsInput!){product_b6304_d984e:product(filter:$filter1){opinions_03450_55993:opinions(input:$input2){payload{summary{rating ratingCounters{__typename count percentage rating}bestOpinion{id creationDate pros cons text rating isBest author{id b2c{__typename ...on B2C_PublicUserNotFoundError{message}...on B2C_PublicUserB2C{id userInfo{nickname firstName avatar{sources{__typename url size}}}expert{isExpert}}}counters{__typename ...on B2C_UserActivityCountersNotFoundError{message}...on B2C_UserActivityCounters{review opinion question}}vendor{__typename ...on B2C_VendorNotFoundError{message}...on B2C_Vendor{brand{id name}categories{__typename id}}}}status vendor voteInfo{info{type counters{likes dislikes}isVoted}target{id}}authorNickname abuse{reasons{__typename id name targetType isMessageRequired withMessage}target}}}items{__typename id creationDate pros cons text rating isBest author{id b2c{__typename ...on B2C_PublicUserNotFoundError{message}...on B2C_PublicUserB2C{id userInfo{nickname firstName avatar{sources{__typename url size}}}expert{isExpert}}}counters{__typename ...on B2C_UserActivityCountersNotFoundError{message}...on B2C_UserActivityCounters{review opinion question}}vendor{__typename ...on B2C_VendorNotFoundError{message}...on B2C_Vendor{brand{id name}categories{__typename id}}}}status vendor voteInfo{info{type counters{likes dislikes}isVoted}target{id}}authorNickname abuse{reasons{__typename id name targetType isMessageRequired withMessage}target}}sortings{__typename id name sort isSelected}}pageInfo{page perPage totalItems totalPages hasNextPage hasPreviousPage}}}}"""
        variables = {
            "filter1": {
                "id": product['id']
            },
            "input2": {
                "pagination": {
                    "page": 1,
                    "perPage": count_comment
                }
            }
        }
        rating_request_data = request(url, query, variables, f"рейтинга товара ID: {product['id']}")

        # Запрос для обзоров товаров
        query = """query($filter1:Catalog_ProductFilterInput!$input2:UGC_ReviewsInput!){product_b6304_839cf:product(filter:$filter1){reviews_b6834_ed052:reviews(input:$input2){items{__typename id content_84701_bf21a:content title viewsCount author{id b2c{__typename ...on B2C_PublicUserNotFoundError{message}...on B2C_PublicUserB2C{id userInfo{nickname firstName avatar{sources{__typename url size}}}expert{isExpert}}}counters{__typename ...on B2C_UserActivityCountersNotFoundError{message}...on B2C_UserActivityCounters{review opinion question}}vendor{__typename ...on B2C_VendorNotFoundError{message}...on B2C_Vendor{brand{id name}categories{__typename id}}}}status vendor voteInfo{info{type counters{likes dislikes}isVoted}target{id}}isBlocked creationDate}pageInfo{page perPage totalItems totalPages hasNextPage hasPreviousPage}}}}"""
        variables = {
            "filter1": {
                "id": product['id']
            },
            "input2": {
                "pagination": {
                    "page": 1,
                    "perPage": count_review
                },
                "forCurrentUser": False,
            }
        }
        review_request_data = request(url, query, variables, f"обзоров товара ID: {product['id']}")

        products_data = product_answer(product, properties_request_data, document_request_data, rating_request_data)
        rating_data = rating_answer(rating_request_data, product['id'])
        review_data = review_answer(review_request_data, product['id'])

        # Записываем информацию о продукте
        with open('Товары.json', 'a', encoding='utf-8') as f:
            if not first_product:
                f.write(',\n')
            json.dump(products_data, f, ensure_ascii=False, indent=4)
            first_product = False

        # Записываем отзывы продукта
        with open('Отзывы.json', 'a', encoding='utf-8') as f:
            for rating in rating_data:
                if not first_rating:
                    f.write(',\n')
                rating_info = {
                    'product_id': int(rating['product_id']),
                    'id': rating['id'],
                    'rating': rating['rating'],
                    'author': rating['author'],
                    'date': rating['date'],
                    'pros': rating['pros'],
                    'cons': rating['cons'],
                    'comment': rating['comment'],
                    'likes': rating['likes'],
                    'dislikes': rating['dislikes']
                }
                json.dump(rating_info, f, ensure_ascii=False, indent=4)
                first_rating = False

        # Записываем обзоры продукта
        with open('Обзоры.json', 'a', encoding='utf-8') as f:
            for review in review_data:
                if not first_review:
                    f.write(',\n')
                review_info = {
                    'product_id': int(review['product_id']),
                    'id': review['id'],
                    'author': review['author'],
                    'date': review['date'],
                    'title': review['title'],
                    'content': review['content'],
                    'views': review['views'],
                    'likes': review['likes'],
                    'dislikes': review['dislikes']
                }
                json.dump(review_info, f, ensure_ascii=False, indent=4)
                first_review = False

        logging.info(f"Продукт {int(product['id'])} успешно обработан")
        time.sleep(2)

    for filename in ['Товары.json', 'Отзывы.json', 'Обзоры.json']:
        with open(filename, 'a', encoding='utf-8') as f:
            f.write('\n]')
    logging.info(f"Программа успешно завершена")


if __name__ == "__main__":
    fetch_products()