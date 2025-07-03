"""장소 추천 AI 에이전트 메인 스크립트.

이 스크립트는 OpenAI의 LLM과 대한민국 공공데이터포털의 API를 연동하여,
사용자의 자연어 질문에 대한 장소 추천을 수행하는 AI 에이전트의
핵심 로직을 담고 있습니다.

주요 기능:
- 2개의 공공데이터 API(한국관광공사, 한국문화정보원) 연동.
- OpenAI의 Function Calling 기능을 사용한 동적 도구 선택.
- 사용자의 자연어 입력을 기반으로 API 파라미터를 동적으로 생성 및 전처리.
- JSON(관광공사) 및 XML(문화정보원) API 응답 파싱 및 정규화.
- 전체 대화 흐름을 관리하고 시나리오 기반 테스트 실행.

실행 전, 아래 환경 변수가 반드시 설정되어야 합니다:
- OPENAI_API_KEY: OpenAI API 인증키
- KR_TOUR_API_KEY: 한국관광공사 API 인증키
- KR_CULTURE_API_KEY: 한국문화정보원 API 인증키
"""
import os
import json
import httpx
import xml.etree.ElementTree as ET
from openai import OpenAI
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncio
from dotenv import load_dotenv
from urllib.parse import quote, urlencode
import traceback
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain_core.tools import tool
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain import hub

load_dotenv()
# --- 1. 설정: API 키 및 클라이언트 초기화 ---
try:
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
    # OpenAI 클라이언트 초기화
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    # 한국관광공사 API 키
    KR_TOUR_API_KEY = os.environ.get("KR_TOUR_API_KEY")
    if not KR_TOUR_API_KEY:
        raise ValueError("한국관광공사 API 키(KR_TOUR_API_KEY)가 설정되지 않았습니다.")

    # 한국문화정보원 API 키
    KR_CULTURE_API_KEY = os.environ.get("KR_CULTURE_API_KEY")
    if not KR_CULTURE_API_KEY:
        raise ValueError("한국문화정보원 API 키(KR_CULTURE_API_KEY)가 설정되지 않았습니다.")

except (TypeError, ValueError) as e:
    print(f"--- 경고: API 키 설정에 문제가 있습니다: {e} ---")
    print("API 호출 기능이 제한될 수 있습니다. 스크립트를 실행하기 전에 API 키를 환경 변수로 설정해야 합니다.")
    client = None
    KR_TOUR_API_KEY = "DUMMY_KEY"  # 예외 발생 시 더미 키로 설정
    KR_CULTURE_API_KEY = "DUMMY_KEY"

CONTENT_TYPE_MAP = {
    12: "관광지",
    14: "문화시설",
    15: "행사/공연/축제",
    25: "여행코스",
    28: "레포츠",
    32: "숙박",
    38: "쇼핑",
    39: "음식점"
}
# --- 2. 데이터 애그리게이션 계층: API 호출 및 데이터 변환 ---


def transform_kto_to_canonical(item: Dict[str, Any]) -> Dict[str, Any]:
    """한국관광공사(TourAPI) 응답 아이템을 표준 데이터 모델로 변환합니다.

    Args:
        item (Dict[str, Any]): TourAPI의 JSON 응답에서 추출된 개별 아이템 딕셔너리.

    Returns:
        Dict[str, Any]: 에이전트 내부에서 사용하는 표준화된 데이터 모델 딕셔너리.
    """
    return {
        "canonical_name": item.get("title", ""),
        "category": CONTENT_TYPE_MAP.get(item.get("contenttypeid", "")),
        "sub_category": ">".join(filter(None, [item.get("cat1"), item.get("cat2"), item.get("cat3")])),
        "address_full": " ".join(filter(None, [item.get("addr1"), item.get("addr2")])),
        "geo_lat": float(item.get("mapy", 0.0)),
        "geo_lon": float(item.get("mapx", 0.0)),
        "description_main": item.get("overview", ""),
        "image_url": item.get("firstimage", ""),
        "contact_info": item.get("tel", ""),
        "operating_hours": "",
        "fee_info": "",
        "source_api_id": "B551011",
        "source_data_id": item.get("contentid", ""),
    }


