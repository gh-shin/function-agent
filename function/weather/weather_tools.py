import os
import requests
import json
from dotenv import load_dotenv

from pydantic import BaseModel, Field
from langchain_core.tools import tool

load_dotenv()

weather_code_dict = {
    0: "맑음", 1: "대체로 맑음", 2: "부분적으로 흐림", 3: "흐림", 45: "안개", 48: "서리 안개",
    51: "가벼운 이슬비", 53: "보통 이슬비", 55: "짙은 이슬비", 56: "가벼운 동결 이슬비", 57: "짙은 동결 이슬비",
    61: "가벼운 비", 63: "보통 비", 65: "폭우", 66: "가벼운 동결 비", 67: "강한 동결 비",
    71: "가벼운 눈", 73: "보통 눈", 75: "폭설", 77: "소낙눈",
    80: "가벼운 소나기", 81: "보통 소나기", 82: "강한 소나기", 85: "가벼운 눈소나기", 86: "강한 눈소나기",
    95: "뇌우", 96: "가벼운 우박을 동반한 뇌우", 99: "강한 우박을 동반한 뇌우",
}


def get_location_points(location: str):
    """카카오맵 API를 사용하여 위치명을 위도, 경도로 변환하는 함수"""
    map_url = f"https://dapi.kakao.com/v2/local/search/keyword.json?page=1&size=1&sort=accuracy&query={location}"
    headers = {"Authorization": f"KakaoAK {os.getenv('KAKAO_REST_API_KEY')}"}
    try:
        response = requests.get(map_url, headers=headers)
        response.raise_for_status()
        results = response.json()
        if results.get("documents"):
            document = results["documents"][0]
            return round(float(document.get("y")), 4), round(float(document.get("x")), 4)
        else:
            return 37.3947, 127.1111 
    except Exception as e:
        print(f"카카오맵 API 오류: {e}")
        return 37.3947, 127.1111 


class WeatherInput(BaseModel):
    location: str = Field(description="날씨를 조회할 위치명, 예: '판교역', '강남역', '서울'")



@tool(args_schema=WeatherInput)
def get_weather(location: str) -> str:
    """
    지정한 위치의 현재 날씨와 14일간의 일일 예보를 조회합니다.
    '서울 날씨 알려줘'와 같은 사용자 요청에 응답할 때 사용하세요.
    """
    latitude, longitude = get_location_points(location)
    
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        f"¤t=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
        f"&daily=temperature_2m_max,temperature_2m_min,uv_index_max,wind_speed_10m_max,precipitation_probability_max,weather_code"
        f"&timezone=Asia%2FTokyo"
    )
    try:
        response = requests.get(weather_url)
        response.raise_for_status()
        data = response.json()

        current = data.get("current", {})
        current_units = data.get("current_units", {})
        daily = data.get("daily", {})
        daily_units = data.get("daily_units", {})

        current_result = {
            "location": location,
            "observation_time": current.get("time"),
            "temperature": f"{current.get('temperature_2m')}{current_units.get('temperature_2m', '')}",
            "humidity": f"{current.get('relative_humidity_2m')}{current_units.get('relative_humidity_2m', '')}",
            "wind_speed": f"{current.get('wind_speed_10m')}{current_units.get('wind_speed_10m', '')}",
            "weather": weather_code_dict.get(current.get("weather_code"), "Unknown"),
        }
        
        daily_result = []
        if daily and daily.get("time"):
            days = daily["time"]
            for i, day in enumerate(days):
                daily_result.append({
                    "date": day,
                    "temp_max": f"{daily.get('temperature_2m_max', [])[i]}{daily_units.get('temperature_2m_max', '')}",
                    "temp_min": f"{daily.get('temperature_2m_min', [])[i]}{daily_units.get('temperature_2m_min', '')}",
                    "uv_index_max": f"{daily.get('uv_index_max', [])[i]}",
                    "wind_speed_max": f"{daily.get('wind_speed_10m_max', [])[i]}{daily_units.get('wind_speed_10m_max', '')}",
                    "precipitation_probability": f"{daily.get('precipitation_probability_max', [])[i]}{daily_units.get('precipitation_probability_max', '')}",
                    "weather": weather_code_dict.get(daily.get('weather_code', [])[i], "Unknown"),
                })

        final_result = {"current_weather": current_result, "daily_forecast": daily_result}
        return json.dumps(final_result, ensure_ascii=False, indent=2)

    except requests.exceptions.RequestException as e:
        error_message = {"error": f"날씨 API 요청 중 오류가 발생했습니다: {e}"}
        return json.dumps(error_message, ensure_ascii=False, indent=2)
