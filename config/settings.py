import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

class Settings:
    """애플리케이션 설정 관리"""
    
    # OpenAI 설정
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_TEMPERATURE = float(os.getenv("OPENAI_TEMPERATURE", "0.1"))
    
    # AWS 설정
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-2")
    
    # Datadog 설정
    DATADOG_API_KEY = os.getenv("DATADOG_API_KEY")
    DATADOG_APP_KEY = os.getenv("DATADOG_APP_KEY")
    
    # Slack 설정
    SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
    
    @classmethod
    def validate_openai_config(cls):
        """OpenAI 설정 검증"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.")
        return True

# 전역 설정 인스턴스
settings = Settings()
