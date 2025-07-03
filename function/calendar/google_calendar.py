from ..tools import (
    google_calendar_create_event,
    google_calendar_search_events,
    google_calendar_modify_event,
    google_calendar_delete_event
)
import datetime
import os.path
import json
from typing import Optional, List, Dict, Any, Union

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import openai
# OpenAI API 키 설정 (환경 변수 또는 직접 입력)
# 실제 배포 시에는 환경 변수를 사용하는 것이 보안상 권장됩니다.
openai_api_key = os.getenv("OPENAI_API_KEY")
client = openai.OpenAI(api_key=openai_api_key)

# tools.py 파일에서 정의된 도구 목록을 가져옵니다.

# Google Calendar API 스코프 정의 (이벤트 생성, 수정, 삭제 권한)
# CALENDAR_EVENTS: 캘린더 이벤트에 대한 읽기/쓰기 권한.
# CALENDAR_READONLY: 캘린더 이벤트에 대한 읽기 전용 권한 (필요에 따라 추가).
SCOPES = ['https://www.googleapis.com/auth/calendar.events']

# Google API 인증 정보 (tokens.json)가 저장될 디렉토리 경로
TOKENS_DIRECTORY_PATH = ''

# Google Cloud Console에서 다운로드한 credentials.json 파일 경로
# 이 파일은 프로젝트의 루트 또는 적절한 리소스 폴더에 있어야 합니다.
CREDENTIALS_FILE_PATH = 'credentials.json'


def get_calendar_service():
    """
    Google Calendar API 서비스 객체를 반환합니다.
    OAuth2 인증 흐름을 처리하여 Credential을 얻습니다.

    이 함수는 사용자의 Google 계정 인증을 처리합니다.
    최초 실행 시 웹 브라우저를 통해 인증을 요청하며,
    인증이 완료되면 'tokens.json' 파일에 인증 정보를 저장하여
    이후 호출 시에는 재인증 없이 사용합니다.

    Returns:
        googleapiclient.discovery.Resource: Google Calendar API 서비스 객체.

    Raises:
        FileNotFoundError: 'credentials.json' 파일이 없을 경우 발생.
        HttpError: Google API 호출 중 오류가 발생할 경우 발생.
    """
    creds = None
    # 1. 기존 인증 정보 확인:
    # 'tokens.json' 파일이 존재하면 이전에 저장된 인증 정보를 로드합니다.
    # 이를 통해 애플리케이션을 다시 실행할 때마다 사용자에게 재인증을 요청할 필요가 없습니다.
    if os.path.exists('tokens.json'):
        creds = Credentials.from_authorized_user_file('tokens.json', SCOPES)

    # 2. 인증 정보 유효성 검사 및 새로고침:
    # 인증 정보가 없거나, 유효하지 않거나 (예: 만료된 경우), 새로고침이 필요한 경우
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # 토큰이 만료되었지만 새로고침 토큰이 있는 경우, 토큰을 새로고침합니다.
            # 이 과정은 백그라운드에서 자동으로 진행될 수 있습니다.
            creds.refresh(Request())
        else:
            # 3. 새로운 인증 흐름 시작:
            # 'credentials.json' 파일에서 클라이언트 ID와 시크릿을 로드하여
            # OAuth 2.0 인증 흐름을 시작합니다.
            # `InstalledAppFlow.from_client_secrets_file`은 로컬에 설치된
            # 애플리케이션을 위한 인증 흐름을 생성합니다.
            # `run_local_server(port=0)`는 사용자가 인증을 완료할 때 Google로부터
            # 리디렉션될 로컬 웹 서버를 동적으로 할당된 포트에 띄웁니다.
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE_PATH, SCOPES)
                creds = flow.run_local_server(port=0)
            except FileNotFoundError:
                raise FileNotFoundError(f"Error: '{CREDENTIALS_FILE_PATH}' 파일이 없습니다. "
                                        "Google Cloud Console에서 다운로드하여 프로젝트 루트에 배치해주세요.")

        # 4. 새로 얻은 인증 정보 저장:
        # 새로 얻거나 새로고침된 인증 정보를 'tokens.json' 파일에 저장합니다.
        # 다음 실행부터 이 파일을 사용하여 재인증을 피할 수 있습니다.
        with open('tokens.json', 'w') as token:
            token.write(creds.to_json())

    # 5. Calendar API 서비스 객체 빌드 및 반환:
    # 얻은 인증 정보를 사용하여 Google Calendar API 서비스 객체를 빌드합니다.
    # 이 객체를 통해 실제 캘린더 API 호출을 수행할 수 있습니다.
    return build('calendar', 'v3', credentials=creds)


