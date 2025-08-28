#!/usr/bin/env python3
"""
RCA Agent Gradio Demo
LangGraph 기반 Root Cause Analysis 에이전트의 Gradio 시연 인터페이스
"""

import gradio as gr
import json
import traceback
from datetime import datetime
from typing import Dict, List, Any
import time

# RCA Agent 컴포넌트 import
from agent.graph import app as rca_agent
from agent.state import AgentState


class RCAGradioDemo:
    """RCA Agent Gradio 데모 클래스"""
    
    def __init__(self):
        self.current_state = {}
        self.execution_history = []
        
    def simulate_slack_alert(self, service_name: str, error_time: str) -> Dict[str, Any]:
        """Slack 알림 시뮬레이션"""
        return {
            "timestamp": error_time,
            "channel": "#alerts",
            "service": service_name,
            "alert_type": "critical",
            "description": f"{service_name}에서 장애 발생",
            "severity": "high"
        }
    
    def run_rca_analysis(
        self, 
        service_name: str, 
        error_time: str
    ) -> tuple:
        """RCA 분석 실행 (Approval Gate까지)"""
        try:
            # 초기 상태 설정
            initial_state = {
                "slack_alert": self.simulate_slack_alert(service_name, error_time),
                "context": {},
                "metrics": {},  # context_collector_node에서 설정됨
                "logs": [],
                "traces": [],
                "root_cause": "",
                "recommended_actions": [],
                "user_choice": "",
                "selected_action_details": {},
                "execution_results": [],
                "final_status": "",
                "human_feedback": {}
            }
            
            # RCA 에이전트 실행 (Approval Gate까지)
            print(f"🚀 RCA 분석 시작: {service_name}")
            
            # SlackAlert부터 ApprovalGate까지 실행
            result = rca_agent.invoke(initial_state, {
                "recursion_limit": 50
            })
            
            self.current_state = result
            
            # 결과 포맷팅
            analysis_result = self._format_analysis_result(result)
            actions_info = self._format_actions_for_display(result.get("recommended_actions", []))
            
            return analysis_result, actions_info, gr.update(visible=True)
            
        except Exception as e:
            error_msg = f"❌ RCA 분석 중 오류 발생:\n{str(e)}\n\n{traceback.format_exc()}"
            return error_msg, "", gr.update(visible=False)
    
    def execute_selected_action(self, choice: str) -> str:
        """선택된 액션 실행"""
        try:
            if not self.current_state:
                return "❌ 먼저 RCA 분석을 실행해주세요."
            
            if not choice:
                return "❌ 액션을 선택해주세요."
            
            # 유효한 선택인지 확인
            valid_choices = ["1", "2", "3", "manual", "re_analyze"]
            if choice not in valid_choices:
                return f"❌ 올바른 액션을 선택해주세요. 유효한 선택: {', '.join(valid_choices)}"
            
            # manual이나 re_analyze 선택 처리
            if choice == "manual":
                return self._handle_manual_action()
            elif choice == "re_analyze":
                return self._handle_reanalyze_action()
            
            # 사용자 선택을 상태에 추가
            self.current_state["user_choice"] = choice
            self.current_state["human_feedback"] = {
                "choice": choice,
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"🎯 사용자 선택: {choice}")
            
            # ApprovalGate에서 ExecuteAction까지 실행
            result = rca_agent.invoke(self.current_state, {
                "recursion_limit": 50
            })
            
            self.current_state = result
            
            # 실행 결과 포맷팅
            execution_result = self._format_execution_result(result)
            
            # 실행 히스토리에 추가
            self.execution_history.append({
                "timestamp": datetime.now().isoformat(),
                "choice": choice,
                "result": result.get("execution_results", []),
                "final_status": result.get("final_status", "")
            })
            
            return execution_result
            
        except Exception as e:
            error_msg = f"❌ 액션 실행 중 오류 발생:\n{str(e)}\n\n{traceback.format_exc()}"
            return error_msg
    
    def _format_analysis_result(self, state: Dict[str, Any]) -> str:
        """분석 결과 포맷팅"""
        lines = []
        lines.append("🔍 **Root Cause Analysis 결과**")
        lines.append("=" * 50)
        
        # 근본 원인
        root_cause = state.get("root_cause", "분석 결과 없음")
        lines.append(f"\n📊 **근본 원인:**\n{root_cause}")
        
        # 메트릭 정보
        metrics = state.get("metrics", {})
        lines.append(f"\n📈 **현재 상황:**")
        lines.append(f"- 에러율: {metrics.get('error_rate', 'N/A')}")
        lines.append(f"- 지연시간(P95): {metrics.get('latency_p95_ms', 'N/A')}ms")
        lines.append(f"- 영향받는 서비스: {metrics.get('affected_services', 'N/A')}")
        
        # 컨텍스트 정보
        context = state.get("context", {})
        if context:
            lines.append(f"\n🔧 **시스템 컨텍스트:**")
            for key, value in context.items():
                lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)
    
    def _format_actions_for_display(self, actions: List[Dict[str, Any]]) -> str:
        """액션 목록 포맷팅"""
        if not actions:
            return "❌ 추천 액션이 없습니다."
        
        lines = []
        lines.append("🎯 **추천 조치 액션**")
        lines.append("=" * 50)
        
        for i, action in enumerate(actions, 1):
            lines.append(f"\n**{i}. {action.get('title', f'Action {i}')}**")
            lines.append(f"설명: {action.get('description', '')}")
            lines.append(f"위험도: {action.get('risk_level', 'N/A')}")
            lines.append(f"예상 시간: {action.get('estimated_time', 'N/A')}")
            
            # 도구 목록
            tools = action.get('tools', [])
            if tools:
                lines.append("실행할 도구:")
                for tool in tools:
                    tool_name = tool.get('name', 'Unknown')
                    tool_params = tool.get('params', {})
                    lines.append(f"  • {tool_name}: {tool_params}")
            
            lines.append("")
        
        # 추가 옵션들
        lines.append("**📋 추가 옵션:**")
        lines.append("")
        lines.append("**manual. 수동 처리**")
        lines.append("설명: 시스템 관리자가 직접 문제를 해결합니다")
        lines.append("위험도: 사용자 판단")
        lines.append("예상 시간: 사용자 판단")
        lines.append("")
        
        lines.append("**re_analyze. 재분석**")
        lines.append("설명: 시스템 상태를 다시 분석합니다")
        lines.append("위험도: 없음")
        lines.append("예상 시간: 3-5분")
        lines.append("")
        
        lines.append("👆 위 액션 중 하나를 선택하여 실행하세요.")
        return "\n".join(lines)
    
    def _format_execution_result(self, state: Dict[str, Any]) -> str:
        """실행 결과 포맷팅"""
        lines = []
        lines.append("⚡ **액션 실행 결과**")
        lines.append("=" * 50)
        
        # 선택된 액션 정보
        selected_action = state.get("selected_action_details", {})
        if selected_action:
            lines.append(f"\n🎯 **실행된 액션:** {selected_action.get('title', 'Unknown')}")
            lines.append(f"설명: {selected_action.get('description', '')}")
        
        # 실행 결과
        execution_results = state.get("execution_results", [])
        if execution_results:
            lines.append(f"\n🛠 **도구 실행 결과:**")
            
            success_count = 0
            for result in execution_results:
                tool_name = result.get("tool", "Unknown")
                status = result.get("status", "unknown")
                
                if status == "success":
                    lines.append(f"✅ {tool_name}: 성공")
                    success_count += 1
                    tool_result = result.get("result", {})
                    if isinstance(tool_result, dict):
                        for key, value in tool_result.items():
                            lines.append(f"   - {key}: {value}")
                else:
                    lines.append(f"❌ {tool_name}: 실패")
                    error = result.get("error", "Unknown error")
                    lines.append(f"   오류: {error}")
                
                lines.append("")
            
            lines.append(f"📊 **실행 요약:** {success_count}/{len(execution_results)} 성공")
        
        # 최종 상태
        final_status = state.get("final_status", "")
        if final_status:
            lines.append(f"\n🏁 **최종 상태:** {final_status}")
        
        return "\n".join(lines)
    
    def _handle_manual_action(self) -> str:
        """수동 처리 액션 핸들링"""
        try:
            # 수동 처리를 상태에 추가
            self.current_state["user_choice"] = "manual"
            self.current_state["human_feedback"] = {
                "choice": "manual",
                "timestamp": datetime.now().isoformat()
            }
            
            print("🔧 수동 처리 선택됨")
            
            # Manual Remediation 노드 실행
            try:
                result = rca_agent.invoke(self.current_state, {
                    "recursion_limit": 50
                })
            except Exception as continue_e:
                print(f"⚠️ 그래프 재개 중 오류: {str(continue_e)}")
                # 직접 노드 실행으로 fallback
                from agent.graph import manual_remediation_node
                
                state = self.current_state.copy()
                state = manual_remediation_node(state)
                
                result = state
            
            self.current_state = result
            
            # 수동 처리 결과 포맷팅
            lines = []
            lines.append("🔧 **수동 처리 선택됨**")
            lines.append("=" * 50)
            lines.append("\n📝 **안내사항:**")
            lines.append("- 시스템 관리자가 직접 문제를 해결해야 합니다")
            lines.append("- 근본 원인을 참고하여 적절한 조치를 취하세요")
            lines.append("- 해결 후 시스템 상태를 모니터링하세요")
            
            root_cause = self.current_state.get("root_cause", "")
            if root_cause:
                lines.append(f"\n🔍 **참고 - 근본 원인:**")
                lines.append(root_cause)
            
            lines.append(f"\n🏁 **최종 상태:** {result.get('final_status', '수동 처리 대기 중')}")
            
            # 실행 히스토리에 추가
            self.execution_history.append({
                "timestamp": datetime.now().isoformat(),
                "choice": "manual",
                "result": [],
                "final_status": "수동 처리"
            })
            
            return "\n".join(lines)
            
        except Exception as e:
            error_msg = f"❌ 수동 처리 중 오류 발생:\n{str(e)}"
            return error_msg
    
    def _handle_reanalyze_action(self) -> str:
        """재분석 액션 핸들링"""
        try:
            # 재분석을 위해 상태 초기화
            print("🔄 재분석 시작...")
            
            # 기본 정보는 유지하고 분석 결과만 초기화
            slack_alert = self.current_state.get("slack_alert", {})
            
            # 재분석을 위한 새 상태 생성
            reanalyze_state = {
                "slack_alert": slack_alert,
                "context": {},
                "metrics": {},
                "logs": [],
                "traces": [],
                "root_cause": "",
                "recommended_actions": [],
                "user_choice": "",
                "selected_action_details": {},
                "execution_results": [],
                "final_status": "",
                "human_feedback": {}
            }
            
            # 재분석 실행 (ActionPlanner까지)
            try:
                from agent.graph import (
                    context_collector_node, 
                    root_cause_analyzer_node, 
                    action_planner_node
                )
                
                state = reanalyze_state.copy()
                state = context_collector_node(state)
                state = root_cause_analyzer_node(state)
                state = action_planner_node(state)
                
                self.current_state = state
                result = state
                
            except Exception as e:
                print(f"⚠️ 재분석 중 오류: {str(e)}")
                return f"❌ 재분석 중 오류가 발생했습니다: {str(e)}"
            
            # 재분석 결과 포맷팅
            lines = []
            lines.append("🔄 **재분석 완료**")
            lines.append("=" * 50)
            
            # 새로운 근본 원인
            root_cause = result.get("root_cause", "분석 결과 없음")
            lines.append(f"\n🔍 **새로운 근본 원인:**")
            lines.append(root_cause)
            
            # 새로운 추천 액션
            actions = result.get("recommended_actions", [])
            if actions:
                lines.append(f"\n🎯 **새로운 추천 액션:** {len(actions)}개")
                for i, action in enumerate(actions[:3], 1):
                    lines.append(f"{i}. {action.get('title', f'Action {i}')}")
                    lines.append(f"   - {action.get('description', '')}")
            
            lines.append(f"\n💡 **다음 단계:** 위의 새로운 분석 결과를 바탕으로 액션을 선택하세요.")
            
            # 실행 히스토리에 추가
            self.execution_history.append({
                "timestamp": datetime.now().isoformat(),
                "choice": "re_analyze",
                "result": [],
                "final_status": "재분석 완료"
            })
            
            return "\n".join(lines)
            
        except Exception as e:
            error_msg = f"❌ 재분석 중 오류 발생:\n{str(e)}"
            return error_msg
    
    def get_execution_history(self) -> str:
        """실행 히스토리 조회"""
        if not self.execution_history:
            return "📝 아직 실행된 액션이 없습니다."
        
        lines = []
        lines.append("📜 **실행 히스토리**")
        lines.append("=" * 50)
        
        for i, entry in enumerate(self.execution_history, 1):
            lines.append(f"\n**{i}. {entry['timestamp']}**")
            lines.append(f"선택한 액션: {entry['choice']}")
            lines.append(f"최종 상태: {entry['final_status']}")
            
            results = entry['result']
            success_count = len([r for r in results if r.get('status') == 'success'])
            lines.append(f"실행 결과: {success_count}/{len(results)} 성공")
            lines.append("")
        
        return "\n".join(lines)


