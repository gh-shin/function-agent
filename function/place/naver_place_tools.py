import os
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
import httpx
from dotenv import load_dotenv

from langchain_core.tools import tool

load_dotenv()

NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "")


class NaverPlaceSearchArgs(BaseModel):
    query: str = Field(
        description="검색할 장소나 가게 이름. '강남역 맛집', '홍대 카페'와 같이 구체적으로 입력해야 합니다."
    )
    display: int = Field(
        default=5, ge=1, le=5, description="검색 결과 개수(1에서 5 사이)"
    )


@tool(args_schema=NaverPlaceSearchArgs)
async def search_naver_places(
    query: str, display: int = 5
) -> Union[List[Dict[str, Any]], str]:
    """
    사용자가 맛집, 카페, 병원 등 특정 장소를 찾아달라고 요청할 때 사용합니다.
    예: '강남역 근처 맛집 찾아줘', '서울 시청 주변 주차장 알려줘'
    """
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        return "오류: 네이버 API 인증 정보(NAVER_CLIENT_ID, NAVER_CLIENT_SECRET)가 설정되지 않았습니다."

    print(f"네이버 장소 검색 실행: query='{query}', display={display}")

    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query": query,
        "display": display,
        "start": "1",
        "sort": "sim",
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

        items = data.get("items", [])
        if not items:
            return f"'{query}'에 대한 검색 결과가 없습니다."

        simplified_results = [
            {
                "title": item["title"],
                "category": item["category"],
                "roadAddress": item["roadAddress"],
                "link": item["link"],
            }
            for item in items
        ]
        return simplified_results

    except httpx.HTTPStatusError as e:
        return f"네이버 API 호출 중 오류가 발생했습니다: {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"장소 검색 중 예기치 않은 오류가 발생했습니다: {str(e)}"
