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
    근본 원인 분석 결과를 바탕으로 효과적이고 안전한 조치 계획을 수립하세요.

    조치 계획 원칙:
    1. 즉시 조치 (서비스 안정화)
    2. 단기 조치 (임시 해결책)
    3. 장기 조치 (근본적 해결)
    4. 모니터링 강화

    답변 형식:
    **즉시 조치 (5분 내):**
    - 구체적인 실행 명령어
    
    **단기 조치 (1시간 내):**
    - 상세한 단계별 작업
    
    **장기 조치 (1주일 내):**
    - 근본적 개선 방안
    
    **모니터링:**
    - 추가 모니터링 항목
    
    **위험도:** [낮음/보통/높음]"""),
    
    ("human", """다음 근본 원인 분석 결과를 바탕으로 조치 계획을 수립해주세요:

    **근본 원인:**
    {root_cause}

    **현재 상황:**
    - 에러율: {error_rate}
    - 지연시간: {latency}
    - 영향받는 서비스: {affected_services}""")
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