def create_gradio_interface():
    """Gradio 인터페이스 생성"""
    
    demo_instance = RCAGradioDemo()
    
    with gr.Blocks(
        title="RCA Agent Demo", 
        theme=gr.themes.Soft(),
        css="""
        .gradio-container {
            max-width: 1200px !important;
        }
        """
    ) as demo:
        
        gr.Markdown("""
        # 🤖 RCA Agent 시연
        
        **LangGraph 기반 Root Cause Analysis 에이전트**
        
        이 데모는 시스템 장애 발생 시 자동으로 근본 원인을 분석하고 
        적절한 조치를 추천하는 RCA 에이전트를 시연합니다.
        """)
        
        with gr.Row():
            with gr.Column(scale=1):
                gr.Markdown("## 📥 입력 정보")
                
                service_name = gr.Textbox(
                    label="서비스 이름",
                    value="api-service",
                    placeholder="예: api-service, web-frontend, user-auth"
                )
                
                error_time = gr.Textbox(
                    label="에러 발생 시간",
                    value=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    placeholder="YYYY-MM-DD HH:MM:SS",
                    info="장애가 발생한 시간을 입력하세요"
                )
                
                analyze_btn = gr.Button(
                    "🔍 RCA 분석 시작", 
                    variant="primary",
                    size="lg"
                )
            
            with gr.Column(scale=2):
                gr.Markdown("## 📊 분석 결과")
                
                analysis_output = gr.Textbox(
                    label="근본 원인 분석",
                    lines=15,
                    interactive=False
                )
        
        with gr.Row(visible=False) as action_section:
            with gr.Column():
                gr.Markdown("## 🎯 추천 액션")
                
                actions_output = gr.Textbox(
                    label="추천 조치 목록",
                    lines=20,
                    interactive=False
                )
                
                with gr.Row():
                    action_choice = gr.Radio(
                        choices=["1", "2", "3", "manual", "re_analyze"],
                        label="실행할 액션 선택",
                        value="1",
                        info="1, 2, 3: 추천 액션 / manual: 수동 처리 / re_analyze: 재분석"
                    )
                    
                    execute_btn = gr.Button(
                        "⚡ 액션 실행",
                        variant="secondary"
                    )
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("## 📋 실행 결과")
                
                execution_output = gr.Textbox(
                    label="액션 실행 결과",
                    lines=15,
                    interactive=False
                )
        
        with gr.Row():
            with gr.Column():
                gr.Markdown("## 📜 실행 히스토리")
                
                history_output = gr.Textbox(
                    label="지금까지의 실행 기록",
                    lines=10,
                    interactive=False
                )
                
                refresh_history_btn = gr.Button("🔄 히스토리 새로고침")
        
        # 이벤트 바인딩
        analyze_btn.click(
            fn=demo_instance.run_rca_analysis,
            inputs=[service_name, error_time],
            outputs=[analysis_output, actions_output, action_section]
        )
        
        execute_btn.click(
            fn=demo_instance.execute_selected_action,
            inputs=[action_choice],
            outputs=[execution_output]
        )
        
        refresh_history_btn.click(
            fn=demo_instance.get_execution_history,
            outputs=[history_output]
        )
        
        # 시작 시 샘플 데이터 로드
        demo.load(
            fn=lambda: "🎯 서비스 이름과 에러 발생 시간을 입력하고 'RCA 분석 시작' 버튼을 클릭하세요.\n\n시스템에서 자동으로 모니터링 데이터(로그, 메트릭, 트레이스)를 수집하여 분석합니다.",
            outputs=[analysis_output]
        )
    
    return demo


if __name__ == "__main__":
    print("🚀 RCA Agent Gradio Demo 시작...")
    
    # Gradio 인터페이스 생성 및 실행
    demo = create_gradio_interface()
    
    # 서버 실행
    demo.launch(
        server_name="0.0.0.0",  # 외부 접속 허용
        server_port=7860,       # 포트 지정
        share=False,            # 공유 링크 생성 안함
        debug=True,             # 디버그 모드
        show_error=True         # 오류 표시
    )
