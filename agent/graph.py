from langgraph.graph import StateGraph, END, START
from langgraph.types import interrupt, Command
from typing import List, Dict, Any
from agent.llm import create_root_cause_chain, create_action_planning_chain
from agent.tools import get_tool_by_name
from agent.state import AgentState
import json
from datetime import datetime


# --- Node 구현 ---
def slack_alert_input_node(state: AgentState):
    """Slack 알림에서 트리거"""
    print("🚨 Slack Alert Received")
    
    # Mock Slack alert data (기존 데이터가 없으면 생성)
    if "slack_alert" not in state or not state["slack_alert"]:
        state["slack_alert"] = {
            "timestamp": "2024-01-15T10:30:00Z",
            "channel": "#alerts",
            "service": "Service A",
            "alert_type": "critical",
            "description": "High error rate detected"
        }
    
    print("✅ Slack alert processed")
    return state


def context_collector_node(state: AgentState):
    """CloudWatch / Datadog 모니터링 데이터 수집"""
    print("📊 Collecting monitoring data...")
    
    # Mock logs data
    state["logs"] = [
        {
            "timestamp": "2024-01-15T14:30:45Z",
            "level": "ERROR",
            "service": "service-a",
            "message": "ConnectionTimeout: Failed to connect to database after 30s"
        },
        {
            "timestamp": "2024-01-15T14:30:46Z",
            "level": "ERROR", 
            "service": "service-a",
            "message": "org.springframework.dao.QueryTimeoutException: Query timed out"
        },
        {
            "timestamp": "2024-01-15T14:30:47Z",
            "level": "WARN",
            "service": "service-a", 
            "message": "Connection pool exhausted, current: 20/20"
        }
    ]
    
    # Mock metrics가 없으면 기본값 설정
    if "metrics" not in state or not state["metrics"]:
        state["metrics"] = {
            "error_rate": "25%",
            "latency_p95_ms": 3500,
            "latency_p99_ms": 8000,
            "cpu_usage_percent": 85.2,
            "memory_usage_percent": 92.1,
            "db_connection_count": 20,
            "db_max_connections": 20,
            "request_rate_per_sec": 150
        }
    
    # Mock traces
    state["traces"] = [
        {
            "trace_id": "abc-123-def-456",
            "service": "api-gateway",
            "duration_ms": 8200,
            "status": "error"
        },
        {
            "trace_id": "abc-123-def-456", 
            "service": "service-a",
            "duration_ms": 8100,
            "status": "error",
            "error": "timeout"
        }
    ]
    
    # Context 정보
    state["context"] = {
        "environment": "production",
        "region": "us-west-2",
        "cluster": "prod-cluster",
        "deployment_version": "v1.2.3"
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
    """LLM으로 3가지 조치 액션과 도구 정보 생성 (JSON 파싱)"""
    print("📝 Generating 3 action plans with tools using LLM...")
    
    try:
        # Action Planning 체인 사용
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
            "affected_services": "Service A, Database",
            "metrics": str(metrics)
        }
        
        # LLM으로 조치 계획 생성 (JSON 응답)
        action_plan_json = planning_chain.invoke(planning_input)
        
        print(f"📋 LLM 응답:\n{action_plan_json}")

        # JSON 파싱 시도
        try:
            # JSON 문자열에서 실제 JSON 부분 추출
            start_idx = action_plan_json.find('{')
            end_idx = action_plan_json.rfind('}') + 1
            json_str = action_plan_json[start_idx:end_idx]
            
            action_plan_data = json.loads(json_str)
            state["recommended_actions"] = action_plan_data.get("actions", [])
            
            print("✅ Action plan with tools generated from LLM")
            print(f"🎯 Generated {len(state['recommended_actions'])} action options")
            
        except json.JSONDecodeError as je:
            print(f"⚠️ JSON parsing failed: {je}")
            # Fallback: 기본 액션 생성
            state["recommended_actions"] = [
                {
                    "id": 1,
                    "title": "ECS 서비스 재시작",
                    "description": "기본 서비스 재시작 조치",
                    "risk_level": "중간",
                    "estimated_time": "3분",
                    "tools": [
                        {"name": "check_ecs_health", "params": {"service": "api-service"}},
                        {"name": "restart_ecs_task", "params": {"service": "api-service"}},
                        {"name": "verify_restart", "params": {"service": "api-service"}}
                    ]
                },
                {
                    "id": 2,
                    "title": "DB 커넥션 재설정",
                    "description": "데이터베이스 커넥션 문제 해결",
                    "risk_level": "낮음",
                    "estimated_time": "2분",
                    "tools": [
                        {"name": "check_db_connections", "params": {"database": "main"}},
                        {"name": "restart_db_pool", "params": {"database": "main"}},
                        {"name": "validate_db_health", "params": {"database": "main"}}
                    ]
                },
                {
                    "id": 3,
                    "title": "트래픽 제어 후 재시작",
                    "description": "안전한 전체 시스템 복구",
                    "risk_level": "높음",
                    "estimated_time": "10분",
                    "tools": [
                        {"name": "reduce_traffic", "params": {"percentage": 50}},
                        {"name": "restart_all_services", "params": {"cluster": "prod"}},
                        {"name": "gradual_traffic_restore", "params": {"steps": 5}}
                    ]
                }
            ]
            print("✅ Action plan with tools generated from LLM")
            print(f"🎯 Generated {len(state['recommended_actions'])} action options")

    except Exception as e:
        print(f"❌ Error in action planning: {e}")
        # 실패 시 기본 폴백 액션
        state["recommended_actions"] = [
            {
                "id": 1,
                "title": "수동 점검 필요",
                "description": f"자동 계획 생성 실패: {str(e)}",
                "risk_level": "낮음",
                "estimated_time": "수동",
                "tools": []
            }
        ]
    
    return state


