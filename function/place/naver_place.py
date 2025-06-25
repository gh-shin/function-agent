import os
from typing import List, Optional
from pydantic import BaseModel, Field
import httpx
from dotenv import load_dotenv

# 환경 변수 로딩
load_dotenv()

NAVER_CLIENT_ID: str = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET: str = os.getenv("NAVER_CLIENT_SECRET", "")

class NaverPlaceItem(BaseModel):
    """네이버 지역 검색 결과의 단일 아이템 모델

    Attributes:
        title (str): 업체, 기관의 이름
        link (str): 업체, 기관의 상세 정보 URL
        category (str): 업체, 기관의 분류 정보
        description (str): 업체, 기관에 대한 설명
        address (str): 업체, 기관명의 지번 주소
        roadAddress (str): 업체, 기관명의 도로명 주소
        mapx (int): 장소의 x 좌표(WGS84)
        mapy (int): 장소의 y 좌표(WGS84)
    """
    title: str
    link: str
    category: str
    description: str
    address: str
    roadAddress: str
    mapx: int
    mapy: int

class NaverPlaceSearchResponse(BaseModel):
    """네이버 지역 검색 API 응답 모델

    Attributes:
        total (int): 총 검색 결과 개수
        start (int): 검색 시작 위치
        display (int): 한 번에 표시할 검색 결과 개수
        items (List[NaverPlaceItem]): 검색 결과 리스트
    """
    total: int
    start: int
    display: int
    items: List[NaverPlaceItem]

class NaverPlaceSearchRequest(BaseModel):
    """네이버 지역 검색 API 요청 모델

    Attributes:
        query (str): 검색어
        display (Optional[int]): 한 번에 표시할 검색 결과 개수(1~5)
        start (Optional[int]): 검색 시작 위치(1~5)
        sort (Optional[str]): 정렬 방법(random/comment)
    """
    query: str = Field(..., description="검색어")
    display: Optional[int] = Field(5, ge=1, le=5, description="검색 결과 개수(1~5)")
    start: Optional[int] = Field(1, ge=1, le=5, description="검색 시작 위치(1~5)")
    sort: Optional[str] = Field("random", description="정렬 방법(random/comment)")

# 시간복잡도: O(1) (단일 HTTP 요청)
async def search_naver_place(
    req: NaverPlaceSearchRequest
) -> NaverPlaceSearchResponse:
    """네이버 지역 검색 API를 호출하여 결과를 반환합니다.

    Args:
        req (NaverPlaceSearchRequest): 검색 요청 파라미터
    Returns:
        NaverPlaceSearchResponse: 검색 결과
    Raises:
        httpx.HTTPStatusError: 네이버 API 호출 실패 시
    """
    print(f"naver place search: {req}")
    url = "https://openapi.naver.com/v1/search/local.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
    }
    params = {
        "query": req.query,
        "display": req.display,
        "start": req.start,
        "sort": req.sort,
    }
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        print(f'receive naver place: {data}')
        # 네이버 API의 응답 필드명을 그대로 사용
        return NaverPlaceSearchResponse(
            total=data["total"],
            start=data["start"],
            display=data["display"],
            items=[NaverPlaceItem(**item) for item in data["items"]],
        )

# 사용 예시 (FastAPI endpoint로 확장 가능)
# from fastapi import APIRouter
# router = APIRouter()
#
# @router.post("/naver/place/search", response_model=NaverPlaceSearchResponse)
# async def naver_place_search(req: NaverPlaceSearchRequest):
#     return await search_naver_place(req)

# ---
# 기술적 배경 및 장단점
# - 네이버 지역 검색 API는 비로그인 오픈 API로, 인증이 간단하고 빠르게 사용할 수 있습니다.
# - 단점: 호출 한도(25,000회/일)가 있으며, Client ID/Secret이 노출되지 않도록 주의해야 합니다.
# - 본 함수는 비동기 HTTP 요청을 사용하여 FastAPI 등 비동기 프레임워크와 궁합이 좋습니다.
# - 입력/출력 모델을 Pydantic으로 엄격하게 검증하여 안정성을 높였습니다.