def transform_kcis_to_canonical(item: Dict[str, Any]) -> Dict[str, Any]:
    """한국문화정보원(KCIS) 응답 아이템을 표준 데이터 모델로 변환합니다.

    Args:
        item (Dict[str, Any]): 문화정보원 API의 XML 응답을 파싱하여 생성된 
                              개별 아이템 딕셔너리.

    Returns:
        Dict[str, Any]: 에이전트 내부에서 사용하는 표준화된 데이터 모델 딕셔너리.
    """
    return {
        "canonical_name": item.get("title", ""),
        "category": item.get("serviceName", "문화행사"),
        "sub_category": item.get("realmName", ""),
        "address_full": f"{item.get('area', '')} {item.get('sigungu', '')} {item.get('place', '')}".strip(),
        "geo_lat": float(item.get("gpsY", 0.0)),
        "geo_lon": float(item.get("gpsX", 0.0)),
        "description_main": "",
        "image_url": item.get("thumbnail", ""),
        "contact_info": "",
        "operating_hours": f"{item.get('startDate', '')} ~ {item.get('endDate', '')}",
        "fee_info": "",
        "source_api_id": "B553457",
        "source_data_id": item.get("seq", ""),
    }


class KrTourInfoInput(BaseModel):
    keyword: str = Field(
        description="한국 관광공사에서 제공하는 지역별 추천 여행지 관련 키워드"
    )
    area_code: str = Field(
        default="", description="검색할 지역의 코드: 1=서울, 2=인천, 3=대전, 4=대구, 5=광주, 6=부산, 7=울산, 8=세종, 31=경기도, 32=강원도, 33=충청북도, 34=충청남도, 35=경상북도, 36=경상남도, 37=전라북도, 38=전라남도, 39=제주도"
    )


