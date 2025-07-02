from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
import httpx
import json
import requests

from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

load_dotenv()
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


shopping_search_tool = {
    "type": "function",
    "name": "get_naver_search_results",
    "description": """
        사용자가 쇼핑 삼품에 대한 검색, 구매 및 추천을 원할 때 사용하는 함수
        해당 함수를 통해 사용자의 쿼리와 연관된 상품을 검색할 수 있다.
    """,
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "상품 혹은 유저가 찾고자 하는 상품의 키워드 e.g., '파란 신발', '서정적인 책', '보온 텀블러'",
            }
        },
        "required": ["query"],
    },
}

shopping_add_cart_tool = {
    "type": "function",
    "name": "add_product_to_mycart",
    "description": """
        사용자가 추천 혹은 검색된 상품을 장바구니에 추가하고자 할 때 사용하는 함수
        사용자 대화 히스토리를 기반으로 저장할 상품을 탐색한다
    """,
    "parameters": {
        "type": "object",
        "properties": {
            "product_names": {
                "type": "array",
                "description": "장바구니에 추가하고자하는 상품 이름 목록",
                "items": {
                    "type": "string"
                },
            },
            "product_urls": {
                "type": "array",
                "description": "해당 상품의 url. product_names 와 길이가 같아야하며, 만약 url이 없다면 공백을 삽입",
                "items": {
                    "type": "string"
                }
            },
            "prices": {
                "type": "array",
                "description": "해당 상품의 가격. product_names와 길이가 같아야하며, 만약 가격이 없다면 공백 삽입",
                "items": {
                    "type": "string"
                }
            }
        },
        "required": ["query"],
    },
}


async def search_naver_shopping(query):
    url = "https://openapi.naver.com/v1/search/shop.json?query={query}&display=10&start=1&sort=sim&filter=naverpay"
    headers = {
        "X-Naver-Client-Id": os.getenv("NAVER_CLIENT_ID"),
        "X-Naver-Client-Secret": os.getenv("NAVER_CLIENT_SECRET"),
    }
    params = {
        "query": query,
        "display": "10",
        "start": "1",
        "sort": "sim",
        "filter": "naverpay",
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

    return data


async def add_product_to_mycart(product_names, product_urls, prices):
    MONGODB_URI = os.getenv('MONGODB_URI')


    add_cart_list = []
    for idx in len(product_names):
        tmp_product = {
            "product_name": product_names[idx],
            "product_url": product_urls[idx],
            "price": prices[idx],
        }
        add_cart_list.append(tmp_product)

    try:
        client = MongoClient(MONGODB_URI)

        db = client['shopping']
        collection = db['cart']

        if add_cart_list:
            result = collection.insert_many(add_cart_list)
        
        return '삽입 완료'
    except:
        return '삽입 불가능한 상태'



async def get_shopping_response(user_prompt):
    tools = [shopping_search_tool]
    messeges = [{"role": "user", "content": user_prompt}]
    response = await client.responses.create(
        model="gpt-4.1-mini",
        input=messeges,
        tools=tools,
    )
    for output in response.output:
        if output.type == "function_call" and output.name == "get_naver_search_results":
            search_result = await search_naver_shopping(output.arguments)
            messeges.append(
                {
                    "role": "function",
                    "name": "get_naver_search_results",
                    "content": str(search_result),
                }
            )

    final_response = await client.chat.completions.create(
        model="gpt-4.1-mini", messages=messeges
    )

    return final_response.choices[0].message.content


async def main():  # test 용 메인 함수
    user_prompt = """어제 안경 매장에 갔는데 너무 이쁜 안경들이 많더라궁.
  근데 안경은 안어울려서 안경 말고 비슷한 선글라스를 사려고 했어.
  하지만 선글라스는 내 취향이 아니라서 핸드폰 케이스를 사고 싶은데 어떤걸 사면 좋을까 검색해줄 수 있어?
  기종은 아이폰 15얌"""
    response = await get_shopping_response(user_prompt)
    print(response)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
