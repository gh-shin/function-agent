# function-agent

## Multi-Agent Architecture
super agent 하위에 sub agent를 작업 속성에 맞게 생성하고, 사용자의 요청에 대해 각 에이전트간 적절한 기능을 수행하여 사용자에게 응답하는것을 목표로 함

### super agent
user의 요청을 직접 받는 agent이며, 사용자의 요청을 판단하여 작업을 지시할 하위 agent에 기능을 요청함

#### business agent
업무 관련 요청을 처리하는 에이전트
##### mail
- 메일 조회
- 메일 내용 요약
- 사용자 요청에 맞는 초안 작성
##### calendar
- 일정 생성
- 일정 조회
- 일정 수정
- 일정 삭제

#### search agent
검색 관련 요청을 처리하는 에이전트
##### tavily
- 웹검색 기능 제공
##### tech news search
- tech crunch나 the verge 등, 최신 기술뉴스 기사 전용 검색기능
##### link search
- 사용자가 발화한 주제에 연관된 링크, 웹사이트 등 URL 목록을 제공

#### life agent
사용자의 일상생활과 관련한 요청을 처리하는 에이전트
##### naver places
- 사용자 키워드를 통한 장소검색
##### naver shopping
- 상품 검색
- 상품 장바구니 추가
- 구매 목록에 추가
##### weather
- 사용자 키워드에서 위치 키워드를 추출하여 좌표값으로 치환
- 날씨 API를 사용하여 현재 위치의 날씨 및 14일 간의 중기예보 조회
