"""VoiceLink 웹 대시보드 API.

FastAPI 기반 세션 관리 및 시각화 API입니다.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# 환경변수에서 데이터 디렉토리 가져오기
DATA_DIR = Path(os.getenv("VOICELINK_DATA_DIR", "./test_recordings"))

# SessionManager import (상대 경로 조정)
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from voicelink.session import SessionManager
from voicelink.title_generator import TitleGenerator, TitleGeneratorConfig

app = FastAPI(
    title="VoiceLink Dashboard API",
    description="세션 관리 및 시각화 API",
    version="0.1.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 (프론트엔드)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


class SessionSummary(BaseModel):
    """세션 요약 정보."""
    session_id: str
    date: str
    start_time: str
    end_time: Optional[str]
    duration_seconds: float
    duration_formatted: str
    status: str
    title: str
    summary: str
    total_chunks: int
    tags: list[str]


class StatsResponse(BaseModel):
    """통계 응답."""
    total_sessions: int
    recording_sessions: int
    transcribed_sessions: int
    disk_usage_mb: float


class GenerateSummaryRequest(BaseModel):
    """요약 생성 요청."""
    transcript: str


def format_duration(seconds: float) -> str:
    """초를 HH:MM:SS 형식으로 변환."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def get_session_manager() -> SessionManager:
    """세션 매니저 인스턴스를 반환."""
    return SessionManager(DATA_DIR)


def get_title_generator() -> TitleGenerator:
    """제목 생성기 인스턴스를 반환."""
    ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434")
    return TitleGenerator(TitleGeneratorConfig(ollama_url=ollama_url))


@app.get("/")
async def root():
    """대시보드 메인 페이지."""
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"message": "VoiceLink Dashboard API", "docs": "/docs"}


@app.get("/api/sessions", response_model=list[SessionSummary])
async def list_sessions(
    date: Optional[str] = Query(None, description="날짜 필터 (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="상태 필터"),
    limit: int = Query(100, description="최대 개수"),
):
    """세션 목록을 반환합니다."""
    manager = get_session_manager()
    
    filter_date = None
    if date:
        try:
            filter_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(400, "잘못된 날짜 형식입니다. YYYY-MM-DD 형식을 사용하세요.")
    
    sessions = manager.list_sessions(date=filter_date, status=status, limit=limit)
    
    return [
        SessionSummary(
            session_id=s.session_id,
            date=s.start_time.strftime("%Y-%m-%d"),
            start_time=s.start_time.strftime("%H:%M:%S"),
            end_time=s.end_time.strftime("%H:%M:%S") if s.end_time else None,
            duration_seconds=s.duration_seconds,
            duration_formatted=format_duration(s.duration_seconds),
            status=s.status,
            title=s.title or "제목 없음",
            summary=s.summary or "",
            total_chunks=s.total_chunks,
            tags=s.tags,
        )
        for s in sessions
    ]


@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """세션 상세 정보를 반환합니다."""
    manager = get_session_manager()
    session = manager.get_session(session_id)
    
    if not session:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    
    return session.to_dict()


@app.post("/api/sessions/{session_id}/generate-summary")
async def generate_summary(session_id: str, request: GenerateSummaryRequest):
    """세션 요약을 생성합니다."""
    manager = get_session_manager()
    session = manager.get_session(session_id)
    
    if not session:
        raise HTTPException(404, "세션을 찾을 수 없습니다.")
    
    generator = get_title_generator()
    
    if not generator.is_available():
        raise HTTPException(503, "LLM 서버에 연결할 수 없습니다.")
    
    # 제목 생성
    title = generator.generate(request.transcript)
    
    # 요약 생성 (같은 내용 사용)
    summary = request.transcript[:200] + "..." if len(request.transcript) > 200 else request.transcript
    
    # 세션 업데이트
    session.title = title
    session.summary = summary
    manager.save_session(session)
    
    return {"title": title, "summary": summary}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """저장소 통계를 반환합니다."""
    manager = get_session_manager()
    stats = manager.get_stats()
    
    return StatsResponse(**stats)


@app.get("/api/dates")
async def get_available_dates():
    """녹음이 있는 날짜 목록을 반환합니다."""
    manager = get_session_manager()
    sessions = manager.list_sessions(limit=1000)
    
    dates = sorted(set(s.start_time.strftime("%Y-%m-%d") for s in sessions), reverse=True)
    return {"dates": dates}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str, delete_files: bool = False):
    """세션을 삭제합니다."""
    manager = get_session_manager()
    
    if manager.delete_session(session_id, delete_files=delete_files):
        return {"message": "세션이 삭제되었습니다."}
    
    raise HTTPException(404, "세션을 찾을 수 없습니다.")


@app.get("/api/health")
async def health_check():
    """헬스 체크."""
    generator = get_title_generator()
    return {
        "status": "ok",
        "llm_available": generator.is_available(),
        "data_dir": str(DATA_DIR),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
