
import sys
sys.path.append('/app/ica_project2/function-agent/') # 각 환경에 맞게 python path를 수정해야합니다 .
from function.mail_agent.src.main import create_mail_agent_executor
from function.search_agent.src.main import create_search_agent_executor
from langchain.tools import Tool
from datetime import datetime, timedelta

today_str = datetime.now().strftime("%Y-%m-%d")

# 1. 이메일 전문가 에이전트를 생성합니다.
mail_agent_executor = create_mail_agent_executor()

# 2. 검색 전문가 에이전트를 생성합니다.
search_agent_executor = create_search_agent_executor()


mail_agent = Tool(
        name="email_management_specialist",
        # 상위 에이전트가 이 도구를 호출하면, 람다 함수가 실행됩니다.
        # user_input에는 상위 에이전트가 판단한 작업 내용(문자열)이 들어옵니다.
        # 이 문자열을 하위 에이전트가 필요로 하는 {"input": ..., "today": ...} 딕셔너리 형태로 변환하여 invoke 해줍니다.
        func=lambda user_input: mail_agent_executor.invoke({
            "input": user_input,
            "today": today_str  # create_super_agent 함수가 받은 today_str 값을 주입합니다.
        }),
        # 이 설명은 슈퍼 에이전트(LLM)가 어떤 도구를 선택할지 결정하는 데 사용하는 가장 중요한 정보입니다.
        description="""사용자의 Gmail 계정과 관련된 작업을 처리하는 이메일 전문가입니다. 
        메일 검색, 초안 작성, 특정인과의 대화 요약 등의 기능을 수행합니다. 
        '메일', '이메일', '편지', '초안', '답장'과 같은 키워드가 있을 때 사용하세요."""
    )
search_agent = Tool(
        name="web_search_specialist",
        # 이메일 전문가와 동일한 패턴으로, 하위 검색 에이전트가 필요로 하는
        # 모든 변수(input, today)를 포함한 딕셔너리를 만들어 전달합니다.
        func=lambda user_input: search_agent_executor.invoke({
            "input": user_input,
            "today": today_str  # create_super_agent 함수가 받은 today_str 값을 주입합니다.
        }),
        description="""웹 검색이 필요할 때 사용하는 전문 검색 도우미입니다. 
        일반적인 질문 답변, 특정 기술 뉴스 사이트(TechCrunch, The Verge) 검색, 
        또는 주제 관련 링크 목록 찾기 등 다양한 검색 작업을 수행할 수 있습니다. 
        '검색해줘', '알려줘', '뉴스', '링크 찾아줘', '최신 동향'과 같은 요청에 사용하세요."""
    )