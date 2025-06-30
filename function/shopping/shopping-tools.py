from openai import AsyncOpenAI
import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
import httpx
import json
import requests


load_dotenv()
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


shopping_tool = {
    "type": "function",
    "name": "get_naver_search_results",
    "description": """
        Use this function when the user expresses a desire to buy a product, asks for product recommendations, or wants to search for items. This function can find relevant products based on a query.
    """,
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The product or keywords the user is looking for. e.g., 'blue running shoes', 'book', 'cup'",
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


async def get_shopping_response(user_prompt):
    tools = [shopping_tool]
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
