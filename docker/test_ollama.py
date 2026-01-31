"""Ollama 연결 테스트."""

from voicelink.title_generator import TitleGenerator, TitleGeneratorConfig

print("=" * 60)
print("  Ollama LLM 연결 테스트")
print("=" * 60)
print()

config = TitleGeneratorConfig()
generator = TitleGenerator(config)

# 연결 확인
print(f"Ollama URL: {config.ollama_url}")
print(f"모델: {config.model}")
print()

if generator.is_available():
    print("✅ Ollama 서버 연결 성공!")
    print()

    # 사용 가능한 모델 목록
    models = generator.list_models()
    print(f"📦 사용 가능한 모델: {len(models)}개")
    for m in models:
        print(f"  - {m}")

    # 필요한 모델이 있는지 확인
    if config.model not in models and f"{config.model}:latest" not in models:
        print()
        print(f"⚠️  {config.model} 모델이 없습니다. 다음 명령으로 다운로드하세요:")
        print(f"   docker exec -it voicelink-ollama ollama pull {config.model}")
    else:
        print()
        print("🧪 제목 생성 테스트:")
        print()

        test_cases = [
            "오늘 회의에서 AI 프로젝트 일정을 논의했습니다. 다음 주 월요일까지 프로토타입을 완성하기로 했습니다.",
            "유튜브에서 파이썬 프로그래밍 강좌를 시청했습니다. 클래스와 객체에 대해 배웠습니다.",
            "고객사와 통화했습니다. 다음 달 납품 일정을 조율했습니다.",
        ]

        for i, transcript in enumerate(test_cases, 1):
            print(f"  [{i}] 전사문: {transcript[:50]}...")
            title = generator.generate(transcript)
            print(f"      → 제목: {title}")
            print()

else:
    print("❌ Ollama 서버 연결 실패!")
    print()
    print("다음 단계를 확인하세요:")
    print("  1. Docker Desktop 실행 중인지 확인")
    print("  2. Ollama 컨테이너 시작:")
    print("     docker compose -f docker/docker-compose.yml up -d")
    print("  3. 모델 다운로드:")
    print("     docker exec -it voicelink-ollama ollama pull qwen2.5:3b")

print()
print("=" * 60)
