
EVALUATION_SET = [
    {
        "description": "일반 지식 질문 (도구 사용 없음)",
        "query": "어린왕자라는 책의 줄거리좀 알려줄래?",
        "expected_tool_calls": []
    },
    {
        "description": "기술 개념 질문 (도구 사용 없음)",
        "query": "LLM과 RAG 차이를 잘 모르겠어 알려줘",
        "expected_tool_calls": []
    },
    {
        "description": "명시적 단일 도구 호출 (검색)",
        "query": "LLM과 RAG의 차이를 검색을 해서 알려줘",
        "expected_tool_calls": [
            {
                "agent_name": "search_agent",
                "function_name": "general_search",
                "argument_checks": {
                    "query": lambda arg: "LLM" in arg and "RAG" in arg
                }
            }
        ]
    },
    {
        "description": "단일 도구 호출 (주식 추천)",
        "query": "오늘 종목 추천해줘",
        "expected_tool_calls": [
            {
                "agent_name": "stock_agent",
                "function_name": "recommend_stock",
                "argument_checks": {}
            }
        ]
    },
    {
        "description": "단일 도구 호출 (메일 요약)",
        "query": "홍길동이랑 주고받은 최근 메일 요약해줘",
        "expected_tool_calls": [
            {
                "agent_name": "mail_agent",
                "function_name": "summarize_conversation_in_mails",
                "argument_checks": {
                    "person": lambda arg: "홍길동" in arg
                }
            }
        ]
    },
    {
        "description": "복합 도구 순차 호출 (검색 후 메일 작성)",
        "query": "최신 AI 기술 동향에 대해 TechCrunch에서 검색해서, 그 내용을 바탕으로 우리 팀에게 공유할 메일 초안을 작성해줘. 받는 사람은 'dev_team@mycompany.com' 이야.",
        "expected_tool_calls": [
            {
                "agent_name": "search_agent",
                "function_name": "tech_news_search",
                "argument_checks": {
                    "query": lambda arg: "AI" in arg and "TechCrunch" in arg
                }
            },
            {
                "agent_name": "mail_agent",
                "function_name": "draft_mail",
                "argument_checks": {
                    "recipient": lambda arg: "dev_team@mycompany.com" in arg
                }
            }
        ]
    },
    {
        "description": "복합 도구 순차 호출 (캘린더 조회 후 장소 추천)",
        "query": "오늘 오후 스케쥴에 맞춰 잠깐 한시간정도 쇼핑할만한 장소 추천해줘",
        "expected_tool_calls": [
            {
                "agent_name": "calendar_agent",
                "function_name": "list_calendar_events",
                "argument_checks": {
                    "date": lambda arg: "오늘" in arg 
                }
            },
            {
                "agent_name": "place_agent",
                "function_name": "search_naver_place",
                "argument_checks": {
                    "query": lambda arg: "쇼핑" in arg
                }
            }
        ]
    },
    {
        "description": "복합 도구 순차 호출 (날씨 확인 후 장소 추천)",
        "query": "이번 주말에 가족과 나들이 갈만한 곳을 추천해줘",
        "expected_tool_calls": [
            {
                "agent_name": "weather_agent",
                "function_name": "get_weather",
                "argument_checks": {
                    "date": lambda arg: "주말" in arg
                }
            },
            {
                "agent_name": "place_agent",
                "function_name": "search_naver_place",
                "argument_checks": {
                    "query": lambda arg: "나들이" in arg or "가족" in arg
                }
            }
        ]
    },
    {
        "description": "복합 도구 순차 호출 (문서 검색 후 메일 작성)",
        "query": "오늘 있었던 팀 KPI 회의록 요약해서 박기훈 팀장님에게 보낼 수 있게 메일 내용을 작성해줘",
        "expected_tool_calls": [
            {
                "agent_name": "document_agent",
                "function_name": "get_document",
                "argument_checks": {
                    "query": lambda arg: "KPI" in arg and "회의록" in arg
                }
            },
            {
                "agent_name": "mail_agent",
                "function_name": "draft_mail",
                "argument_checks": {
                    "recipient": lambda arg: "박기훈" in arg
                }
            }
        ]
    },
    {
        "description": "복합 대화형 쿼리 (장소 검색 및 캘린더 등록)",
        "query": "오늘 주말에 민수랑 저녁먹으려고 하는데 강남에 술한잔하기 괜찮은데 알려주고 캘린더에 등록좀 해줘.",
        "expected_tool_calls": [
            {
                "agent_name": "place_agent",
                "function_name": "search_naver_place",
                "argument_checks": {
                    "query": lambda arg: "강남" in arg and ("술" in arg or "저녁" in arg)
                }
            },
            {
                "agent_name": "calendar_agent",
                "function_name": "create_calendar_event",
                "argument_checks": {
                    "title": lambda arg: "민수" in arg,
                }
            }
        ]
    },
    {
        "description": "연속적인 복합 쿼리 (장소 검색 2회 후 캘린더 등록)",
        "query": "주말에 우리 뽀미 데리고 놀러갈건데 강원도에 애견펜션 알려줘. 혹시 그 애견펜션 근처에 강아지 데리고 갈만한 곳들은 없어?, 찾은 곳들로 주말 일정을 등록해줘",
        "expected_tool_calls": [
            {
                "agent_name": "place_agent",
                "function_name": "search_naver_place",
                "argument_checks": {
                    "query": lambda arg: "강원도" in arg and "애견펜션" in arg
                }
            },
            {
                "agent_name": "place_agent",
                "function_name": "search_naver_place",
                "argument_checks": {
                    "query": lambda arg: ("근처" in arg or "주변" in arg) and ("강아지" in arg or "애견" in arg)
                }
            },
            {
                "agent_name": "calendar_agent",
                "function_name": "create_calendar_event",
                "argument_checks": {
                    "title": lambda arg: "뽀미" in arg or "강원도" in arg or "주말" in arg
                }
            }
        ]
    }
]