@tool(args_schema=KrTourInfoInput)
async def search_tourist_info(keyword: str, area_code: str = "") -> str:
    """한국관광공사 TourAPI를 호출하여 관광 정보를 검색합니다.

    키워드, 지역 코드를 사용하여 관광 정보를 조회하고,
    결과를 JSON 형식의 문자열로 반환합니다.

    Args:
        keyword (str): 검색할 키워드.
        area_code (str, optional): 지역 코드 (예: '1' for 서울). Defaults to "".

    Returns:
        str: 검색 결과를 표준 데이터 모델로 변환한 후 직렬화한 JSON 문자열.
             오류 발생 시 오류 정보를 담은 JSON 문자열을 반환합니다.
    """
    print(
        f"  [도구 실행] search_tourist_info(keyword='{keyword}', area_code='{area_code}'")
    if KR_TOUR_API_KEY == "DUMMY_KEY":
        return json.dumps({"error": "한국관광공사 API 키가 없어 실제 호출을 할 수 없습니다."})

    base_url = "http://apis.data.go.kr/B551011/KorService2/searchKeyword2"
    params = {
        "serviceKey": KR_TOUR_API_KEY, "numOfRows": 3, "pageNo": 1,
        "MobileOS": "WEB", "MobileApp": "PlaceAgent", "_type": "json",
        "keyword": quote(keyword),
        "areaCode": area_code
    }

    try:
        print(f"[DEBUG] 요청 URL: {base_url}")
        print(f"[DEBUG] 요청 파라미터: {params}")
        query_string = urlencode(
            {k: v for k, v in params.items() if v}, safe='%')
        full_url = f"{base_url}?{query_string}"
        print(f"[DEBUG] 최종 요청 URL: {full_url}")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(full_url)
            print(f"[DEBUG] 응답 status code: {response.status_code}")
            print(f"[DEBUG] 응답 본문: {response.text}")
            response.raise_for_status()
            data = response.json()

        if data.get("response", {}).get("header", {}).get("resultCode") != "0000":
            return json.dumps({"error": data.get("response", {}).get("header", {}).get("resultMsg", "알 수 없는 오류")}, ensure_ascii=False)

        items_container = data.get("response", {}).get(
            "body", {}).get("items", "")
        if isinstance(items_container, dict):
            items = items_container.get("item", [])
        elif not items_container:
            items = []
        else:
            items = items_container

        if not items:
            return json.dumps({"message": "검색 결과가 없습니다."}, ensure_ascii=False)

        canonical_results = [
            transform_kto_to_canonical(item) for item in items]
        return json.dumps(canonical_results, ensure_ascii=False, indent=2)

    except httpx.HTTPError as e:
        print(f"[ERROR] httpx.HTTPError: {e!r}")
        print(f"[ERROR] type: {type(e)}")
        print(traceback.format_exc())
        if hasattr(e, 'request'):
            print(f"[ERROR] 요청 정보: {getattr(e, 'request', None)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[ERROR] 응답 status code: {e.response.status_code}")
            print(f"[ERROR] 응답 본문: {e.response.text}")
        return json.dumps({"error": f"API 요청 중 오류 발생: {e!r}"}, ensure_ascii=False)
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[ERROR] JSONDecodeError/KeyError: {e}")
        if 'response' in locals():
            print(f"[ERROR] 응답 원문: {response.text}")
        return json.dumps({"error": f"API 응답 처리 중 오류 발생: {e}"}, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Exception: {e!r}")
        print(f"[ERROR] type: {type(e)}")
        print(traceback.format_exc())
        return json.dumps({"error": f"알 수 없는 오류 발생: {e!r}"}, ensure_ascii=False)


async def search_cultural_events(
    sido: str,
    from_date: str,
    to_date: str,
    sigungu: str = "",
    keyword: str = "",
    serviceTp: str = ""
) -> str:
    """한국문화정보원 API를 호출하여 문화 행사를 검색합니다.

    기간과 지역을 기반으로 문화 행사(공연, 전시, 축제 등) 정보를 조회하고,
    XML 응답을 파싱하여 결과를 JSON 형식의 문자열로 반환합니다.

    Args:
        sido (str): 검색할 시/도 이름 (예: '서울').
        from_date (str): 검색 시작일 (YYYY-MM-DD).
        to_date (str): 검색 종료일 (YYYY-MM-DD).
        sigungu (str, optional): 시/군/구 이름 (예: '종로구'). Defaults to "".
        keyword (str, optional): 검색할 키워드. Defaults to "".
        serviceTp (str, optional): 분야 구분 코드 (A:공연/전시, B:행사/축제,
                                   C:교육/체험). Defaults to "".

    Returns:
        str: 검색 결과를 표준 데이터 모델로 변환한 후 직렬화한 JSON 문자열.
             오류 발생 시 오류 정보를 담은 JSON 문자열을 반환합니다.
    """
    print(
        f"  [도구 실행] search_cultural_events(sido='{sido}', from='{from_date}', to='{to_date}', ...)")
    if KR_CULTURE_API_KEY == "DUMMY_KEY":
        return json.dumps({"error": "한국문화정보원 API 키가 없어 실제 호출을 할 수 없습니다."})

    base_url = "http://apis.data.go.kr/B553457/cultureinfo/area2"
    params = {
        "serviceKey": KR_CULTURE_API_KEY, "numOfrows": 3, "pageNo": 1,
        "sido": quote(sido),
        "from": from_date.replace("-", ""),
        "to": to_date.replace("-", ""),
        "sigungu": quote(sigungu) if sigungu else "",
        "keyword": quote(keyword) if keyword else "",
        "serviceTp": serviceTp,
        "sortStdr": "1",  # 1:등록일, 2:공연명, 3:지역
    }

    try:
        print(f"[DEBUG] 요청 URL: {base_url}")
        print(f"[DEBUG] 요청 파라미터: {params}")
        query_string = urlencode(
            {k: v for k, v in params.items() if v}, safe='%')
        full_url = f"{base_url}?{query_string}"
        print(f"[DEBUG] 최종 요청 URL: {full_url}")
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(full_url)
            print(f"[DEBUG] 응답 status code: {response.status_code}")
            print(f"[DEBUG] 응답 본문: {response.text}")
            response.raise_for_status()

            root = ET.fromstring(response.content)

        if root.find(".//resultCode").text != "00":
            return json.dumps({"error": root.find(".//resultMsg").text}, ensure_ascii=False)

        items = []
        for item_node in root.findall(".//item"):
            item_dict = {child.tag: child.text for child in item_node}
            items.append(item_dict)

        if not items:
            return json.dumps({"message": "검색 결과가 없습니다."}, ensure_ascii=False)

        canonical_results = [
            transform_kcis_to_canonical(item) for item in items]
        return json.dumps(canonical_results, ensure_ascii=False, indent=2)

    except httpx.HTTPError as e:
        print(f"[ERROR] httpx.HTTPError: {e!r}")
        print(f"[ERROR] type: {type(e)}")
        print(traceback.format_exc())
        if hasattr(e, 'request'):
            print(f"[ERROR] 요청 정보: {getattr(e, 'request', None)}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"[ERROR] 응답 status code: {e.response.status_code}")
            print(f"[ERROR] 응답 본문: {e.response.text}")
        return json.dumps({"error": f"API 요청 중 오류 발생: {e!r}"}, ensure_ascii=False)
    except ET.ParseError as e:
        print(f"[ERROR] XML ParseError: {e!r}")
        print(f"[ERROR] type: {type(e)}")
        print(traceback.format_exc())
        if 'response' in locals():
            print(f"[ERROR] 응답 원문: {response.text}")
        return json.dumps({"error": f"XML 파싱 중 오류 발생: {e!r}"}, ensure_ascii=False)
    except Exception as e:
        print(f"[ERROR] Exception: {e!r}")
        print(f"[ERROR] type: {type(e)}")
        print(traceback.format_exc())
        return json.dumps({"error": f"알 수 없는 오류 발생: {e!r}"}, ensure_ascii=False)


# --- 3. AI 오케스트레이션 계층: LLM 설정 및 대화 흐름 제어 ---

# 3.1. LLM에게 제공할 도구(함수) 목록 정의
tools = [
    {"type": "function", "function": {
        "name": "search_tourist_info",
        "description": "키워드, 지역, 콘텐츠 유형을 기반으로 한국의 관광 정보를 검색합니다. 사용자가 가볼만한 곳을 찾는다면 이 함수가 도움이 될 수 있습니다.",
        "parameters": {"type": "object", "properties": {
            "keyword": {"type": "string", "description": "검색할 키워드"},
            "area_code": {"type": "string", "enum": ["1", "2", "3", "4", "5", "6", "7", "8", "31", "32", "33", "34", "35", "36", "37", "38", "39"],
                          "description": "지역 코드: 1=서울, 2=인천, 3=대전, 4=대구, 5=광주, 6=부산, 7=울산, 8=세종, 31=경기도, 32=강원도, 33=충청북도, 34=충청남도, 35=경상북도, 36=경상남도, 37=전라북도, 38=전라남도, 39=제주도"},
        }, "required": ["keyword"]}
    }},
    # {"type": "function", "function": {
    #     "name": "search_cultural_events",
    #     "description": "특정 기간과 지역의 문화 행사(공연, 전시, 축제)를 검색합니다.",
    #     "parameters": {"type": "object", "properties": {
    #         "sido": {"type": "string", "description": "검색할 지역의 시/도 이름 (예: '서울', '부산', '제주')"},
    #         "from_date": {"type": "string", "description": "검색 시작일 (YYYY-MM-DD 형식)"},
    #         "to_date": {"type": "string", "description": "검색 종료일 (YYYY-MM-DD 형식)"},
    #         "sigungu": {"type": "string", "description": "시/군/구 이름 (예: '종로구', '해운대구')"},
    #         "keyword": {"type": "string", "description": "검색할 키워드 (예: '클래식', '미술관')"},
    #         "serviceTp": {"type": "string", "enum": ["A", "B", "C"], "description": "분야 구분(A:공연/전시, B:행사/축제, C:교육/체험)"}
    #     }, "required": ["sido", "from_date", "to_date"]}
    # }}
]

# 3.2. 인자 변환을 위한 유틸리티
AREA_CODE_MAP = {
    "서울": "1", "인천": "2", "대전": "3", "대구": "4", "광주": "5", "부산": "6", "울산": "7",
    "세종": "8", "경기도": "31", "경기": "31", "강원도": "32", "강원": "32", "충청북도": "33", "충북": "33",
    "충청남도": "34", "충남": "34", "경상북도": "35", "경북": "35", "경상남도": "36", "경남": "36",
    "전라북도": "37", "전북": "37", "전라남도": "38", "전남": "38", "제주도": "39", "제주": "39"
}
CONTENT_TYPE_MAP = {
    "관광지": "12", "명소": "12", "문화시설": "14", "박물관": "14", "미술관": "14",
    "행사": "15", "공연": "15", "축제": "15",
    "레포츠": "28", "스포츠": "28", "숙소": "32", "호텔": "32",
    "쇼핑": "38", "맛집": "39", "음식점": "39", "식당": "39", "카페": "39"
}
SERVICE_TYPE_MAP = {
    "공연": "A", "전시": "A",
    "행사": "B", "축제": "B",
    "교육": "C", "체험": "C", "강좌": "C"
}


def preprocess_arguments(function_name: str, args: dict, query: str) -> dict:
    """LLM이 생성한 인자를 API 호출에 적합한 형식으로 전처리합니다.

    사용자의 자연어(예: '서울', '이번 주말', '축제')를 기반으로
    API가 요구하는 코드 값(예: '1', '2025-07-05', 'B')으로 변환합니다.

    Args:
        function_name (str): 호출될 함수의 이름.
        args (dict): LLM이 생성한, 전처리 전의 인자 딕셔너리.
        query (str): 사용자의 원본 질문 문자열.

    Returns:
        dict: API 호출에 사용될, 전처리 후의 인자 딕셔너리.
    """
    processed_args = args.copy()

    if function_name == "search_tourist_info":
        if not processed_args.get("area_code"):
            for loc, code in AREA_CODE_MAP.items():
                if loc in query or loc in processed_args.get("keyword", ""):
                    processed_args["area_code"] = code
                    break

    elif function_name == "search_cultural_events":
        today = datetime.now()
        if "오늘" in query:
            processed_args["from_date"] = today.strftime("%Y-%m-%d")
            processed_args["to_date"] = today.strftime("%Y-%m-%d")
        elif "주말" in query:
            saturday = today + timedelta(days=(5 - today.weekday() + 7) % 7)
            sunday = saturday + timedelta(days=1)
            processed_args["from_date"] = saturday.strftime("%Y-%m-%d")
            processed_args["to_date"] = sunday.strftime("%Y-%m-%d")

        if not processed_args.get("serviceTp"):
            for type_name, type_code in SERVICE_TYPE_MAP.items():
                if type_name in query:
                    processed_args["serviceTp"] = type_code
                    break
    return processed_args


async def run_conversation(user_query: str, messages: List[Dict[str, Any]]) -> str:
    """사용자 질문에 대해 AI 에이전트와의 대화를 한 턴 실행합니다.

    이 함수는 전체 오케스트레이션 흐름을 관장합니다:
    1. LLM에 도구 사용 여부 및 방법을 질문합니다.
    2. LLM의 결정에 따라 도구(API)를 실행합니다.
    3. 도구 실행 결과를 다시 LLM에 전달하여 최종 답변을 생성합니다.

    Args:
        user_query (str): 사용자의 질문.
        messages (List[Dict[str, Any]]): 이전 대화 기록이 담긴 리스트.
                                          대화의 맥락을 유지하는 데 사용됩니다.

    Returns:
        str: 에이전트가 생성한 최종 답변 문자열.
    """
    if not client:
        return "OpenAI 클라이언트가 초기화되지 않았습니다. API 키를 확인해주세요."

    print(f"👤 사용자: {user_query}")
    messages.append({"role": "user", "content": user_query})

    response = client.chat.completions.create(
        model="gpt-4o", messages=messages, tools=tools, tool_choice="auto"
    )
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        print("  [LLM 판단] 도구 사용 결정 됨.")
        available_functions = {"search_tourist_info": search_tourist_info,
                               "search_cultural_events": search_cultural_events}
        messages.append(response_message)

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_to_call = available_functions[function_name]
            function_args = json.loads(tool_call.function.arguments)

            processed_args = preprocess_arguments(
                function_name, function_args, user_query)

            function_response = await function_to_call(**processed_args)
            print(f"  [도구 결과]\n{function_response}\n")
            messages.append({"tool_call_id": tool_call.id, "role": "tool",
                            "name": function_name, "content": function_response})

        second_response = client.chat.completions.create(
            model="gpt-4o", messages=messages)
        final_response = second_response.choices[0].message.content
    else:
        print("  [LLM 판단] 도구 사용 없이 자체 답변 결정.")
        final_response = response_message.content

    messages.append({"role": "assistant", "content": final_response})
    return final_response


if __name__ == "__main__":
    # 시스템 프롬프트: 에이전트의 역할과 행동 지침 정의
    system_prompt = f"""
    당신은 대한민국 여행 전문가 AI 어시스턴트 '여행비서'입니다. 
    사용자의 질문을 이해하고, 제공된 도구를 사용하여 정확한 정보를 찾은 후,
    이를 바탕으로 친절하고 유용한 답변을 생성해야 합니다.
    - 오늘 날짜는 {datetime.now()} 입니다.
    - 항상 제공된 도구(함수)를 통해서만 정보를 찾아야 하며, 추측으로 답변하지 마세요.
    - API 결과가 JSON 형식으로 제공되면, 그 데이터를 사람이 읽기 쉬운 형태로 
      가공하여 설명해주세요.
    - 추천할 때는 각 장소의 핵심적인 특징과 장점을 요약해서 알려주세요.
    - 날짜 관련 질문(예: '이번 주말')이 들어오면 오늘 날짜를 기준으로 정확한 날짜를
      계산해서 함수를 호출해야 합니다.
    - API 호출 결과 '검색 결과가 없습니다.'가 나오면, 사용자에게 정중하게 다른
      검색어를 제안해주세요.
    """

    async def run_scenario(scenario_title: str, queries: List[str]) -> None:
        """테스트 시나리오를 실행하고 결과를 출력합니다.

        각 시나리오는 독립적인 대화 기록을 가지며, 순차적으로 실행됩니다.

        Args:
            scenario_title (str): 실행할 시나리오의 제목.
            queries (List[str]): 시나리오 내에서 실행될 사용자 질문들의 리스트.
        """
        print("\n" + "="*60)
        print(f"🎬 시나리오 시작: {scenario_title}")
        print("="*60)
        conversation_history = [{"role": "system", "content": system_prompt}]
        for query in queries:
            final_response = await run_conversation(query, conversation_history)
            print(f"🤖 여행비서:\n{final_response}\n")
            print("--- (대화 턴 종료) ---")

    async def main():
        # --- 시나리오 실행 부 ---
        await run_scenario(
            "문화정보 API 실제 호출 테스트 (XML 파싱)",
            ["7월에 경기도에서 볼만한 축제나 행사가 있나?"]
        )

        await run_scenario(
            "반려동물 동반 가능 장소 검색",
            ["강원도에서 강아지랑 같이 갈만한 곳 알려줘"]
        )

        await run_scenario(
            "대화 맥락 유지 및 후속 질문 처리",
            [
                "서울에 있는 유명한 미술관 2곳만 알려줘.",
                "좋아. 그럼 첫 번째로 알려준 곳은 주차가 가능해? (이 정보는 API에 없으므로 '알 수 없음'으로 답변해야 함)"
            ]
        )
        await run_scenario(
            "목적성 약한 질문",
            [
                "주말에 가볼만한데 없나?"]
        )
    asyncio.run(main())
