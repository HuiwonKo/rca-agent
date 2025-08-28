from langgraph.graph import StateGraph, END, START
from typing import TypedDict, List, Dict, Any
from agent.llm import create_root_cause_chain, create_action_planning_chain

# --- 상태 정의 ---
class AgentState(TypedDict):
    alert_context: Dict[str, Any]   # Slack 알림/Trigger 정보
    logs: str                       # CloudWatch 로그
    metrics: Dict[str, Any]         # Datadog Metrics snapshot
    traces: Dict[str, Any]          # Datadog Trace
    root_cause: str                 # 분석 결과
    action_plan: str                # 권장 조치
    approved: bool                  # 승인 여부
    result: str                     # 실행 결과
    is_mock: bool                    # 모킹 여부


# --- Node 구현 ---
def slack_alert_input_node(state: AgentState):
    """Slack 알림에서 트리거"""
    print("🚨 Slack Alert Received")
    state["is_mock"] = True
    return state


def context_collector_node(state: AgentState):
    """CloudWatch / Datadog 모니터링 데이터 수집"""
    # 더 상세한 모킹 데이터로 LLM 분석에 도움이 되도록 개선
    state["logs"] = """
2024-01-15 14:30:45 ERROR [service-a] ConnectionTimeout: Failed to connect to database after 30s
2024-01-15 14:30:46 ERROR [service-a] org.springframework.dao.QueryTimeoutException: Query timed out
2024-01-15 14:30:47 WARN  [service-a] Connection pool exhausted, current: 20/20
2024-01-15 14:30:48 ERROR [load-balancer] Upstream timeout from service-a:8080
2024-01-15 14:30:49 ERROR [service-a] java.sql.SQLException: Communications link failure
"""
    
    state["metrics"] = {
        "error_rate": 0.25,
        "latency_p95_ms": 3500,
        "latency_p99_ms": 8000,
        "cpu_usage_percent": 85.2,
        "memory_usage_percent": 92.1,
        "db_connection_count": 20,
        "db_max_connections": 20,
        "request_rate_per_sec": 150
    }
    
    state["traces"] = {
        "trace_id": "abc-123-def-456",
        "spans": [
            {"service": "api-gateway", "duration_ms": 8200, "status": "error"},
            {"service": "service-a", "duration_ms": 8100, "status": "error", "error": "timeout"},
            {"service": "postgres-db", "duration_ms": 30000, "status": "timeout"}
        ],
        "error_count": 45,
        "total_requests": 180
    }
    
    print("📥 Context collected from mock CloudWatch/Datadog")
    return state


def root_cause_analyzer_node(state: AgentState):
    """ChatOpenAI를 사용한 실제 근본원인 분석"""
    print("🔎 Analyzing root cause with ChatOpenAI...")
    
    try:
        # LLM 체인 생성
        analysis_chain = create_root_cause_chain()
        
        # 프롬프트에 전달할 데이터 준비
        analysis_input = {
            "logs": state.get("logs", "로그 정보 없음"),
            "metrics": str(state.get("metrics", {})),
            "traces": str(state.get("traces", {})),
            "alert_context": str(state.get("alert_context", {}))
        }
        
        # LLM으로 분석 수행
        analysis_result = analysis_chain.invoke(analysis_input)
        state["root_cause"] = analysis_result
        
        print("✅ Root cause analysis completed with ChatOpenAI")
        
    except Exception as e:
        print(f"❌ Error in root cause analysis: {e}")
        # 실패 시 폴백
        state["root_cause"] = f"분석 실패: {str(e)}. 수동 분석이 필요합니다."
    
    return state


def action_planner_node(state: AgentState):
    """ChatOpenAI를 사용한 권장 조치 계획 생성"""
    print("📝 Generating action plan with ChatOpenAI...")
    
    try:
        # Action Planning 체인 생성
        planning_chain = create_action_planning_chain()
        
        # 메트릭에서 필요한 정보 추출
        metrics = state.get("metrics", {})
        error_rate = metrics.get("error_rate", "알 수 없음")
        latency = f"{metrics.get('latency_p95_ms', 'N/A')}ms (P95)"
        
        # 프롬프트에 전달할 데이터 준비
        planning_input = {
            "root_cause": state.get("root_cause", "근본 원인 분석 결과 없음"),
            "error_rate": error_rate,
            "latency": latency,
            "affected_services": "Service A, Database"
        }
        
        # LLM으로 조치 계획 생성
        action_plan = planning_chain.invoke(planning_input)
        state["action_plan"] = action_plan
        
        print("✅ Action plan generated with ChatOpenAI")
        
    except Exception as e:
        print(f"❌ Error in action planning: {e}")
        # 실패 시 폴백
        state["action_plan"] = f"조치 계획 생성 실패: {str(e)}. 수동 계획 수립이 필요합니다."
    
    return state


def approval_gate_node(state: AgentState):
    """Human-in-the-loop (Slack/Gradio UI)"""
    print("⚖️ Approval needed:")
    print(f"- Root Cause: {state['root_cause']}")
    print(f"- Plan: {state['action_plan']}")
    # 실제 구현에서는 Slack 버튼/Gradio UI 연결
    user_input = input("Approve action? (y/n): ").strip().lower()
    state["approved"] = user_input == "y"
    return state


def remediator_node(state: AgentState):
    """자동 실행 단계 (모킹)"""
    if state["approved"]:
        state["result"] = "✅ ECS task restarted successfully"
        print("🛠 Remediation executed")
    else:
        state["result"] = "❌ Action rejected by human"
    return state


# --- Graph 구성 ---
workflow = StateGraph(AgentState)

# 노드 추가
workflow.add_node("SlackAlert", slack_alert_input_node)
workflow.add_node("ContextCollector", context_collector_node)
workflow.add_node("RootCauseAnalyzer", root_cause_analyzer_node)
workflow.add_node("ActionPlanner", action_planner_node)
workflow.add_node("ApprovalGate", approval_gate_node)
workflow.add_node("Remediator", remediator_node)

# Edge 연결
workflow.add_edge(START, "SlackAlert")
workflow.add_edge("SlackAlert", "ContextCollector")
workflow.add_edge("ContextCollector", "RootCauseAnalyzer")
workflow.add_edge("RootCauseAnalyzer", "ActionPlanner")
workflow.add_edge("ActionPlanner", "ApprovalGate")
workflow.add_conditional_edges(
    "ApprovalGate",
    lambda s: "Remediator" if s["approved"] else END,
    {"Remediator": "Remediator", END: END},
)
workflow.add_edge("Remediator", END)

# --- 실행기 ---
app = workflow.compile()

if __name__ == "__main__":
    initial_state: AgentState = {"alert_context": {"service": "Service A"}}
    final_state = app.invoke(initial_state)
    print("🎉 Final State:", final_state)
