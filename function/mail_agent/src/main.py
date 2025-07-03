from openai import OpenAI
import polars as pl
from langchain_openai import ChatOpenAI
import dotenv
import os 
dotenv.load_dotenv()

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import tool, AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from datetime import datetime, timedelta
load_dotenv()
from dateutil.parser import parse as parse_datetime  # <--- 이 줄을 추가!


# Google API 관련 라이브러리
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup
import base64
from email.mime.text import MIMEText

# Gmail API의 권한 범위를 지정합니다. 'readonly'는 읽기 전용 권한입니다.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    """Google 인증을 처리하고 Gmail API 서비스 객체를 반환하는 함수 (token.json 사용)"""
    creds = None
    # 'token.json' 파일은 사용자의 액세스 및 리프레시 토큰을 저장합니다.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    
    # 유효한 자격 증명이 없는 경우, 사용자가 로그인하도록 합니다.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # 토큰이 만료되었으면 리프레시합니다.
            creds.refresh(Request())
        else:
            # 새 인증을 위해 로그인 흐름을 시작합니다.
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        
        # 다음 실행을 위해 새 자격 증명(JSON 형식)을 저장합니다.
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    # API 서비스 객체를 빌드하여 반환합니다.
    service = build("gmail", "v1", credentials=creds)
    return service


def _process_message_list(service, list_results, include_body=False):
    """
    메시지 또는 초안의 API 리스트 결과를 받아, 사람이 이해하기 쉬운 상세 정보 리스트로 가공합니다.

    - service: 인증된 Gmail API 서비스 객체.
    - list_results: `users().messages().list()` 또는 `users().drafts().list()`의 결과 리스트.
    - include_body: True일 경우, 메일 본문 전체를 포함하여 반환합니다.
    """
    if not list_results:
        return []
    include_body=True
    processed_results = []
    num_items_to_process = 3 if include_body else 5
    for item_stub in list_results[:num_items_to_process]:
        try:
            resource_id = item_stub.get('id')
            is_draft = resource_id and resource_id.startswith('r')

            if is_draft:
                full_resource = service.users().drafts().get(userId='me', id=resource_id, format='full').execute()
                msg_data = full_resource.get('message', {})
                from_email = "나 (초안)"
            else: 
                msg_format = 'full' if include_body else 'metadata'
                msg_data = service.users().messages().get(userId='me', id=resource_id, format=msg_format).execute()
                headers_temp = msg_data.get('payload', {}).get('headers', [])
                from_email = next((h['value'] for h in headers_temp if h['name'].lower() == 'from'), 'N/A')

            if not msg_data:
                print(f"ID '{resource_id}'에 유효한 메시지 내용이 없어 건너뜁니다.")
                continue

            payload = msg_data.get('payload', {})
            headers = payload.get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '제목 없음')
            date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '날짜 정보 없음')

            result_item = {
                "id": resource_id,
                "type": "draft" if is_draft else "message",
                "from": from_email,
                "subject": subject,
                "snippet": msg_data.get('snippet', ''),
            }
            
            if include_body:
                body = ""
                if 'parts' in payload:
                    for part in payload['parts']:
                        # 일반 텍스트 본문을 우선적으로 찾습니다.
                        if part['mimeType'] == 'text/plain':
                            body_data = part.get('body', {}).get('data')
                            if body_data:
                                body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
                                break
                    # 텍스트 본문이 없는 경우, HTML 본문에서 텍스트를 추출합니다.
                    if not body:
                        for part in payload['parts']:
                            if part['mimeType'] == 'text/html':
                                html_body_data = part.get('body', {}).get('data')
                                if html_body_data:
                                    html_body = base64.urlsafe_b64decode(html_body_data).decode('utf-8', errors='replace')
                                    soup = BeautifulSoup(html_body, 'html.parser')
                                    body = soup.get_text(separator='\n', strip=True)
                                    break
                elif payload.get('body', {}).get('data'):
                    body_data = payload['body']['data']
                    body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='replace')
                
                result_item['body'] = body[:2000] # API 토큰 절약을 위해 길이 제한


            processed_results.append(result_item)

        except HttpError as e:
            print(f"ID '{item_stub.get('id')}' 처리 중 API 오류 발생: {e}")
            continue
        except Exception as e:
            print(f"ID '{item_stub.get('id')}' 처리 중 예상치 못한 오류 발생: {e}")
            continue
    return processed_results


@tool
def find_mails(
    sender: str = None,
    query: str = None,
    start_date: str = None,
    end_date: str = None,
    has_attachment: bool = None,
    is_unread: bool = None,
    exclude_label: str = None,
    include_body: bool = False,
    search_in_label: str = None,
):
    """
    사용자의 Gmail에서 특정 조건에 맞는 이메일 또는 초안을 검색합니다.
    - search_in_label (str): 검색할 특정 메일함. 예: 'inbox', 'draft', 'sent'.
    ... (기타 파라미터 설명은 동일) ...
    """
    print(f"--- 툴 호출: find_mails (label: {search_in_label}) ---")
    service = get_gmail_service()
    try:
        operators = []
        if sender: operators.append(f'from:({sender})')
        if query: operators.append(query)
        if is_unread: operators.append('is:unread')
        if has_attachment: operators.append('has:attachment')
        if start_date: operators.append(f'after:{start_date.replace("-", "/")}')
        if end_date: operators.append(f'before:{end_date.replace("-", "/")}')
        if exclude_label: operators.append(f'-label:{exclude_label}')
        
        final_query = ' '.join(operators)
        
        list_results = []
        if search_in_label == 'draft':
            print(f"INFO: Calling drafts.list with query: '{final_query}'")
            response = service.users().drafts().list(userId='me', q=final_query).execute()
            list_results = response.get('drafts', [])
        else:
            if search_in_label:
                final_query = f'in:{search_in_label} {final_query}'.strip()
            print(f"INFO: Calling messages.list with query: '{final_query}'")
            response = service.users().messages().list(userId='me', q=final_query).execute()
            list_results = response.get('messages', [])

        if not list_results:
            return "해당 조건에 맞는 메일이 없습니다."
        
        return _process_message_list(service, list_results, include_body)
        
    except HttpError as error:
        return f"메일 검색 중 오류가 발생했습니다: {error}"
    
