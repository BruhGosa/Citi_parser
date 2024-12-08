import requests
import json
import time
import os
import re
from lxml import html

# Переменая для выбора категории
category = "noutbuki"

# Кол-во продуктов для прасинга
count_product = 50

# Кол-во отзывов для каждого продукта
count_comment = 5

# Кол-во обзоров для каждого продукта
count_review = 5


# Функция которая отправляет запрос с последующей записью в json файл
def request(url, query, variables):
    while True:
        response = requests.post(url=url, json={"query": query, "variables": variables})
        if response.status_code == 200:
            data = response.json()
            return data
        elif response.status_code == 429:
            print("Слишком много запросов. Ожидание перед повторной попыткой...")
            time.sleep(5)
        else:
            print(f"HTTP Error: {response.status_code}, Response: {response.text}")


# Основная функция
def fetch_products():
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
    data = request(url, query, variables)
    products = data['data']['productsFilter']['record']['products']

    products_data = []
    rating_data = []
    review_data = []

    for product in products:
        product_id = product['id']
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
        if product['price']['old'] != 0:
            product_price = product['price']['current']
            product_price_old = product['price']['old']
        else:
            product_price = product['price']['current']
            product_price_old = None

        product_images = []

        for images in product['images']['citilink']:
            for image in images['sources']:
                product_images.append(image['url'])


        # Запрос для характеристики товара
        query = """query GetProductTabProperties($filter:Catalog_ProductFilterInput!){product(filter:$filter){...ProductTabProperties}}fragment ProductTabProperties on Catalog_Product{propertiesGroup{...PropertyGroup}}fragment PropertyGroup on Catalog_PropertyGroup{id,name,properties{...Property}}fragment Property on Catalog_Property{id,name,description,value,measure}"""
        variables = {
            "filter": {
                "id": product_id,
            },
        }
        data = request(url, query, variables)

        product_properties_data = []

        for properties in data['data']['product']['propertiesGroup']:
            properties_group_data = []
            properties_group_name = properties['name']

            for properties_grop in properties['properties']:
                properties_grop_info = {
                    'name': properties_grop['name'],
                    'value': properties_grop['value']
                }
                properties_group_data.append(properties_grop_info)

            properties_info = {
                'name': properties_group_name,
                'properties': properties_group_data
            }
            product_properties_data.append(properties_info)



        query = """query GetProductTabDocumentation($filter:Catalog_ProductFilterInput!){product(filter:$filter){...ProductTabDocumentation}}fragment ProductTabDocumentation on Catalog_Product{documentation{certificates{...Document},attachments{...Document}}}fragment Document on Catalog_ProductDocument{size,title,url}"""
        variables = {
            "filter": {
                "id": product_id
            }
        }
        data = request(url, query, variables)
        product_documents = data['data']['product']['documentation']

        documents_data = []
        for certificates in product_documents['certificates']:
            documents_data.append(certificates['url'])
        for attachments in product_documents['attachments']:
            documents_data.append(attachments['url'])



        query = """query($filter1:Catalog_ProductFilterInput!$input2:UGC_OpinionsInput!){product_b6304_d984e:product(filter:$filter1){opinions_03450_55993:opinions(input:$input2){payload{summary{rating ratingCounters{__typename count percentage rating}bestOpinion{id creationDate pros cons text rating isBest author{id b2c{__typename ...on B2C_PublicUserNotFoundError{message}...on B2C_PublicUserB2C{id userInfo{nickname firstName avatar{sources{__typename url size}}}expert{isExpert}}}counters{__typename ...on B2C_UserActivityCountersNotFoundError{message}...on B2C_UserActivityCounters{review opinion question}}vendor{__typename ...on B2C_VendorNotFoundError{message}...on B2C_Vendor{brand{id name}categories{__typename id}}}}status vendor voteInfo{info{type counters{likes dislikes}isVoted}target{id}}authorNickname abuse{reasons{__typename id name targetType isMessageRequired withMessage}target}}}items{__typename id creationDate pros cons text rating isBest author{id b2c{__typename ...on B2C_PublicUserNotFoundError{message}...on B2C_PublicUserB2C{id userInfo{nickname firstName avatar{sources{__typename url size}}}expert{isExpert}}}counters{__typename ...on B2C_UserActivityCountersNotFoundError{message}...on B2C_UserActivityCounters{review opinion question}}vendor{__typename ...on B2C_VendorNotFoundError{message}...on B2C_Vendor{brand{id name}categories{__typename id}}}}status vendor voteInfo{info{type counters{likes dislikes}isVoted}target{id}}authorNickname abuse{reasons{__typename id name targetType isMessageRequired withMessage}target}}sortings{__typename id name sort isSelected}}pageInfo{page perPage totalItems totalPages hasNextPage hasPreviousPage}}}}"""
        variables = {
            "filter1": {
                "id": product_id
            },
            "input2": {
                "pagination": {
                    "page": 1,
                    "perPage": count_comment
                }
            }
            }
        data = request(url, query, variables)
        product_rating = data['data']['product_b6304_d984e']['opinions_03450_55993']['payload']['summary']['rating']
        product_rating_count = 0
        for rating in data['data']['product_b6304_d984e']['opinions_03450_55993']['payload']['summary']['ratingCounters']:
            product_rating_count += rating['count']

        for rating in data['data']['product_b6304_d984e']['opinions_03450_55993']['payload']['items']:
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

        # Запрос для обзоров товаров
        query = """query($filter1:Catalog_ProductFilterInput!$input2:UGC_ReviewsInput!){product_b6304_839cf:product(filter:$filter1){reviews_b6834_ed052:reviews(input:$input2){items{__typename id content_84701_bf21a:content title viewsCount author{id b2c{__typename ...on B2C_PublicUserNotFoundError{message}...on B2C_PublicUserB2C{id userInfo{nickname firstName avatar{sources{__typename url size}}}expert{isExpert}}}counters{__typename ...on B2C_UserActivityCountersNotFoundError{message}...on B2C_UserActivityCounters{review opinion question}}vendor{__typename ...on B2C_VendorNotFoundError{message}...on B2C_Vendor{brand{id name}categories{__typename id}}}}status vendor voteInfo{info{type counters{likes dislikes}isVoted}target{id}}isBlocked creationDate}pageInfo{page perPage totalItems totalPages hasNextPage hasPreviousPage}}}}"""
        variables = {
            "filter1": {
                "id": product_id,
             },
            "input2": {
                "pagination": {
                    "page": 1,
                    "perPage": count_review
                },
                "forCurrentUser": False,
            }
        }
        data = request(url, query, variables)
        for review in data['data']['product_b6304_839cf']['reviews_b6834_ed052']['items']:
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

        products_data.append(product_info)

    with open('Товары.json', 'w', encoding='utf-8') as json_file:
        json.dump(products_data, json_file, ensure_ascii=False, indent=4)
    with open('Отзывы.json', 'w', encoding='utf-8') as json_file:
        json.dump(rating_data, json_file, ensure_ascii=False, indent=4)
    with open('Обзоры.json', 'w', encoding='utf-8') as json_file:
        json.dump(review_data, json_file, ensure_ascii=False, indent=4)



    # Запросы для каждого продукта
    # for product in products:
    #     product_id = product['id']
    #     product_name = product['shortName']
    #
    #     # Запрос для отзывов товара
    #     query = """query($filter1:Catalog_ProductFilterInput!$input2:UGC_OpinionsInput!){product_b6304_d984e:product(filter:$filter1){opinions_03450_55993:opinions(input:$input2){payload{summary{rating ratingCounters{__typename count percentage rating}bestOpinion{id creationDate pros cons text rating isBest author{id b2c{__typename ...on B2C_PublicUserNotFoundError{message}...on B2C_PublicUserB2C{id userInfo{nickname firstName avatar{sources{__typename url size}}}expert{isExpert}}}counters{__typename ...on B2C_UserActivityCountersNotFoundError{message}...on B2C_UserActivityCounters{review opinion question}}vendor{__typename ...on B2C_VendorNotFoundError{message}...on B2C_Vendor{brand{id name}categories{__typename id}}}}status vendor voteInfo{info{type counters{likes dislikes}isVoted}target{id}}authorNickname abuse{reasons{__typename id name targetType isMessageRequired withMessage}target}}}items{__typename id creationDate pros cons text rating isBest author{id b2c{__typename ...on B2C_PublicUserNotFoundError{message}...on B2C_PublicUserB2C{id userInfo{nickname firstName avatar{sources{__typename url size}}}expert{isExpert}}}counters{__typename ...on B2C_UserActivityCountersNotFoundError{message}...on B2C_UserActivityCounters{review opinion question}}vendor{__typename ...on B2C_VendorNotFoundError{message}...on B2C_Vendor{brand{id name}categories{__typename id}}}}status vendor voteInfo{info{type counters{likes dislikes}isVoted}target{id}}authorNickname abuse{reasons{__typename id name targetType isMessageRequired withMessage}target}}sortings{__typename id name sort isSelected}}pageInfo{page perPage totalItems totalPages hasNextPage hasPreviousPage}}}}"""
    #     variables = {
    #         "filter1": {
    #             "id": product_id
    #         },
    #         "input2": {
    #             "pagination": {
    #                 "page": 1,
    #                 "perPage": count_comment
    #             }
    #         }
    #     }
    #     other_request_product(url, query, variables, product_name, "comment_product")
    #
    #

if __name__ == "__main__":
    fetch_products()