from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config.settings import settings

def create_llm():
    """ChatOpenAI 인스턴스 생성"""
    settings.validate_openai_config()
    
    return ChatOpenAI(
        api_key=settings.OPENAI_API_KEY,
        model=settings.OPENAI_MODEL,
        temperature=settings.OPENAI_TEMPERATURE,
        max_tokens=2000
    )

# Root Cause Analysis를 위한 프롬프트 템플릿
ROOT_CAUSE_ANALYSIS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """당신은 시스템 장애 분석 전문가입니다. 
    제공된 로그, 메트릭, 트레이스 정보를 종합적으로 분석하여 정확한 근본 원인을 찾아내세요.

    분석 방법론:
    1. 시간순으로 이벤트 분석
    2. 메트릭 패턴과 임계값 비교
    3. 에러 로그와 트레이스 연관성 파악
    4. 시스템 의존성 고려

    답변 형식:
    - 근본 원인 (한 문장으로 명확히)
    - 분석 근거 (2-3개 주요 증거)
    - 영향 범위
    - 신뢰도 (1-10점)"""),
    
    ("human", """다음 정보를 바탕으로 장애의 근본 원인을 분석해주세요:

    **로그 정보:**
    {logs}

    **메트릭 정보:**
    {metrics}

    **트레이스 정보:**
    {traces}

    **알림 컨텍스트:**
    {alert_context}""")
])

# Action Planning을 위한 프롬프트 템플릿 (도구 선택 포함)
ACTION_PLANNING_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """당신은 시스템 운영 전문가입니다. 
    근본 원인 분석 결과를 바탕으로 3가지 구체적인 조치 계획을 수립하세요.
    각 조치마다 실행할 도구들과 순서를 명확히 지정해야 합니다.

    사용 가능한 도구들:
    - check_ecs_health: ECS 서비스 상태 확인
    - restart_ecs_task: ECS 태스크 재시작 
    - verify_restart: 재시작 후 상태 검증
    - check_db_connections: DB 커넥션 상태 확인
    - restart_db_pool: DB 커넥션 풀 재시작
    - validate_db_health: DB 상태 검증
    - reduce_traffic: 트래픽 감소
    - restart_all_services: 전체 서비스 재시작
    - gradual_traffic_restore: 트래픽 단계적 복원

    응답 형식 (JSON):
    {{
      "actions": [
        {{
          "id": 1,
          "title": "ECS 서비스 즉시 재시작",
          "description": "현재 타임아웃 문제 해결을 위한 즉시 조치",
          "risk_level": "중간",
          "estimated_time": "3분",
          "tools": [
            {{"name": "check_ecs_health", "params": {{"service": "api-service", "cluster": "prod"}}}},
            {{"name": "restart_ecs_task", "params": {{"service": "api-service", "force": true}}}},
            {{"name": "verify_restart", "params": {{"service": "api-service", "timeout": 180}}}}
          ]
        }}
      ],
      "recommendation": 1
    }}"""),
    
    ("human", """다음 근본 원인 분석 결과를 바탕으로 3가지 조치 계획을 JSON 형식으로 제시해주세요:

    **근본 원인:**
    {root_cause}

    **현재 상황:**
    - 에러율: {error_rate}
    - 지연시간: {latency}
    - 영향받는 서비스: {affected_services}

    **메트릭 정보:**
    {metrics}""")
])


def create_root_cause_chain():
    """Root Cause Analysis를 위한 LLM 체인 생성"""
    llm = create_llm()
    chain = ROOT_CAUSE_ANALYSIS_PROMPT | llm | StrOutputParser()
    return chain

def create_action_planning_chain():
    """Action Planning을 위한 LLM 체인 생성"""
    llm = create_llm()
    chain = ACTION_PLANNING_PROMPT | llm | StrOutputParser()
    return chain
