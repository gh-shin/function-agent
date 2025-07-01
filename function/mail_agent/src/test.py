import os
import base64 # 본문(payload) 디코딩을 위해 추가
import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# .readonly 권한이면 제목 읽기까지 충분합니다.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_credentials():
    """OAuth 2.0 인증을 수행하고 유효한 자격증명(Credentials) 객체를 반환합니다."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    return creds

def list_messages(credentials):
    """메일 목록을 가져옵니다. (기존과 동일)"""
    url = 'https://gmail.googleapis.com/gmail/v1/users/me/messages'
    headers = {'Authorization': f'Bearer {credentials.token}'}
    params = {'q': 'in:inbox is:unread', 'maxResults': 10}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        print(f"메시지 목록 조회 중 HTTP 에러: {err}")
        return None

# ----- 새로 추가된 함수 -----
def get_message_details(credentials, message_id):
    """
    주어진 message_id를 사용하여 메일의 상세 정보를 가져오고 제목을 반환합니다.
    """
    # users.messages.get API 엔드포인트
    url = f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}'
    
    headers = {'Authorization': f'Bearer {credentials.token}'}
    
    # format=metadata와 headers만 요청하면 응답이 더 가벼워집니다.
    params = {
        'format': 'metadata',
        'metadataHeaders': ['Subject', 'From', 'To', 'Date']
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        message_data = response.json()
        
        # 헤더(headers) 목록에서 'Subject'를 찾습니다.
        subject = ''
        for header in message_data['payload']['headers']:
            if header['name'] == 'Subject':
                subject = header['value']
                break
        
        return subject

    except requests.exceptions.HTTPError as err:
        print(f"메시지 상세 정보 조회 중 HTTP 에러 (ID: {message_id}): {err}")
        return "[제목을 가져올 수 없음]"
    except Exception as e:
        print(f"메시지 상세 정보 조회 중 오류 (ID: {message_id}): {e}")
        return "[오류 발생]"


if __name__ == '__main__':
    # 1. 인증
    gmail_creds = get_gmail_credentials()
    
    if gmail_creds:
        # 2. 메일 목록 가져오기
        messages_data = list_messages(gmail_creds)
        
        if messages_data and 'messages' in messages_data:
            print(f"총 {len(messages_data['messages'])}개의 메시지를 찾았습니다. 각 메시지의 제목을 가져옵니다...\n")
            
            # 3. 각 메시지에 대해 반복하며 상세 정보 요청
            for message in messages_data['messages']:
                msg_id = message['id']
                
                # 4. 상세 정보를 가져와서 제목 출력
                subject = get_message_details(gmail_creds, msg_id)
                print(f"  - ID: {msg_id}, 제목: {subject}")

        elif messages_data:
            print("조건에 맞는 메시지가 없습니다.")