naver_search_poi = {
    "name": "search_naver_place",
    "description": "네이버 지역 검색 API를 사용하여 장소 정보를 검색합니다.",
    "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색어 (예: '카페', '맛집')"},
                "display": {"type": "integer", "description": "검색 결과 개수 (1~5)", "default": 5},
                "start": {"type": "integer", "description": "검색 시작 위치 (1~5)", "default": 1},
                "sort": {"type": "string", "enum": ["random", "comment"], "description": "정렬 방법. 사람들의 리뷰가 많은 순서대로의 추천이 필요한 경우, 'comment'를 사용할 수 있습니다."},
            },
        "required": ["query"],
    },
}

google_calendar_create_event = {
    "type": "function",
    "function": {
        "name": "create_calendar_event",
        "description": "Google 캘린더에 새로운 이벤트를 생성합니다. 사용자의 POI 방문 계획을 캘린더에 추가할 때 유용합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "이벤트의 제목입니다. 예: '팀 회의', '병원 예약', '강남 맛집 방문'"
                },
                "start_time_str": {
                    "type": "string",
                    "description": "이벤트의 시작 시간 (ISO 8601 형식, 예: '2025-07-01T10:00:00+09:00'). 날짜와 시간이 모두 포함되어야 합니다."
                },
                "end_time_str": {
                    "type": "string",
                    "description": "이벤트의 종료 시간 (ISO 8601 형식, 예: '2025-07-01T11:00:00+09:00'). 날짜와 시간이 모두 포함되어야 합니다."
                },
                "description": {
                    "type": "string",
                    "description": "이벤트의 상세 설명입니다. 예: '프로젝트 A 진행 상황 논의', '신상 메뉴 시식'"
                },
                "location": {
                    "type": "string",
                    "description": "이벤트가 열리는 장소입니다. 예: '온라인 Zoom', '서울 강남구 역삼동 812-1'"
                }
            },
            "required": ["summary", "start_time_str", "end_time_str"]
        }
    }
}
google_calendar_search_events = {
    "type": "function",
    "function": {
        "name": "list_calendar_events",
        "description": "Google 캘린더에서 특정 기간 또는 키워드에 해당하는 이벤트를 조회합니다. 사용자의 현재 일정을 파악하여 POI 추천에 활용할 수 있습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "start_date_str": {
                    "type": "string",
                    "description": "조회를 시작할 날짜 (ISO 8601 형식, 예: '2025-07-01'). 날짜만 지정합니다. (시간은 00:00:00으로 간주)"
                },
                "end_date_str": {
                    "type": "string",
                    "description": "조회를 종료할 날짜 (ISO 8601 형식, 예: '2025-07-31'). 날짜만 지정합니다. (시간은 23:59:59으로 간주)"
                },
                "keyword": {
                    "type": "string",
                    "description": "이벤트 제목이나 설명에서 검색할 키워드입니다. 예: '회의', '운동', '여행'"
                }
            },
            "required": []
        }
    }
}
google_calendar_modify_event = {
    "type": "function",
    "function": {
        "name": "modify_calendar_event",
        "description": "Google 캘린더의 기존 이벤트를 수정합니다. 이벤트의 제목, 시간, 장소, 설명, 참석자 등을 변경할 수 있습니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "수정할 이벤트의 고유 ID입니다. 이 ID는 먼저 'list_calendar_events' 함수를 통해 조회해야 합니다."
                },
                "summary": {
                    "type": "string",
                    "description": "이벤트의 새로운 제목입니다."
                },
                "start_time_str": {
                    "type": "string",
                    "description": "이벤트의 새로운 시작 시간 (ISO 8601 형식, 예: '2025-07-01T10:30:00+09:00')."
                },
                "end_time_str": {
                    "type": "string",
                    "description": "이벤트의 새로운 종료 시간 (ISO 8601 형식, 예: '2025-07-01T11:30:00+09:00')."
                },
                "description": {
                    "type": "string",
                    "description": "이벤트의 새로운 상세 설명입니다."
                },
                "location": {
                    "type": "string",
                    "description": "이벤트의 새로운 장소입니다."
                },
                "attendees_to_add": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "이벤트에 추가할 참석자들의 이메일 주소 목록입니다."
                },
                "attendees_to_remove": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "description": "이벤트에서 제거할 참석자들의 이메일 주소 목록입니다."
                }
            },
            "required": ["event_id"]
        }
    }
}
google_calendar_delete_event = {
    "type": "function",
    "function": {
        "name": "delete_calendar_event",
        "description": "Google 캘린더에서 특정 이벤트를 삭제합니다.",
        "parameters": {
            "type": "object",
            "properties": {
                "event_id": {
                    "type": "string",
                    "description": "삭제할 이벤트의 고유 ID입니다. 이 ID는 먼저 'list_calendar_events' 함수를 통해 조회해야 합니다."
                }
            },
            "required": ["event_id"]
        }
    }
}
