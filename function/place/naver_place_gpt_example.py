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
from ..tools import naver_search_poi

# 환경 변수 로딩
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# openai 1.x 클라이언트 객체 생성
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# Function calling에 사용할 함수 정의 (OpenAI function schema)
openai_function_schema = [
    naver_search_poi
]

async def gpt_function_calling_example() -> None:
    """GPT-4.1 function calling을 통해 네이버 지역 검색 API를 호출하는 예제 (openai 1.x)

    Args:
        없음
    Returns:
        없음
    """
    # 1. 사용자가 자연어로 질문
    user_message = "강서구에 장모님 장인어른 처형네와 같이 갈만한 점심먹을건데 갈만한데 없을까? 술도 같이 좀 한 잔 하면 좋겠는데."

    # 2. OpenAI GPT-4.1 function calling API 호출 (실제 function call 예시)
    response = client.chat.completions.create(
        model="gpt-4.1",  # gpt-4.1 function calling 지원 모델
        messages=[
            {"role":"system", "content":"link필드가 있다면, 사용자가 클릭해 이동할 수 있도록 응답해야합니다."},
            {"role": "user", "content": user_message},
        ],
        functions=openai_function_schema,
        function_call="auto",  # GPT가 필요시 함수 호출
    )

    # 3. GPT가 함수 호출을 제안하면, 파라미터 추출
    message = response.choices[0].message
    
    if message.function_call:
        func_name = message.function_call.name
        arguments = message.function_call.arguments
        args_dict = json.loads(arguments)
        # 4. 실제 함수 실행 (비동기)
        req = NaverPlaceSearchRequest(**args_dict)
        result = await search_naver_place(req)
        print(result)
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