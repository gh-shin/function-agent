import datetime
import os.path
from typing import Optional, List, Dict, Any, Union

from langchain_core.tools import tool

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


SCOPES = ["https://www.googleapis.com/auth/calendar.events"]
CREDENTIALS_FILE_PATH = "credentials.json"
TOKENS_FILE_PATH = "token.json"


def get_calendar_service():
    """Google Calendar API 서비스 객체를 인증하고 반환하는 헬퍼 함수"""
    creds = None
    if os.path.exists(TOKENS_FILE_PATH):
        creds = Credentials.from_authorized_user_file(TOKENS_FILE_PATH, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE_PATH, SCOPES
                )
                creds = flow.run_local_server(port=0)
            except FileNotFoundError:
                raise FileNotFoundError(
                    f"Error: '{CREDENTIALS_FILE_PATH}' 파일이 없습니다. Google Cloud Console에서 다운로드하여 프로젝트 루트에 배치해주세요."
                )
        with open(TOKENS_FILE_PATH, "w") as token:
            token.write(creds.to_json())
    return build("calendar", "v3", credentials=creds)


@tool
def create_calendar_event(
    summary: str,
    start_time_str: str,
    end_time_str: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Google 캘린더에 새로운 이벤트를 생성합니다. 시간은 반드시 'YYYY-MM-DDTHH:MM:SS' 형식이어야 합니다.
    예: '2024-05-15T10:00:00'
    """
    try:
        service = get_calendar_service()
        event = {
            "summary": summary,
            "description": description,
            "location": location,
            "start": {"dateTime": start_time_str, "timeZone": "Asia/Seoul"},
            "end": {"dateTime": end_time_str, "timeZone": "Asia/Seoul"},
            "attendees": [{"email": email} for email in attendees] if attendees else [],
            "reminders": {
                "useDefault": False,
                "overrides": [{"method": "popup", "minutes": 10}],
            },
        }
        created_event = (
            service.events().insert(calendarId="primary", body=event).execute()
        )
        print(f"이벤트 생성됨: {created_event.get('htmlLink')}")
        return {
            "status": "success",
            "id": created_event.get("id"),
            "summary": created_event.get("summary"),
            "htmlLink": created_event.get("htmlLink"),
        }
    except Exception as e:
        return {"error": f"이벤트 생성 중 오류 발생: {e}"}


@tool
def list_calendar_events(
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
    keyword: Optional[str] = None,
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """
    사용자의 스케쥴이나, 특정 시간에 있었을 장소를 추론할때 활용할 수 있는 함수입니다. 
    특정 기간이나 키워드로 Google 캘린더의 이벤트를 조회합니다. 날짜는 'YYYY-MM-DD' 형식이어야 합니다.
    오늘 날짜를 기준으로 조회하려면 start_date_str을 지정하지 마세요.
    """
    try:
        service = get_calendar_service()
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        time_min = f"{start_date_str}T00:00:00+09:00" if start_date_str else now
        time_max = f"{end_date_str}T23:59:59+09:00" if end_date_str else None

        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=time_min,
                timeMax=time_max,
                q=keyword,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            return {"message": "해당 조건에 맞는 이벤트가 없습니다."}

        simplified_events = [
            {
                "id": event["id"],
                "summary": event.get("summary", "제목 없음"),
                "start": event["start"].get("dateTime", event["start"].get("date")),
                "end": event["end"].get("dateTime", event["end"].get("date")),
                "location": event.get("location", "장소 미정"),
            }
            for event in events
        ]
        return simplified_events
    except Exception as e:
        return {"error": f"이벤트 조회 중 오류 발생: {e}"}


@tool
def modify_calendar_event(
    event_id: str,
    summary: Optional[str] = None,
    start_time_str: Optional[str] = None,
    end_time_str: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
) -> Dict[str, Any]:
    """
    기존 Google 캘린더 이벤트를 ID로 찾아 수정합니다. 수정할 필드만 인자로 전달하세요.
    시간 형식은 'YYYY-MM-DDTHH:MM:SS' 입니다.
    """
    try:
        service = get_calendar_service()
        event = service.events().get(calendarId="primary", eventId=event_id).execute()

        if summary:
            event["summary"] = summary
        if description:
            event["description"] = description
        if location:
            event["location"] = location
        if start_time_str:
            event["start"]["dateTime"] = start_time_str
        if end_time_str:
            event["end"]["dateTime"] = end_time_str

        updated_event = (
            service.events()
            .update(calendarId="primary", eventId=event_id, body=event)
            .execute()
        )
        print(f"이벤트 수정됨: {updated_event.get('htmlLink')}")
        return {
            "status": "success",
            "id": updated_event.get("id"),
            "summary": updated_event.get("summary"),
            "htmlLink": updated_event.get("htmlLink"),
        }
    except Exception as e:
        return {"error": f"이벤트 수정 중 오류 발생: {e}"}


@tool
def delete_calendar_event(event_id: str) -> Dict[str, str]:
    """
    ID를 사용하여 Google 캘린더에서 특정 이벤트를 삭제합니다.
    """
    try:
        service = get_calendar_service()
        service.events().delete(calendarId="primary", eventId=event_id).execute()
        print(f"이벤트 ID {event_id} 삭제됨.")
        return {
            "status": "success",
            "message": f"이벤트 ID {event_id}가 성공적으로 삭제되었습니다.",
        }
    except Exception as e:
        return {"error": f"이벤트 삭제 중 오류 발생: {e}"}
