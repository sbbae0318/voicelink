"""세션 제목 자동 생성 모듈.

Ollama 로컬 LLM을 사용하여 세션 제목을 자동 생성합니다.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)


@dataclass
class TitleGeneratorConfig:
    """제목 생성기 설정."""
    ollama_url: str = "http://localhost:11434"
    model: str = "qwen2.5:3b"  # 빠르고 정확한 모델
    timeout: float = 30.0
    max_transcript_length: int = 1000  # 전사문 최대 길이


class TitleGenerator:
    """Ollama 기반 세션 제목 생성기."""

    PROMPT_TEMPLATE = """다음은 오디오 녹음의 전사문입니다. 이 내용을 5단어 이내로 요약하여 제목을 만들어주세요.
제목만 출력하세요. 다른 설명은 하지 마세요.

전사문:
{transcript}

제목:"""

    def __init__(self, config: Optional[TitleGeneratorConfig] = None):
        self.config = config or TitleGeneratorConfig()
        self._client = httpx.Client(timeout=self.config.timeout)

    def is_available(self) -> bool:
        """Ollama 서버 연결 가능 여부를 확인합니다."""
        try:
            response = self._client.get(f"{self.config.ollama_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list[str]:
        """사용 가능한 모델 목록을 반환합니다."""
        try:
            response = self._client.get(f"{self.config.ollama_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"모델 목록 조회 실패: {e}")
        return []

    def generate(self, transcript: str) -> str:
        """전사문에서 제목을 생성합니다."""
        if not transcript or len(transcript.strip()) < 10:
            return "무음 녹음"

        # 전사문 길이 제한
        if len(transcript) > self.config.max_transcript_length:
            transcript = transcript[:self.config.max_transcript_length] + "..."

        prompt = self.PROMPT_TEMPLATE.format(transcript=transcript)

        try:
            response = self._client.post(
                f"{self.config.ollama_url}/api/generate",
                json={
                    "model": self.config.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 50,
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                title = result.get("response", "").strip()
                # 제목 정리 (따옴표, 줄바꿈 제거)
                title = re.sub(r'^["\']|["\']$', '', title)
                title = title.split('\n')[0].strip()
                return title if title else "녹음"

        except Exception as e:
            logger.error(f"제목 생성 실패: {e}")

        return self._fallback_title(transcript)

    def _fallback_title(self, transcript: str) -> str:
        """폴백: 간단한 규칙 기반 제목 생성."""
        keywords = {
            "회의": "회의 녹음",
            "미팅": "미팅 녹음",
            "통화": "통화 녹음",
            "강의": "강의 녹음",
            "발표": "발표 녹음",
            "인터뷰": "인터뷰 녹음",
        }
        for kw, title in keywords.items():
            if kw in transcript:
                return title
        return "녹음"


# 편의 함수
_generator: Optional[TitleGenerator] = None


def get_title_generator() -> TitleGenerator:
    """싱글톤 제목 생성기를 반환합니다."""
    global _generator
    if _generator is None:
        _generator = TitleGenerator()
    return _generator


def generate_session_title(
    transcript: str,
    model: Optional[str] = None,
) -> str:
    """세션 제목을 생성합니다.

    Args:
        transcript: 전사문
        model: 사용할 모델 (기본: qwen2.5:3b)

    Returns:
        생성된 제목
    """
    generator = get_title_generator()
    if model:
        generator.config.model = model
    return generator.generate(transcript)