def approval_gate_node(state: AgentState):
    """Human-in-the-loop: LangGraph Studio에서 사용자 입력 대기"""
    
    # 이미 사용자 피드백이 있으면 처리
    if "human_feedback" in state and state["human_feedback"]:
        feedback = state["human_feedback"]
        choice = feedback.get("choice", "")
        
        if choice:
            state["user_choice"] = choice
            print(f"✅ 사용자 선택: {choice}")
            return state
    
    # 사용자에게 표시할 정보 준비
    actions = state.get("recommended_actions", [])
    
    # 선택 옵션 구성
    options = []
    for i, action in enumerate(actions, 1):
        # tools에서 도구 목록 추출
        tools_list = [tool.get('name', 'Unknown') for tool in action.get('tools', [])]
        
        options.append({
            "id": str(i),
            "title": action.get('title', f'Action {i}'),
            "description": action.get('description', ''),
            "risk_level": action.get('risk_level', 'Unknown'),
            "estimated_time": action.get('estimated_time', 'Unknown'),
            "tools": tools_list
        })
    
    # 추가 옵션
    options.extend([
        {
            "id": "manual",
            "title": "수동 조치",
            "description": "사용자가 직접 문제를 해결합니다",
            "risk_level": "사용자 판단",
            "estimated_time": "사용자 판단",
            "tools": []
        },
        {
            "id": "reanalyze", 
            "title": "재분석 요청",
            "description": "시스템 상태를 다시 분석합니다",
            "risk_level": "없음",
            "estimated_time": "3-5분",
            "tools": []
        }
    ])
    
    # Human-in-the-loop: 사용자 입력을 위한 interrupt
    interrupt_message = f"""
⚖️ **분석 완료! 조치를 선택해주세요**

🔍 **근본 원인:** {state.get('root_cause', 'N/A')}

📋 **추천 조치 사항:**

{chr(10).join([
    f"**{opt['id']}. {opt['title']}**" + chr(10) +
    f"   • 설명: {opt['description']}" + chr(10) +
    f"   • 위험도: {opt['risk_level']}" + chr(10) +
    f"   • 예상시간: {opt['estimated_time']}" + chr(10) +
    f"   • 도구: {', '.join(opt['tools'])}" + chr(10)
    for opt in options
])}

💡 **선택 방법:** 액션 번호를 입력하세요 (1, 2, 3, manual, reanalyze)
"""
    
    # Human-in-the-loop: 사용자 입력 대기
    user_input = interrupt(interrupt_message)
    
    # 사용자 선택 처리
    if user_input:
        state["user_choice"] = str(user_input).strip()
        print(f"✅ 사용자 선택: {state['user_choice']}")
    
    return state


