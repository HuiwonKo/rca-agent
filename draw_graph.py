#!/usr/bin/env python3
"""
간단한 LangGraph 시각화 스크립트

draw_mermaid_png 메서드로 RCA Agent 그래프를 PNG로 저장
"""

from agent.graph import app
from pathlib import Path

def save_langgraph_png():
    """LangGraph를 PNG로 저장"""
    try:
        # 현재 디렉토리에 PNG 파일 저장
        output_path = Path("rca_agent_graph.png")
        
        print("🎨 LangGraph 구조 시각화 중...")
        
        # draw_mermaid_png 메서드 사용
        png_data = app.get_graph().draw_mermaid_png()
        
        # PNG 파일로 저장
        with open(output_path, "wb") as f:
            f.write(png_data)
        
        print(f"✅ 성공! 그래프가 저장되었습니다: {output_path.absolute()}")
        
        # 파일 정보
        file_size = output_path.stat().st_size / 1024  # KB
        print(f"📊 파일 크기: {file_size:.1f} KB")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("💡 대신 generate_graph_image.py를 사용해보세요.")

if __name__ == "__main__":
    save_langgraph_png()