def create_calendar_event(
    summary: str,
    start_time_str: str,
    end_time_str: str,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Google 캘린더에 새로운 이벤트를 생성합니다.

    Args:
        summary (str): 이벤트의 제목입니다.
        start_time_str (str): 이벤트의 시작 시간 (ISO 8601 형식, 예: "2025-07-01T10:00:00+09:00").
        end_time_str (str): 이벤트의 종료 시간 (ISO 8601 형식, 예: "2025-07-01T11:00:00+09:00").
        description (str, optional): 이벤트의 상세 설명입니다. Defaults to None.
        location (str, optional): 이벤트가 열리는 장소입니다. Defaults to None.
        attendees (list, optional): 이벤트에 초대할 참석자 이메일 주소 목록입니다. Defaults to None.

    Returns:
        dict: 생성된 이벤트의 정보. 주요 필드는 다음과 같습니다.
            {
                'id': str,  # 이벤트 ID
                'summary': str,  # 이벤트 제목
                'description': str,  # 이벤트 설명
                'location': str,  # 장소
                'start': dict,  # 시작 시간 정보
                'end': dict,    # 종료 시간 정보
                'htmlLink': str,  # 구글 캘린더 웹 링크
                ... (Google Calendar API의 기타 필드)
            }
        오류 발생 시 {'error': str} 형태의 딕셔너리 반환

    Example:
        {
            'id': 'abc123',
            'summary': '회의',
            'description': '팀 미팅',
            'location': '서울',
            'start': {'dateTime': '2025-07-01T10:00:00+09:00', ...},
            'end': {'dateTime': '2025-07-01T11:00:00+09:00', ...},
            'htmlLink': 'https://calendar.google.com/calendar/event?eid=...',
            ...
        }
    """
    try:
        service = get_calendar_service()

        event = {
            'summary': summary,
            'description': description,
            'location': location,
            'start': {
                'dateTime': start_time_str,
                'timeZone': 'Asia/Seoul',  # 한국 시간대
            },
            'end': {
                'dateTime': end_time_str,
                'timeZone': 'Asia/Seoul',  # 한국 시간대
            },
            'reminders': {
                'useDefault': False,  # 기본 알림 설정 사용 안함
                'overrides': [
                    {'method': 'email', 'minutes': 24 * 60},  # 24시간 전 이메일 알림
                    {'method': 'popup', 'minutes': 10},     # 10분 전 팝업 알림
                ],
            },
        }

        # 'primary' 캘린더는 인증된 사용자의 기본 캘린더를 의미합니다.
        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"이벤트 생성됨: {event.get('htmlLink')}, 이벤트 ID: {event.get('id')}")
        # 이벤트 ID를 명확히 반환
        return {**event, "id": event.get("id")}

    except HttpError as error:
        print(f"이벤트 생성 중 오류 발생: {error}")
        return {"error": str(error)}
    except FileNotFoundError as error:
        print(f"인증 파일 오류: {error}")
        return {"error": str(error)}
    except Exception as e:
        print(f"예기치 않은 오류 발생: {e}")
        return {"error": str(e)}


def list_calendar_events(
    start_date_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
    keyword: Optional[str] = None
) -> Union[List[Dict[str, Any]], Dict[str, str]]:
    """
    Google 캘린더에서 이벤트를 조회합니다.

    Args:
        start_date_str (str, optional): 조회 시작 날짜 (ISO 8601 형식, 예: "2025-07-01"). Defaults to None.
        end_date_str (str, optional): 조회 종료 날짜 (ISO 8601 형식, 예: "2025-07-31"). Defaults to None.
        keyword (str, optional): 이벤트 제목이나 설명에서 검색할 키워드입니다. Defaults to None.

    Returns:
        list: 조회된 이벤트 목록. 각 이벤트는 다음과 같은 필드를 포함합니다.
            [
                {
                    'id': str,  # 이벤트 ID
                    'summary': str,  # 이벤트 제목
                    'start': str,    # 시작 시간 (ISO 8601)
                    'end': str,      # 종료 시간 (ISO 8601)
                    'location': str, # 장소
                    'description': str, # 설명
                },
                ...
            ]
        오류 발생 시 {'error': str} 형태의 딕셔너리 반환

    Example:
        [
            {
                'id': 'abc123',
                'summary': '회의',
                'start': '2025-07-01T10:00:00+09:00',
                'end': '2025-07-01T11:00:00+09:00',
                'location': '서울',
                'description': '팀 미팅'
            },
            ...
        ]
    """
    try:
        service = get_calendar_service()

        # 현재 시간 (UTC)을 ISO 8601 형식으로 변환하여 기본 조회 시작 시간으로 사용
        now = datetime.datetime.now(datetime.timezone.utc).isoformat() + 'Z'

        # timeMin: 조회 시작 시간 (ISO 8601). start_date_str이 제공되면 해당 날짜의 00:00:00으로 설정.
        # timeMax: 조회 종료 시간 (ISO 8601). end_date_str이 제공되면 해당 날짜의 23:59:59으로 설정.
        # singleEvents=True: 반복 이벤트를 개별 이벤트로 확장하여 반환합니다.
        # orderBy='startTime': 이벤트들을 시작 시간 순으로 정렬합니다.
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_date_str + 'T00:00:00+09:00' if start_date_str else now,
            timeMax=end_date_str + 'T23:59:59+09:00' if end_date_str else None,
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        events = events_result.get('items', [])

        filtered_events = []
        if not events:
            print("조회된 이벤트가 없습니다.")
        else:
            for event in events:
                # 키워드 필터링 로직: Google API 자체 검색 기능도 있지만, 여기서는 Python에서 간단히 처리
                # summary 또는 description에 키워드가 포함되어 있는지 확인
                if keyword:
                    summary_match = keyword.lower() in event.get('summary', '').lower()
                    description_match = keyword.lower() in event.get('description', '').lower()
                    if not (summary_match or description_match):
                        continue

                # 이벤트 시작/종료 시간 추출 (dateTime 또는 date 필드 사용)
                start = event['start'].get(
                    'dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))

                # POI 시스템 연관: 이벤트에 장소 정보가 있다면 함께 출력하여 POI 추천에 활용 가능
                location = event.get('location', '장소 미정')

                # 사용자에게 보여줄 간략화된 이벤트 정보
                filtered_events.append({
                    "id": event['id'],
                    "summary": event.get('summary', '제목 없음'),
                    "start": start,
                    "end": end,
                    "location": location,
                    "description": event.get('description', '')
                })
                print(f"{event.get('summary')} ({start} - {end}) at {location}")

        return filtered_events

    except HttpError as error:
        print(f"이벤트 조회 중 오류 발생: {error}")
        return {"error": str(error)}
    except FileNotFoundError as error:
        print(f"인증 파일 오류: {error}")
        return {"error": str(error)}
    except Exception as e:
        print(f"예기치 않은 오류 발생: {e}")
        return {"error": str(e)}


def modify_calendar_event(
    event_id: str,
    summary: Optional[str] = None,
    start_time_str: Optional[str] = None,
    end_time_str: Optional[str] = None,
    description: Optional[str] = None,
    location: Optional[str] = None,
    attendees_to_add: Optional[List[str]] = None,
    attendees_to_remove: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Google 캘린더의 기존 이벤트를 수정합니다.

    Args:
        event_id (str): 수정할 이벤트의 ID입니다.
        summary (str, optional): 새로운 이벤트 제목입니다. Defaults to None.
        start_time_str (str, optional): 새로운 시작 시간 (ISO 8601 형식). Defaults to None.
        end_time_str (str, optional): 새로운 종료 시간 (ISO 8601 형식). Defaults to None.
        description (str, optional): 새로운 상세 설명입니다. Defaults to None.
        location (str, optional): 새로운 장소입니다. Defaults to None.
        attendees_to_add (list, optional): 추가할 참석자 이메일 주소 목록입니다. Defaults to None.
        attendees_to_remove (list, optional): 제거할 참석자 이메일 주소 목록입니다. Defaults to None.

    Returns:
        dict: 수정된 이벤트의 정보. 주요 필드는 다음과 같습니다.
            {
                'id': str,  # 이벤트 ID
                'summary': str,  # 이벤트 제목
                'description': str,  # 이벤트 설명
                'location': str,  # 장소
                'start': dict,  # 시작 시간 정보
                'end': dict,    # 종료 시간 정보
                'htmlLink': str,  # 구글 캘린더 웹 링크
                ... (Google Calendar API의 기타 필드)
            }
        오류 발생 시 {'error': str} 형태의 딕셔너리 반환

    Example:
        {
            'id': 'abc123',
            'summary': '수정된 회의',
            'description': '수정된 설명',
            'location': '서울',
            'start': {'dateTime': '2025-07-01T10:30:00+09:00', ...},
            'end': {'dateTime': '2025-07-01T11:30:00+09:00', ...},
            'htmlLink': 'https://calendar.google.com/calendar/event?eid=...',
            ...
        }
    """
    try:
        service = get_calendar_service()

        # 1. 기존 이벤트 정보 가져오기: 수정하려면 먼저 해당 이벤트의 현재 상태를 알아야 합니다.
        event = service.events().get(calendarId='primary', eventId=event_id).execute()

        # 2. 변경할 필드 업데이트: 전달된 인자가 None이 아닐 경우에만 해당 필드를 업데이트합니다.
        if summary is not None:
            event['summary'] = summary
        if description is not None:
            event['description'] = description
        if location is not None:
            event['location'] = location

        # 시작/종료 시간은 'start'/'end' 객체 내부의 'dateTime'을 수정합니다.
        if start_time_str is not None:
            # 기존 'start' 객체가 없으면 새로 생성 (안전장치)
            if 'start' not in event:
                event['start'] = {'timeZone': 'Asia/Seoul'}
            event['start']['dateTime'] = start_time_str
        if end_time_str is not None:
            # 기존 'end' 객체가 없으면 새로 생성 (안전장치)
            if 'end' not in event:
                event['end'] = {'timeZone': 'Asia/Seoul'}
            event['end']['dateTime'] = end_time_str

        # 3. 참석자 업데이트:
        # 기존 참석자 목록을 가져와서 추가/제거 요청을 반영합니다.
        current_attendees = event.get('attendees', [])
        # 현재 참석자들의 이메일 주소만 집합(set)으로 만들어 중복 처리 및 빠른 검색 준비
        current_attendee_emails = {
            att.get('email') for att in current_attendees if att.get('email')}

        if attendees_to_add:
            for email in attendees_to_add:
                if email not in current_attendee_emails:
                    current_attendees.append({'email': email})
                    current_attendee_emails.add(email)  # 중복 방지를 위해 집합에도 추가

        if attendees_to_remove:
            # 제거할 참석자를 제외하고 새로운 목록을 만듭니다.
            current_attendees = [att for att in current_attendees if att.get(
                'email') not in attendees_to_remove]

        event['attendees'] = current_attendees

        # 4. API 호출: 수정된 이벤트 객체로 Google 캘린더의 이벤트를 업데이트합니다.
        updated_event = service.events().update(
            calendarId='primary', eventId=event_id, body=event).execute()
        print(f"이벤트 수정됨: {updated_event.get('htmlLink')}")
        return updated_event

    except HttpError as error:
        print(f"이벤트 수정 중 오류 발생: {error}")
        return {"error": str(error)}
    except FileNotFoundError as error:
        print(f"인증 파일 오류: {error}")
        return {"error": str(error)}
    except Exception as e:
        print(f"예기치 않은 오류 발생: {e}")
        return {"error": str(e)}


def delete_calendar_event(event_id: str) -> Dict[str, str]:
    """
    Google 캘린더에서 특정 이벤트를 삭제합니다.

    Args:
        event_id (str): 삭제할 이벤트의 ID입니다.

    Returns:
        dict: 삭제 성공 여부 메시지. 주요 필드는 다음과 같습니다.
            {
                'status': 'success',
                'message': '이벤트 ID abc123가 성공적으로 삭제되었습니다.'
            }
        오류 발생 시 {'error': str} 형태의 딕셔너리 반환

    Example:
        {'status': 'success', 'message': '이벤트 ID abc123가 성공적으로 삭제되었습니다.'}
    """
    try:
        service = get_calendar_service()

        # API 호출: 지정된 calendarId('primary')에서 eventId에 해당하는 이벤트를 삭제합니다.
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        print(f"이벤트 ID {event_id} 삭제됨.")
        return {"status": "success", "message": f"이벤트 ID {event_id}가 성공적으로 삭제되었습니다."}

    except HttpError as error:
        print(f"이벤트 삭제 중 오류 발생: {error}")
        return {"error": str(error)}
    except FileNotFoundError as error:
        print(f"인증 파일 오류: {error}")
        return {"error": str(error)}
    except Exception as e:
        print(f"예기치 않은 오류 발생: {e}")
        return {"error": str(e)}


def llm_ask(
    messages: list,
    tools: list = None,
    tool_choice: str = "auto"
) -> Any:
    """
    LLM에 메시지와 도구 목록을 전달하고 응답을 받는 함수

    Args:
        messages (list): LLM에 전달할 메시지 목록
        tools (list, optional): function calling에 사용할 도구 목록
        tool_choice (str, optional): 도구 선택 방식 (기본값: "auto")

    Returns:
        Any: LLM의 응답 객체
    """
    kwargs = {
        "model": "gpt-4.1",
        "messages": messages,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice
    response = client.chat.completions.create(**kwargs)
    return response


def execute_tool_calls(tool_calls: list) -> list:
    """
    LLM이 반환한 tool_calls를 실제 함수로 실행하고 결과를 반환하는 함수

    Args:
        tool_calls (list): LLM 응답에서 추출한 tool_calls 리스트

    Returns:
        list: 각 tool_call의 실행 결과 딕셔너리
    """
    available_functions = {
        "create_calendar_event": create_calendar_event,
        "list_calendar_events": list_calendar_events,
        "modify_calendar_event": modify_calendar_event,
        "delete_calendar_event": delete_calendar_event,
    }
    results = []
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        print(
            f"AI calls function '{function_name}' with args: {tool_call.function.arguments}")
        function_args = json.loads(tool_call.function.arguments)
        if function_name in available_functions:
            function_to_call = available_functions[function_name]
            function_response = function_to_call(**function_args)
        else:
            function_response = {"error": f"Unknown function: {function_name}"}
        results.append({
            "tool_call_id": tool_call.id,
            "name": function_name,
            "response": function_response
        })
    return results


def run_conversation(messages: list) -> str:
    """
    전체 대화 흐름을 orchestration하는 함수. LLM 질의, function call 실행, 최종 응답 생성만 담당.
    Args:
        messages (list): 대화 이력 메시지 리스트 (멀티턴 지원)
    Returns:
        str: ChatGPT의 최종 응답
    """
    tools = [
        google_calendar_create_event,
        google_calendar_search_events,
        google_calendar_modify_event,
        google_calendar_delete_event
    ]
    # 1단계: LLM에 질의
    response = llm_ask(messages, tools)
    response_message = response.choices[0].message
    messages.append(response_message)
    # 2단계: function call이 있으면 실행
    if response_message.tool_calls:
        tool_results = execute_tool_calls(response_message.tool_calls)
        # 3단계: 각 function call 결과를 메시지로 추가
        for result in tool_results:
            messages.append({
                "tool_call_id": result["tool_call_id"],
                "role": "tool",
                "name": result["name"],
                "content": json.dumps(result["response"]),
            })
        # 4단계: LLM에 최종 응답 생성 요청
        second_response = llm_ask(messages)
        messages.append(second_response.choices[0].message)
        return second_response.choices[0].message.content
    else:
        # function call 없이 바로 응답
        return response_message.content


def simulate_conversation_flow():
    """
    Google 캘린더 API와 ChatGPT Function Calling 통합의 전체 대화 플로우를 시뮬레이션합니다.
    """
    print("--- 대화 플로우 시뮬레이션 시작 ---")
    print("-" * 40)

    messages = [
        {"role": "system", "content": f"You are a helpful assistant about Google Calendar. Today is '{datetime.datetime.now()}'."},
    ]
    # --- 1단계: 이벤트 생성 ---
    print("\n[사용자] 이번 주 금요일 오후 1시에 친구랑 강남역 근처에서 점심 먹기로 했어. 캘린더에 추가해 줘.")
    user_query_create = f"이번 주 금요일 오후 1시에 친구랑 강남역 근처에서 점심 먹기로 했어. 캘린더에 추가해 줘. "
    messages.append({"role": "user", "content": user_query_create})
    # run_conversation 호출 및 응답 저장
    response_create = run_conversation(messages=messages)
    messages.append({"role": "assistant", "content": response_create})
    print(f"[AI 어시스턴트] {messages[-1]}")
    print("-" * 40)

    # --- 2단계: 이벤트 조회 ---
    print("\n[사용자] 이번 주 내 일정이 어떻게 돼?")
    # list_calendar_events 호출
    user_query_list = f"이번 주 내 일정이 어떻게 돼? "
    messages.append({"role": "user", "content": user_query_list})
    response_list = run_conversation(
        messages=messages
    )
    messages.append({"role": "assistant", "content": response_list})
    print(f"[AI 어시스턴트] {messages[-1]}")
    print("-" * 40)

    # --- 3단계: 이벤트 수정 ---
    print("\n[사용자] 아까 그 점심 약속, 30분 미뤄서 오후 1시 30분부터로 바꿔줘.")
    user_query_modify = f"아까 그 점심 약속, 30분 미뤄서 오후 1시 30분부터로 바꿔줘."
    messages.append({"role": "user", "content": user_query_modify})
    response_modify = run_conversation(messages=messages)
    messages.append({"role": "assistant", "content": response_modify})
    print(f"[AI 어시스턴트] {messages[-1]}")
    print("-" * 40)

    # --- 4단계: 이벤트 삭제 ---
    print(f"\n[사용자] 방금 그 점심 약속 취소됐어. 캘린더에서 지워줘.")
    user_query_delete = f"방금 그 점심 약속 취소됐어. 캘린더에서 지워줘."
    messages.append({"role": "user", "content": user_query_delete})
    response_delete = run_conversation(messages=messages)
    messages.append({"role": "assistant", "content": response_delete})
    print(f"[AI 어시스턴트] {messages[-1]}")

    # --- 5단계: 일정 요약 ---
    print(f"\n[사용자] 이번달의 중요한 일정들은 뭐가있지?")
    user_query_summary = f"이번달의 중요한 일정들은 뭐가있지?"
    messages.append({"role": "user", "content": user_query_summary})
    response_summary = run_conversation(messages=messages)
    messages.append({"role": "assistant", "content": response_summary})
    print(f"[AI 어시스턴트] {messages[-1]}")

    print("\n--- 대화 플로우 시뮬레이션 종료 ---")


# 스크립트 실행 시 simulate_conversation_flow 메서드 호출
if __name__ == "__main__":
    simulate_conversation_flow()

# # --- 실행 예시 ---
# if __name__ == "__main__":
#     # 사용자 요청 예시 1: 이벤트 생성
#     print("\n--- 이벤트 생성 요청 (POI 시스템 연동 예시) ---")
#     # POI 추천 시스템에서 사용자가 '강남역 맛집 A'를 방문하기로 결정했다고 가정합니다.
#     # 시스템은 해당 맛집의 정보 (이름, 주소, 추천 시간)를 가지고 있다고 가정합니다.
#     poi_name = "강남역 맛집 A"
#     poi_address = "서울 강남구 테헤란로 123"
#     # 현재 날짜 기준 다음 주 토요일 오후 7시부터 9시까지로 가정합니다.
#     # 실제 구현 시에는 사용자 입력이나 POI 시스템의 추천 로직을 통해 날짜/시간을 동적으로 결정합니다.
#     today = datetime.date.today()
#     # 다음 주 토요일 날짜 계산: (5 - 오늘 요일 + 7) % 7 --> 다음 주 토요일까지 남은 일수
#     # 예: 오늘이 수요일(2)이면 (5-2+7)%7 = 3 --> 3일 후 토요일 (이번 주 토요일)
#     #  -> 이 경우 +7을 해서 다음 주 토요일을 명확히 지정하거나, 실제 날짜 계산 로직을 더 견고히 해야 함.
#     # 간단히 datetime 모듈로 처리
#     next_saturday = today + \
#         datetime.timedelta(days=(5 - today.weekday() + 7) % 7 + 7)
#     start_time_iso = f"{next_saturday.isoformat()}T19:00:00+09:00"
#     end_time_iso = f"{next_saturday.isoformat()}T21:00:00+09:00"

#     user_query_poi = (
#         f"다음 주 토요일 저녁 7시에 '{poi_name}' 방문 일정을 잡아줘. "
#         f"주소는 '{poi_address}'야. 친구랑 같이 갈 거야."
#         f"시작 시간: {start_time_iso}, 종료 시간: {end_time_iso}"  # 명확한 시간 정보 제공
#     )
#     response_poi = run_conversation(user_query_poi)
#     print(f"모델 응답: {response_poi}")

#     # 사용자 요청 예시 2: 이벤트 조회
#     print("\n--- 이벤트 조회 요청 ---")
#     user_query_list = "내일 일정이 뭐야?"
#     # # user_query_list = "이번 주에 '회의'라는 키워드가 들어간 일정이 있는지 알려줘."
#     response_list = run_conversation(user_query_list)
#     print(f"모델 응답: {response_list}")

#     # 사용자 요청 예시 3: 이벤트 수정 (조회된 이벤트 ID가 필요)
#     # 실제 사용 시에는 list_calendar_events를 통해 얻은 event_id를 사용해야 합니다.
#     print("\n--- 이벤트 수정 요청 ---")
#     # !!! 여기에 실제 Google 캘린더에서 조회된 이벤트 ID를 넣어주세요. !!!
#     # 예: 'list_calendar_events'를 실행하여 얻은 ID
#     dummy_event_id_for_modify = "your_actual_event_id_for_modification"
#     user_query_modify = (
#         f"이벤트 ID '{dummy_event_id_for_modify}'의 제목을 '긴급 POI 회의'로 변경하고, "
#         f"시작 시간을 내일 오후 4시 30분으로 변경해줘. "
#         # 모델이 날짜를 유추하기 위한 힌트
#         f"내일 날짜: {datetime.date.today() + datetime.timedelta(days=1)}"
#     )
#     response_modify = run_conversation(user_query_modify)
#     print(f"모델 응답: {response_modify}")

#     # 사용자 요청 예시 4: 이벤트 삭제 (조회된 이벤트 ID가 필요)
#     print("\n--- 이벤트 삭제 요청 ---")
#     # !!! 여기에 실제 Google 캘린더에서 조회된 이벤트 ID를 넣어주세요. !!!
#     dummy_event_id_for_delete = "your_actual_event_id_for_deletion"
#     user_query_delete = f"이벤트 ID '{dummy_event_id_for_delete}'를 삭제해줘."
#     response_delete = run_conversation(user_query_delete)
#     print(f"모델 응답: {response_delete}")

#     print("\n--- 추가 테스트 ---")
#     # 이 테스트를 실행하려면 먼저 적절한 이벤트 ID로 'dummy_event_id_for_modify'와 'dummy_event_id_for_delete'를 바꿔야 합니다.
#     # 사용자가 event_id를 직접 제공하는 경우는 드물기 때문에,
#     # 보통은 "내일 회의 일정을 바꿔줘" -> (list_calendar_events 호출) -> "어떤 회의 말씀이신가요? ID: XYZ"
#     # -> 사용자가 ID를 알려주면 -> (modify_calendar_event 호출) 하는 식으로 2단계 대화가 필요합니다.
