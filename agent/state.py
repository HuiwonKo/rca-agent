from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    """RCA Agent의 상태를 정의하는 TypedDict"""
    
    # 입력 정보
    slack_alert: Dict[str, Any]      # Slack 알림 정보

    # 모니터링 데이터
    context: Dict[str, Any]          # 시스템 컨텍스트
    metrics: Dict[str, Any]          # 메트릭 정보
    logs: List[Dict[str, Any]]       # 로그 데이터
    traces: List[Dict[str, Any]]     # 트레이스 데이터
    
    # 분석 결과
    root_cause: str                  # 근본 원인 분석 결과
    recommended_actions: List[Dict[str, Any]]  # 추천 액션 리스트
    
    # 사용자 인터랙션
    user_choice: str                 # 사용자가 선택한 액션
    selected_action_details: Dict[str, Any]  # 선택된 액션의 상세 정보
    human_feedback: Dict[str, Any]   # 사용자 피드백 (LangGraph Studio용)
    
    # 실행 결과
    execution_results: List[Dict[str, Any]]  # 도구 실행 결과
    final_status: str                # 최종 처리 상태
