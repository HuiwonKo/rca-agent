# 🤖 RCA Agent

LangGraph 기반 Root Cause Analysis 에이전트

## 📋 개요

이 프로젝트는 시스템 장애 발생 시 자동으로 근본 원인을 분석하고 적절한 조치를 추천하는 RCA(Root Cause Analysis) 에이전트입니다.

### 🎯 주요 기능

- **자동 근본 원인 분석**: ChatOpenAI를 사용한 지능적 분석
- **3가지 조치 추천**: ECS, DB, 트래픽 제어 기반 액션
- **Human-in-the-loop**: 사용자 승인 후 액션 실행
- **도구 자동 실행**: 선택된 액션의 도구 순차 실행
- **Gradio UI**: 웹 기반 시연 인터페이스
- **LangGraph Studio**: 개발/디버깅 지원

## 🏗 아키텍처

```
Slack Alert → Context Collection → Root Cause Analysis → Action Planning → Approval Gate → Execute Action → Validation
```

### 노드 구성

1. **SlackAlert**: 알림 트리거 수신
2. **ContextCollector**: 모니터링 데이터 수집 (로그, 메트릭, 트레이스)
3. **RootCauseAnalyzer**: ChatOpenAI 기반 근본 원인 분석
4. **ActionPlanner**: 3가지 조치 액션과 도구 목록 생성
5. **ApprovalGate**: 사용자 승인 대기 (Human-in-the-loop with interrupt)
6. **ExecuteAction**: 선택된 액션의 도구 실행
7. **Validation**: 실행 후 상태 검증

## 🛠 설치 및 실행

### 1. 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd rca-agent

# 의존성 설치
uv sync

# 환경 변수 설정
cp .env.example .env
# .env 파일에 OpenAI API 키 설정
```

### 2. 환경 변수

`.env` 파일 생성:

```env
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL_NAME=gpt-4o-mini
```

### 3. 실행 방법

#### 🎮 Gradio 데모 (추천)

```bash
# 간단한 실행
python run_demo.py

# 또는 직접 실행
python gradio_app.py
```

브라우저에서 `http://localhost:7860` 접속

#### 🔧 LangGraph Studio

```bash
# LangGraph Studio 실행
langgraph dev

# 브라우저에서 LangGraph Studio UI 접속
# http://localhost:8123
```

## 📱 Gradio 데모 사용법

1. **장애 정보 입력**:
   - 서비스 이름: `api-service`
   - 에러 발생 시간: `2024-01-15 14:30:00`

2. **RCA 분석 시작**: 'RCA 분석 시작' 버튼 클릭
   - 시스템이 자동으로 모니터링 데이터(로그, 메트릭, 트레이스) 수집
   - ChatOpenAI로 근본 원인 분석 수행

3. **액션 선택**: 추천된 3가지 액션 중 하나 선택

4. **실행 확인**: 선택한 액션의 도구들이 순차 실행됨

5. **결과 확인**: 실행 결과 및 히스토리 조회

## 🎯 추천 액션 유형

### 1. ECS 서비스 재시작 (즉시 조치)
- **도구**: `check_ecs_health` → `restart_ecs_task` → `verify_restart`
- **위험도**: 중간
- **예상 시간**: 3분

### 2. DB 커넥션 재설정 (단기 조치)
- **도구**: `check_db_connections` → `restart_db_pool` → `validate_db_health`
- **위험도**: 낮음
- **예상 시간**: 2분

### 3. 트래픽 제어 후 재시작 (장기 조치)
- **도구**: `reduce_traffic` → `restart_all_services` → `gradual_traffic_restore`
- **위험도**: 높음
- **예상 시간**: 10분

## 🔧 개발

### 프로젝트 구조

```
rca-agent/
├── agent/
│   ├── __init__.py
│   ├── state.py          # AgentState 정의
│   ├── graph.py          # LangGraph 워크플로우
│   ├── llm.py           # ChatOpenAI 체인들
│   └── tools.py         # 실행 도구들
├── config/
│   ├── __init__.py
│   └── settings.py      # 설정 관리
├── gradio_app.py        # Gradio 웹 인터페이스
├── run_demo.py          # 데모 실행 스크립트
├── langgraph.json       # LangGraph Studio 설정
├── pyproject.toml       # 의존성 관리
└── README.md
```

### 주요 컴포넌트

#### AgentState
```python
class AgentState(TypedDict):
    slack_alert: Dict[str, Any]              # Slack 알림 정보
    context: Dict[str, Any]                  # 시스템 컨텍스트
    metrics: Dict[str, Any]                  # 메트릭 정보
    logs: List[Dict[str, Any]]               # 로그 데이터
    traces: List[Dict[str, Any]]             # 트레이스 데이터
    root_cause: str                          # 근본 원인 분석 결과
    recommended_actions: List[Dict[str, Any]] # 추천 액션 리스트
    user_choice: str                         # 사용자가 선택한 액션
    selected_action_details: Dict[str, Any]   # 선택된 액션의 상세 정보
    human_feedback: Dict[str, Any]           # 사용자 피드백
    execution_results: List[Dict[str, Any]]   # 도구 실행 결과
    final_status: str                        # 최종 처리 상태
```

#### Tools
모든 도구는 순수 Python 함수로 구현:
- `check_ecs_health()`: ECS 서비스 상태 확인
- `restart_ecs_task()`: ECS 태스크 재시작
- `verify_restart()`: 재시작 후 상태 검증
- `check_db_connections()`: DB 커넥션 상태 확인
- `restart_db_pool()`: DB 커넥션 풀 재시작
- `validate_db_health()`: DB 상태 검증
- `reduce_traffic()`: 트래픽 감소
- `restart_all_services()`: 전체 서비스 재시작
- `gradual_traffic_restore()`: 트래픽 단계적 복원

## 🧪 테스트

### 시나리오 테스트

1. **데이터베이스 서비스 장애**
   - 서비스 이름: `database-service`
   - 에러 발생 시간: `2024-01-15 14:30:00`
   - 예상: DB 커넥션 재설정 액션 추천

2. **API 서비스 응답 지연**
   - 서비스 이름: `api-service`
   - 에러 발생 시간: `2024-01-15 15:45:00`
   - 예상: ECS 서비스 재시작 액션 추천

3. **전체 시스템 과부하**
   - 서비스 이름: `load-balancer`
   - 에러 발생 시간: `2024-01-15 16:00:00`
   - 예상: 트래픽 제어 후 재시작 액션 추천

## 📊 모니터링

### LangGraph Studio에서 확인 가능한 정보
- 각 노드별 실행 상태
- 노드 간 데이터 흐름
- 실행 시간 및 성능
- 오류 발생 지점

### Gradio 데모에서 확인 가능한 정보
- 근본 원인 분석 결과
- 추천 액션 상세 정보
- 도구별 실행 결과
- 실행 히스토리

## 🚀 확장 계획

- [ ] 실제 AWS/GCP 연동
- [ ] Slack 봇 통합
- [ ] 더 많은 도구 추가
- [ ] 머신러닝 기반 패턴 학습
- [ ] 알림 자동화

## 📝 라이센스

MIT License

## 🤝 기여

이슈 제보 및 Pull Request를 환영합니다!
