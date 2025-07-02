from dotenv import load_dotenv
# 검색 위치의 좌표 찾기
import os
import requests
import json

load_dotenv()
weather_code_dict = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
    51: "Light Drizzle",
    53: "Moderate Drizzle",
    55: "Dense Intensity Drizzle",
    56: "Light Freezing Drizzle",
    57: "Dense Intensity Freeze Drizzle",
    61: "Slight Rain",
    63: "Moderate Rain",
    65: "Heavy intensity Rain",
    66: "Light Freezing Rain",
    67: "Heavy Intensity Freezing Drizzle",
    71: "Slight Snow fall",
    73: "Moderate Snow fall",
    75: "Heavy intensity Snow fall",
    77: "Snow grains",
    80: "Slight Rain Shower",
    81: "Moderate Rain Shower",
    82: "Violent Rain Shower",
    85: "Slight Snow Shower",
    86: "Heavy Snow Shower",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with Heavy hail",
}


def get_location_points(location):
    map_url = f"https://dapi.kakao.com/v2/local/search/keyword.json?page=1&size=15&sort=accuracy&query={location}"
    headers = {"Authorization": f"KakaoAK {os.getenv('KAKAO_REST_API_KEY')}"}

    try:
        tmp = requests.get(map_url, headers=headers)
        tmp.raise_for_status()
        results = json.loads(tmp.text)
        if results.get("documents"):
            latitude = results.get("documents")[0].get("y")
            longitude = results.get("documents")[0].get("x")
            return round(float(latitude), 4), round(float(longitude), 4)
        else:
            return str(37.3947), str(127.1111)
    except Exception as e:
        print(e)
        return None

# 해당 지역 날씨 찾기


def get_current_weather(location: str) -> dict:
    """
    지역의 현재 및 14일간의 날씨 정보를 반환합니다.

    Args:
        location (str): 날씨를 조회할 위치

    Returns:
        dict: 위치에 대한 현재 및 14일간의 일별 날씨 정보
    """
    latitude, longitude = get_location_points(location)
    weather_url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}&longitude={longitude}"
        f"&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"
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

        # 현재 날씨 변환
        current_result = {
            "location": location,
            "observation_time": current.get("time"),
            "temperature": f"{current.get('temperature_2m')}{current_units.get('temperature_2m', '')}",
            "humidity": f"{current.get('relative_humidity_2m')}{current_units.get('relative_humidity_2m', '')}",
            "wind_speed": f"{current.get('wind_speed_10m')}{current_units.get('wind_speed_10m', '')}",
            "weather": weather_code_dict.get(current.get("weather_code"), "Unknown"),
        }

        # 일별 날씨 변환
        daily_result = []
        if daily:
            days = daily.get("time", [])
            for i, day in enumerate(days):
                daily_result.append({
                    "date": day,
                    "temp_max": f"{daily.get('temperature_2m_max', [None]*len(days))[i]}{daily_units.get('temperature_2m_max', '')}",
                    "temp_min": f"{daily.get('temperature_2m_min', [None]*len(days))[i]}{daily_units.get('temperature_2m_min', '')}",
                    "uv_index_max": f"{daily.get('uv_index_max', [None]*len(days))[i]}",
                    "wind_speed_max": f"{daily.get('wind_speed_10m_max', [None]*len(days))[i]}{daily_units.get('wind_speed_10m_max', '')}",
                    "precipitation_probability": f"{daily.get('precipitation_probability_max', [None]*len(days))[i]}{daily_units.get('precipitation_probability_max', '')}",
                    "weather": weather_code_dict.get(daily.get('weather_code', [None]*len(days))[i], "Unknown"),
                })

        return {
            "current_weather": current_result,
            "daily_forecast": daily_result
        }
    except requests.exceptions.RequestException as e:
        print(f"API 요청 오류: {e}")
        return {}


weather_tool = {
    "type": "function",
    "name": "get_location_weather",
    "description": "Responds with the current weather and daily (14 days) forecast for the specified location.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The location name e.g. '판교역', '강남역', '서울'",
            }
        },
        "required": ["location"],
    },
}
if __name__ == "__main__":
    print(get_current_weather("서울"))