@tool
def draft_mail(recipient: str, subject: str, body: str):
    """
    사용자의 요청에 따라 이메일 초안을 생성하여 Gmail '초안' 보관함에 저장합니다. 메일을 발송하지는 않습니다.
    - recipient (str): 메일을 받을 사람의 이메일 주소.
    - subject (str): 메일의 제목.
    - body (str): 메일의 본문.
    """
    print("--- 툴 호출: draft_mail ---")
    service = get_gmail_service()
    try:
        message = MIMEText(body)
        message['to'] = recipient
        message['subject'] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
        
        draft_body = {'message': {'raw': raw_message}}
        draft = service.users().drafts().create(userId='me', body=draft_body).execute()
        return f"'{recipient}'님에게 보내는 메일 초안을 성공적으로 생성했습니다. Gmail 초안함에서 확인하세요."
    except HttpError as error:
        return f"초안 생성 중 에러 발생: {error}"

@tool
def summarize_conversation_in_mails(person_name_or_email: str):
    """
    특정 인물과 주고받은 가장 최근의 이메일 대화(스레드) 내용을 찾아 요약합니다.
    - person_name_or_email (str): 대화 내용을 요약할 상대방의 이름 또는 이메일 주소.
    """
    print("--- 툴 호출: summarize_conversation ---")
    service = get_gmail_service()
    try:
        query = f"from:{person_name_or_email} OR to:{person_name_or_email}"
        response = service.users().threads().list(userId='me', q=query, maxResults=1).execute()
        threads = response.get('threads', [])
        if not threads:
            return f"'{person_name_or_email}'님과의 대화를 찾을 수 없습니다."
            
        thread_id = threads[0]['id']
        thread = service.users().threads().get(userId='me', id=thread_id).execute()
        
        conversation_text = ""
        for msg in thread['messages']:
            snippet = msg.get('snippet', '')
            conversation_text += snippet + "\n---\n"
        
        summarizer_llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
        summary_prompt = f"다음 이메일 대화 내용을 한글로 2~3문장으로 간결하게 요약해 주세요:\n\n[대화 내용]\n{conversation_text}"
        summary = summarizer_llm.invoke(summary_prompt).content
        return summary
    except HttpError as error:
        return f"대화 요약 중 에러 발생: {error}"

# --- 이메일 에이전트 생성 함수 ---
def create_mail_agent_executor():
    """
    Gmail API를 사용하는 전문 이메일 에이전트(AgentExecutor)를 생성합니다.
    메일 검색, 초안 작성, 대화 요약 기능을 제공합니다.
    """
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a specialized email assistant. 사용자의 이메일 관련 요청을 처리합니다. '나'는 항상 사용자 자신을 의미합니다. 오늘 날짜는 {today}입니다."),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    tools = [find_mails, draft_mail, summarize_conversation_in_mails]
    
    agent = create_openai_functions_agent(llm, tools, prompt)
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False)
    
    return agent_executor

# if __name__ == "__main__":
#     load_dotenv()
    
#     # query = "내 메일함에서 초안 조회해줘, 해당 메일의 본문을 그대로 출력해줘 "
#     query = "내 메일함에서 초안 조회해줘, 그 초안을 2025.06.26 19:00 에 예약발송걸어줘 "
    
#     today_str = datetime.now().strftime("%Y-%m-%d")

#     print(f"\n==================================================")
#     print(f"[사용자 쿼리]: {query}")
#     print(f"==================================================")
    
#     result = agent_executor.invoke({
#         "input": query,
#         "today": today_str
#     })
    
#     ai_response = result['output']
#     print(f"\n[AI 최종 답변]: {ai_response}")



# --- 멀티턴 대화를 위한 메인 실행 블록 ---
if __name__ == "__main__":
    load_dotenv()
    mail_agent = create_mail_agent_executor()
    chat_history = []
    
    today_str = datetime.now().strftime("%Y-%m-%d")

    print("AI 이메일 어시스턴트입니다. 무엇을 도와드릴까요? (종료하려면 'exit' 또는 '종료'를 입력하세요)")

    while True:
        try:
            user_input = input("\nYou: ")
            
            if user_input.lower() in ["exit", "종료"]:
                print("어시스턴트를 종료합니다.")
                break

            result = mail_agent.invoke({
                "input": user_input,
                "today": today_str,
                "chat_history": chat_history 
            })
            
            ai_response = result['output']
            print(f"\nAI: {ai_response}")

            chat_history.append(HumanMessage(content=user_input))
            chat_history.append(AIMessage(content=ai_response))

            if len(chat_history) > 10: # 최근 5번의 대화만 기억
                chat_history = chat_history[-10:]

        except Exception as e:
            print(f"오류가 발생했습니다: {e}")
