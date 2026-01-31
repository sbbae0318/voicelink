# VoiceLink + Ollama 로컬 LLM 연동

## 시스템 요구사항

- Windows 11 + Docker Desktop (이미 설치됨)
- NVIDIA GPU (RTX 3090 Ti 24GB) ✅

## 추천 모델

| 용도 | 모델 | VRAM | 속도 |
|------|------|------|------|
| 제목 생성 (빠름) | `qwen2.5:3b` | ~3GB | 매우 빠름 |
| 제목 생성 (정확) | `qwen2.5:7b` | ~5GB | 빠름 |
| 요약 (고품질) | `llama3:8b` | ~6GB | 빠름 |

## 설치 및 실행

### 1. Ollama 컨테이너 시작

```powershell
docker compose -f docker/docker-compose.yml up -d
```

### 2. 모델 다운로드 (최초 1회)

```powershell
docker exec -it voicelink-ollama ollama pull qwen2.5:3b
```

### 3. 테스트

```powershell
python docker/test_ollama.py
```

## API 사용법

```python
from voicelink.title_generator import generate_session_title

title = generate_session_title(transcript="오늘 회의에서 AI 프로젝트 일정을 논의했습니다...")
print(title)  # "AI 프로젝트 일정 회의"
```