def execute_selected_action_node(state: AgentState):
    """선택된 액션의 도구들을 순차적으로 실행"""
    print("🔍 선택된 액션을 실행하는 execute_selected_action_node 노드 실행")
    choice = state.get("user_choice", "")
    
    if choice.isdigit():
        action_idx = int(choice) - 1
        actions = state.get("recommended_actions", [])
        
        if 0 <= action_idx < len(actions):
            selected_action = actions[action_idx]
            state["selected_action_details"] = selected_action
            
            print(f"🛠 실행 중: {selected_action.get('title', 'Unknown Action')}")
            
            execution_results = []
            
            # 선택된 액션의 도구 목록 가져오기
            tools_list = selected_action.get("tools", [])
            
            if not tools_list:
                print("❌ 선택된 액션에 도구가 없습니다")
                state["execution_results"] = []
                state["result"] = "❌ 실행할 도구가 없습니다"
                return state
            
            print(f"🛠 도구 목록 실행: {[tool.get('name', 'Unknown') for tool in tools_list]}")
            
            # 도구 순차 실행
            for i, tool_spec in enumerate(tools_list):
                try:
                    tool_name = tool_spec.get("name", "")
                    tool_params = tool_spec.get("params", {})
                    
                    print(f"⚙️ 실행 ({i+1}/{len(tools_list)}): {tool_name}")
                    print(f"   파라미터: {tool_params}")
                    
                    # 실제 도구 실행
                    tool_func = get_tool_by_name(tool_name)
                    result = tool_func(**tool_params)
                    
                    execution_results.append({
                        "tool": tool_name,
                        "params": tool_params,
                        "status": "success",
                        "result": result,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    print(f"✅ {tool_name} 완료")
                    
                except Exception as e:
                    execution_results.append({
                        "tool": tool_name if 'tool_name' in locals() else "unknown",
                        "params": tool_params if 'tool_params' in locals() else {},
                        "status": "failed", 
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    print(f"❌ {tool_name if 'tool_name' in locals() else 'unknown'} 실패: {e}")
                    
                    # 중요한 도구 실패 시 중단 (첫 번째와 마지막 도구는 중요)
                    if i == 0 or i == len(tools_list) - 1:
                        print("⚠️ 중요한 도구 실패로 실행 중단")
                        break
            
            state["execution_results"] = execution_results
            
            # 실행 결과 요약
            success_count = len([r for r in execution_results if r["status"] == "success"])
            total_count = len(execution_results)
            
            if success_count == total_count:
                state["result"] = f"✅ 모든 도구 실행 완료 ({success_count}/{total_count})"
            else:
                state["result"] = f"⚠️ 일부 도구 실행 실패 ({success_count}/{total_count})"
        else:
            state["result"] = "❌ 잘못된 액션 선택"
            state["execution_results"] = []
    else:
        state["result"] = "❌ 유효하지 않은 선택"
        state["execution_results"] = []
    
    return state


def validation_node(state: AgentState):
    """실행 결과 검증 및 효과 측정"""
    print("🔍 실행 결과 검증 중...")
    
    execution_results = state.get("execution_results", [])
    
    if not execution_results:
        state["final_status"] = "failed"
        state["result"] = "❌ 실행된 도구가 없습니다"
        return state
    
    # 성공/실패 분석
    success_count = len([r for r in execution_results if r["status"] == "success"])
    total_count = len(execution_results)
    success_rate = success_count / total_count if total_count > 0 else 0
    
    # 메트릭 재수집 시뮬레이션
    print("📊 현재 시스템 상태 재확인...")
    import time
    time.sleep(2)
    
    # Mock 개선 데이터
    if success_rate >= 0.8:
        improvement_data = {
            "error_rate": 0.05,  # 개선됨
            "latency_p95_ms": 1200,  # 개선됨
            "cpu_usage_percent": 65.0,  # 개선됨
            "memory_usage_percent": 70.0  # 개선됨
        }
        
        state["final_status"] = "resolved"
        state["result"] = f"✅ 문제 해결 완료! 성공률: {success_rate:.1%}\n" + \
                         f"📈 개선사항:\n" + \
                         f"- 에러율: 25% → 5%\n" + \
                         f"- 지연시간: 3500ms → 1200ms\n" + \
                         f"- CPU 사용률: 85% → 65%"
        
        print("🎉 시스템 상태 개선 확인!")
        
    elif success_rate >= 0.5:
        state["final_status"] = "partial"
        state["result"] = f"⚠️ 부분적 개선. 성공률: {success_rate:.1%}\n" + \
                         f"추가 조치가 필요할 수 있습니다."
        
        print("⚠️ 부분적 개선 감지")
        
    else:
        state["final_status"] = "failed"
        state["result"] = f"❌ 문제 해결 실패. 성공률: {success_rate:.1%}\n" + \
                         f"수동 개입이 필요합니다."
        
        print("❌ 문제 해결 실패")
    
    return state


def manual_remediation_node(state: AgentState):
    """수동 조치 선택 시 처리"""
    print("👨‍💻 수동 조치 모드")
    print("사용자가 직접 문제를 해결하기로 선택했습니다.")
    
    state["result"] = "👨‍💻 수동 조치 진행 중. 사용자가 직접 문제를 해결합니다."
    state["final_status"] = "manual"
    state["execution_results"] = []
    
    return state


# --- 라우팅 로직 ---
def route_after_approval(state: AgentState):
    """사용자 선택에 따른 라우팅"""
    
    # human_feedback에서 choice 추출 시도
    if "human_feedback" in state and state["human_feedback"]:
        feedback = state["human_feedback"]
        choice = feedback.get("choice", "")
        
        # user_choice에 설정
        if choice:
            state["user_choice"] = choice
    
    choice = state.get("user_choice", "")
    
    if choice.isdigit():
        # 액션 선택 (1, 2, 3...)
        return "execute_action"
    elif choice == "manual":
        # 수동 조치
        return "manual"
    elif choice == "re_analyze":
        # 재분석 요청
        return "context_collector"
    else:
        return END


# --- Graph 구성 ---
workflow = StateGraph(AgentState)

# 노드 추가
workflow.add_node("SlackAlert", slack_alert_input_node)
workflow.add_node("ContextCollector", context_collector_node)
workflow.add_node("RootCauseAnalyzer", root_cause_analyzer_node)
workflow.add_node("ActionPlanner", action_planner_node)
workflow.add_node("ApprovalGate", approval_gate_node)
workflow.add_node("ExecuteAction", execute_selected_action_node)
workflow.add_node("Validation", validation_node)
workflow.add_node("ManualRemediation", manual_remediation_node)

# Edge 연결
workflow.add_edge(START, "SlackAlert")
workflow.add_edge("SlackAlert", "ContextCollector")
workflow.add_edge("ContextCollector", "RootCauseAnalyzer")
workflow.add_edge("RootCauseAnalyzer", "ActionPlanner")
workflow.add_edge("ActionPlanner", "ApprovalGate")

# 조건부 라우팅
workflow.add_conditional_edges(
    "ApprovalGate",
    route_after_approval,
    {
        "execute_action": "ExecuteAction",
        "manual": "ManualRemediation",
        "context_collector": "ContextCollector",  # 재분석 루프백
        END: END
    }
)

# 실행 후 검증
workflow.add_edge("ExecuteAction", "Validation")
workflow.add_edge("Validation", END)
workflow.add_edge("ManualRemediation", END)

# --- 실행기 ---
app = workflow.compile()

# --- Helper 함수 ---
def resume_with_user_choice(current_state: Dict[str, Any], user_choice: str):
    """사용자 선택을 반영하여 그래프 실행 재개"""
    # human_feedback 추가
    current_state["human_feedback"] = {"choice": user_choice}
    
    # 그래프 실행 재개
    return app.invoke(current_state)

if __name__ == "__main__":
    initial_state: AgentState = {"alert_context": {"service": "Service A"}}
    
    try:
        # 초기 실행 (ApprovalGate에서 interrupt 발생)
        result = app.invoke(initial_state)
        print("🎉 Final State:", result)
    except Exception as e:
        print(f"Expected interrupt at ApprovalGate: {e}")
        
        # 실제 사용 시에는 LangGraph Studio에서 사용자 입력을 받고
        # resume_with_user_choice 함수를 사용하여 재개
