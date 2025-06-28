from langchain_community.tools.tavily_search import TavilySearchResults
import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import tool, AgentExecutor, create_openai_functions_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from datetime import datetime, timedelta

tavily_qa_tool = TavilySearchResults(max_results=3)
tavily_qa_tool.name = "general_question_answering"
tavily_qa_tool.description = "사용자의 일반적인 질문에 대해 웹을 검색하고 요약된 답변을 찾을 때 사용합니다."

tech_search_tool = TavilySearchResults(
    max_results=3,
    search_kwargs={"include_domains": ["techcrunch.com", "theverge.com"]}
)
tech_search_tool.name = "tech_news_search"
tech_search_tool.description = "TechCrunch나 The Verge에서 최신 기술 뉴스를 검색할 때 사용합니다."

find_links_tool = TavilySearchResults(
    name="find_relevant_links",
    max_results=5,
    search_kwargs={"include_answer": False}
)
find_links_tool.description = "사용자가 특정 주제에 대한 '링크', '웹사이트', '자료', '튜토리얼' 등을 찾아달라고 요청할 때 사용합니다. 요약된 답변 대신 관련 웹페이지 목록을 제공하는 데 특화되어 있습니다."


def create_search_agent_executor():
    """
    Tavily를 사용하는 전문 검색 에이전트(AgentExecutor)를 생성합니다.
    이 에이전트는 일반 Q&A, 기술 뉴스 검색, 관련 링크 찾기 기능을 제공합니다.
    """
    # --- Tool 정의 ---
    # --- 프롬프트 및 LLM 설정 ---
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a specialized web search assistant. 현재 날짜는 {today} 입니다. 사용자의 검색 요청을 분석하여 가장 적절한 검색 도구를 사용하세요."),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)
    tools = [tavily_qa_tool, tech_search_tool, find_links_tool]
    
    # --- 에이전트 생성 및 반환 ---
    agent = create_openai_functions_agent(llm, tools, prompt)
    
    # 하위 에이전트는 verbose=False로 설정하여 상위 에이전트의 로그를 깔끔하게 유지하는 것이 좋습니다.
    agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=False) 
    
    return agent_executor




if __name__ == "__main__":
    load_dotenv()
    search_agent = create_search_agent_executor()

    # query = "내 메일함에서 초안 조회해줘, 해당 메일의 본문을 그대로 출력해줘 "
    # query = "google gemini에 대해 알려줘, tech news들을 위주로 조회해서 알려줘"
    query = "google gemini에 대해 알려줘, 링크만 알려주면 좋겠어"
    
    today_str = datetime.now().strftime("%Y-%m-%d")

    print(f"\n==================================================")
    print(f"[사용자 쿼리]: {query}")
    print(f"==================================================")
    
    result = search_agent.invoke({
        "input": query,
        "today": today_str
    })
    
    ai_response = result['output']
    print(f"\n[AI 최종 답변]: {ai_response}")