"""세션 관리 모듈.

오디오 청크를 세션 단위로 그룹화하고 메타데이터를 관리합니다.
"""

import json
import logging
import sqlite3
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """단일 오디오 청크 정보."""
    file_path: str
    timestamp: datetime
    duration_seconds: float
    index: int
    rms_level: float = 0.0
    is_silent: bool = False
    speech_ratio: float = 0.0  # VAD 감지 음성 비율

    def to_dict(self) -> dict:
        """딕셔너리로 변환합니다."""
        return {
            "file_path": self.file_path,
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "index": self.index,
            "rms_level": self.rms_level,
            "is_silent": self.is_silent,
            "speech_ratio": self.speech_ratio,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AudioChunk":
        """딕셔너리에서 생성합니다."""
        return cls(
            file_path=data["file_path"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            duration_seconds=data["duration_seconds"],
            index=data["index"],
            rms_level=data.get("rms_level", 0.0),
            is_silent=data.get("is_silent", False),
            speech_ratio=data.get("speech_ratio", 0.0),
        )


@dataclass
class Session:
    """오디오 세션 정보."""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    chunks: list[AudioChunk] = field(default_factory=list)
    status: str = "recording"  # recording, completed, exported
    tags: list[str] = field(default_factory=list)
    transcription_status: str = "pending"  # pending, processing, completed, failed
    transcription_path: Optional[str] = None
    notes: str = ""
    title: str = ""  # LLM 생성 제목
    summary: str = ""  # LLM 생성 요약

    @property
    def duration_seconds(self) -> float:
        """세션 총 길이(초)를 반환합니다."""
        if not self.chunks:
            return 0.0
        return sum(c.duration_seconds for c in self.chunks if not c.is_silent)

    @property
    def total_chunks(self) -> int:
        """총 청크 수를 반환합니다."""
        return len(self.chunks)

    @property
    def avg_rms(self) -> float:
        """평균 RMS 레벨을 반환합니다."""
        non_silent = [c for c in self.chunks if not c.is_silent]
        if not non_silent:
            return 0.0
        return sum(c.rms_level for c in non_silent) / len(non_silent)

    def add_chunk(self, chunk: AudioChunk) -> None:
        """청크를 추가합니다."""
        self.chunks.append(chunk)
        self.end_time = chunk.timestamp + timedelta(seconds=chunk.duration_seconds)

    def add_tag(self, tag: str) -> None:
        """태그를 추가합니다."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """태그를 제거합니다."""
        if tag in self.tags:
            self.tags.remove(tag)

    def complete(self) -> None:
        """세션을 완료 상태로 변경합니다."""
        self.status = "completed"
        if self.chunks and self.end_time is None:
            last_chunk = self.chunks[-1]
            self.end_time = last_chunk.timestamp + timedelta(seconds=last_chunk.duration_seconds)

    def to_dict(self) -> dict:
        """딕셔너리로 변환합니다."""
        return {
            "session_id": self.session_id,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "chunks": [c.to_dict() for c in self.chunks],
            "status": self.status,
            "tags": self.tags,
            "transcription_status": self.transcription_status,
            "transcription_path": self.transcription_path,
            "notes": self.notes,
            "title": self.title,
            "summary": self.summary,
            "duration_seconds": self.duration_seconds,
            "total_chunks": self.total_chunks,
            "avg_rms": self.avg_rms,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        """딕셔너리에서 생성합니다."""
        session = cls(
            session_id=data["session_id"],
            start_time=datetime.fromisoformat(data["start_time"]),
            end_time=datetime.fromisoformat(data["end_time"]) if data.get("end_time") else None,
            status=data.get("status", "completed"),
            tags=data.get("tags", []),
            transcription_status=data.get("transcription_status", "pending"),
            transcription_path=data.get("transcription_path"),
            notes=data.get("notes", ""),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
        )
        session.chunks = [AudioChunk.from_dict(c) for c in data.get("chunks", [])]
        return session

    @classmethod
    def create_new(cls, start_time: Optional[datetime] = None) -> "Session":
        """새 세션을 생성합니다."""
        if start_time is None:
            start_time = datetime.now()

        session_id = f"sess_{start_time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        return cls(session_id=session_id, start_time=start_time)


class SessionManager:
    """세션 메타데이터를 관리합니다."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "sessions.db"
        self._init_db()

    def _init_db(self) -> None:
        """데이터베이스를 초기화합니다."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT NOT NULL,
                    end_time TEXT,
                    status TEXT DEFAULT 'recording',
                    tags TEXT DEFAULT '[]',
                    transcription_status TEXT DEFAULT 'pending',
                    transcription_path TEXT,
                    notes TEXT DEFAULT '',
                    title TEXT DEFAULT '',
                    summary TEXT DEFAULT '',
                    data TEXT NOT NULL
                )
            """)
            # 기존 테이블에 title, summary 컬럼 추가 (마이그레이션)
            try:
                conn.execute("ALTER TABLE sessions ADD COLUMN title TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass  # 이미 존재
            try:
                conn.execute("ALTER TABLE sessions ADD COLUMN summary TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass  # 이미 존재
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_start_time
                ON sessions(start_time)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_status
                ON sessions(status)
            """)
            conn.commit()

    def save_session(self, session: Session) -> None:
        """세션을 저장합니다."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sessions
                (session_id, start_time, end_time, status, tags,
                 transcription_status, transcription_path, notes, title, summary, data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                session.session_id,
                session.start_time.isoformat(),
                session.end_time.isoformat() if session.end_time else None,
                session.status,
                json.dumps(session.tags),
                session.transcription_status,
                session.transcription_path,
                session.notes,
                session.title,
                session.summary,
                json.dumps(session.to_dict()),
            ))
            conn.commit()

        logger.debug(f"세션 저장됨: {session.session_id}")

    def get_session(self, session_id: str) -> Optional[Session]:
        """세션 ID로 세션을 가져옵니다."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            row = cursor.fetchone()

        if row:
            return Session.from_dict(json.loads(row[0]))
        return None

    def list_sessions(
        self,
        date: Optional[datetime] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 100,
    ) -> list[Session]:
        """세션 목록을 가져옵니다."""
        query = "SELECT data FROM sessions WHERE 1=1"
        params = []

        if date:
            date_str = date.strftime("%Y-%m-%d")
            query += " AND start_time LIKE ?"
            params.append(f"{date_str}%")

        if status:
            query += " AND status = ?"
            params.append(status)

        if tag:
            query += " AND tags LIKE ?"
            params.append(f'%"{tag}"%')

        query += " ORDER BY start_time DESC LIMIT ?"
        params.append(limit)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()

        return [Session.from_dict(json.loads(row[0])) for row in rows]

    def list_sessions_by_date(self, date: datetime) -> list[Session]:
        """특정 날짜의 세션 목록을 가져옵니다."""
        return self.list_sessions(date=date)

    def get_today_sessions(self) -> list[Session]:
        """오늘 세션 목록을 가져옵니다."""
        return self.list_sessions(date=datetime.now())

    def delete_session(self, session_id: str, delete_files: bool = False) -> bool:
        """세션을 삭제합니다."""
        session = self.get_session(session_id)
        if not session:
            return False

        # 파일 삭제 옵션
        if delete_files:
            for chunk in session.chunks:
                chunk_path = self.data_dir / chunk.file_path
                if chunk_path.exists():
                    chunk_path.unlink()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()

        logger.info(f"세션 삭제됨: {session_id}")
        return True

    def get_sessions_older_than(self, days: int) -> list[Session]:
        """지정된 일수보다 오래된 세션을 가져옵니다."""
        cutoff = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff.isoformat()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT data FROM sessions WHERE start_time < ?",
                (cutoff_str,)
            )
            rows = cursor.fetchall()

        return [Session.from_dict(json.loads(row[0])) for row in rows]

    def cleanup_old_sessions(self, retention_days: int, delete_files: bool = True) -> int:
        """오래된 세션을 정리합니다."""
        old_sessions = self.get_sessions_older_than(retention_days)
        count = 0

        for session in old_sessions:
            if self.delete_session(session.session_id, delete_files=delete_files):
                count += 1

        logger.info(f"{count}개의 오래된 세션 삭제됨")
        return count

    def export_session(
        self,
        session_id: str,
        output_path: Optional[Path] = None,
    ) -> Optional[Path]:
        """세션을 단일 오디오 파일로 내보냅니다."""
        import wave

        import numpy as np

        session = self.get_session(session_id)
        if not session:
            logger.error(f"세션을 찾을 수 없음: {session_id}")
            return None

        if output_path is None:
            exports_dir = self.data_dir / "exports"
            exports_dir.mkdir(exist_ok=True)
            output_path = exports_dir / f"{session_id}.wav"

        # 청크 파일 병합
        all_audio = []
        sample_rate = None
        channels = None

        for chunk in session.chunks:
            if chunk.is_silent:
                continue

            chunk_path = self.data_dir / chunk.file_path
            if not chunk_path.exists():
                logger.warning(f"청크 파일 없음: {chunk_path}")
                continue

            try:
                with wave.open(str(chunk_path), "rb") as wf:
                    if sample_rate is None:
                        sample_rate = wf.getframerate()
                        channels = wf.getnchannels()

                    frames = wf.readframes(wf.getnframes())
                    audio = np.frombuffer(frames, dtype=np.int16)
                    all_audio.append(audio)
            except Exception as e:
                logger.error(f"청크 읽기 실패: {chunk_path} - {e}")

        if not all_audio:
            logger.error("내보낼 오디오가 없음")
            return None

        # 병합 및 저장
        merged = np.concatenate(all_audio)

        with wave.open(str(output_path), "wb") as wf:
            wf.setnchannels(channels or 1)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate or 16000)
            wf.writeframes(merged.tobytes())

        # 세션 상태 업데이트
        session.status = "exported"
        self.save_session(session)

        logger.info(f"세션 내보내기 완료: {output_path}")
        return output_path

    def get_stats(self) -> dict:
        """저장소 통계를 반환합니다."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM sessions")
            total_sessions = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE status = 'recording'"
            )
            recording_sessions = cursor.fetchone()[0]

            cursor = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE transcription_status = 'completed'"
            )
            transcribed_sessions = cursor.fetchone()[0]

        # 디스크 사용량 계산
        total_size = 0
        for path in self.data_dir.rglob("*.wav"):
            total_size += path.stat().st_size

        return {
            "total_sessions": total_sessions,
            "recording_sessions": recording_sessions,
            "transcribed_sessions": transcribed_sessions,
            "disk_usage_bytes": total_size,
            "disk_usage_mb": total_size / (1024 * 1024),
        }
