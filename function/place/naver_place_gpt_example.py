"""
OpenAI GPT-4.1 function calling 예제 (openai 1.x 최신 버전 호환)
- 네이버 지역 검색 API를 함수로 등록하고, GPT-4.1이 function call을 통해 호출하는 시나리오를 시뮬레이션합니다.
- 실제 OpenAI API 연동 예시 포함
- PEP8, 타입 힌트, Google 스타일 Docstring, 한글 주석
"""

import os
import asyncio
from typing import Any, Dict
from dotenv import load_dotenv
from .naver_place import (
    NaverPlaceSearchRequest,
    search_naver_place,
)
import openai
import json

# 환경 변수 로딩
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# openai 1.x 클라이언트 객체 생성
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Function calling에 사용할 함수 정의 (OpenAI function schema)
openai_function_schema = [
    {
        "name": "search_naver_place",
        "description": "네이버 지역 검색 API를 사용하여 장소 정보를 검색합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색어 (예: '카페', '맛집')"},
                "display": {"type": "integer", "description": "검색 결과 개수 (1~5)", "default": 5},
                "start": {"type": "integer", "description": "검색 시작 위치 (1~5)", "default": 1},
                "sort": {"type": "string", "enum": ["random", "comment"], "description": "정렬 방법. 사람들의 리뷰가 많은 순서대로의 추천이 필요한 경우, 'comment'를 사용할 수 있습니다."},
            },
            "required": ["query"],
        },
    }
]

async def gpt_function_calling_example() -> None:
    """GPT-4.1 function calling을 통해 네이버 지역 검색 API를 호출하는 예제 (openai 1.x)

    Args:
        없음
    Returns:
        없음
    """
    # 1. 사용자가 자연어로 질문
    user_message = "강서구에 장모님 장인어른 처형네와 같이 갈만한 점심 음식점을 추천해줘."

    # 2. OpenAI GPT-4.1 function calling API 호출 (실제 function call 예시)
    response = client.chat.completions.create(
        model="gpt-4.1",  # gpt-4.1 function calling 지원 모델
        messages=[
            {"role": "user", "content": user_message},
        ],
        functions=openai_function_schema,
        function_call="auto",  # GPT가 필요시 함수 호출
    )

    # 3. GPT가 함수 호출을 제안하면, 파라미터 추출
    message = response.choices[0].message
    print(f'GPT message: {message}')
    if message.function_call:
        func_name = message.function_call.name
        arguments = message.function_call.arguments
        args_dict = json.loads(arguments)
        # 4. 실제 함수 실행 (비동기)
        req = NaverPlaceSearchRequest(**args_dict)
        result = await search_naver_place(req)
        # 5. 결과를 다시 GPT에 전달하여 자연어 응답 생성
        followup = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "user", "content": user_message},
                message.model_dump(),
                {
                    "role": "function",
                    "name": func_name,
                    "content": result.model_dump_json(),
                },
            ],
        )
        print("GPT 최종 응답:")
        print(followup.choices[0].message.content)
    else:
        print("GPT가 함수 호출을 제안하지 않았습니다.")

if __name__ == "__main__":
    # 비동기 실행
    asyncio.run(gpt_function_calling_example()) 