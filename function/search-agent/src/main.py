from langchain_community.tools.tavily_search import TavilySearchResults
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import tool, AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime, timedelta
# 1. 일반적인 Q&A Tool (가장 기본)
# search_depth='advanced'는 기본값이므로 따로 설정할 필요 없습니다.
tavily_qa_tool = TavilySearchResults(max_results=3)
tavily_qa_tool.name = "general_question_answering"
tavily_qa_tool.description = "사용자의 일반적인 질문에 대해 웹을 검색하고 요약된 답변을 찾을 때 사용합니다."

# 2. 특정 사이트 검색 Tool
# 기본 Tool의 파라미터를 오버라이드하여 새로운 Tool을 만들 수 있습니다.
tech_search_tool = TavilySearchResults(
    max_results=3,
    search_kwargs={"include_domains": ["techcrunch.com", "theverge.com"]}
)
tech_search_tool.name = "tech_news_search"
tech_search_tool.description = "TechCrunch나 The Verge에서 최신 기술 뉴스를 검색할 때 사용합니다."

find_links_tool = TavilySearchResults(
    name="find_relevant_links",
    max_results=5,
    # search_kwargs는 Tavily API에 직접 전달될 파라미터를 정의합니다.
    search_kwargs={"include_answer": False}
)
find_links_tool.description = "사용자가 특정 주제에 대한 '링크', '웹사이트', '자료', '튜토리얼' 등을 찾아달라고 요청할 때 사용합니다. 요약된 답변 대신 관련 웹페이지 목록을 제공하는 데 특화되어 있습니다."
# --- 새로운 Tool 정의 끝 ---

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful AI assistant. 현재 날짜는 {today} 입니다. 사용자의 요청을 분석하여 적절한 도구를 사용하세요."),
    MessagesPlaceholder(variable_name="chat_history", optional=True),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
tools = [tavily_qa_tool, tech_search_tool, find_links_tool]
agent = create_openai_functions_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


if __name__ == "__main__":
    load_dotenv()
    
    # query = "내 메일함에서 초안 조회해줘, 해당 메일의 본문을 그대로 출력해줘 "
    # query = "google gemini에 대해 알려줘, tech news들을 위주로 조회해서 알려줘"
    query = "google gemini에 대해 알려줘, 링크만 알려주면 좋겠어"
    
    today_str = datetime.now().strftime("%Y-%m-%d")

    print(f"\n==================================================")
    print(f"[사용자 쿼리]: {query}")
    print(f"==================================================")
    
    result = agent_executor.invoke({
        "input": query,
        "today": today_str
    })
    
    ai_response = result['output']
    print(f"\n[AI 최종 답변]: {ai_response}")