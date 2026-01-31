"""Whisper 음성 인식 통합 모듈.

OpenAI Whisper API와 연동하여 음성을 텍스트로 변환합니다.
listener 프로젝트의 ask.py에서 영감을 받아 개선된 버전입니다.
"""

import json
import logging
import os
import re
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Whisper 전사 결과."""
    
    text: str
    file_path: Optional[Path] = None
    duration: float = 0.0
    is_silent: bool = False
    rms_level: float = 0.0


@dataclass
class WhisperConfig:
    """Whisper API 설정."""
    
    model: str = "whisper-1"
    language: Optional[str] = None  # None for auto-detect
    prompt: Optional[str] = None
    temperature: float = 0.0
    sample_rate: int = 16000  # Whisper 권장 샘플레이트


def get_optimal_sample_rate() -> int:
    """Whisper에 최적화된 샘플 레이트를 반환합니다.
    
    Returns:
        16000 (Whisper 권장 샘플 레이트)
    """
    return 16000


def check_audio_for_silence(
    wav_path: Union[str, Path],
    silence_threshold: float = 500,
) -> tuple[bool, float]:
    """WAV 파일이 무음인지 확인합니다.
    
    Args:
        wav_path: WAV 파일 경로
        silence_threshold: RMS 임계값 (int16 기준)
    
    Returns:
        (is_silent, rms_value) 튜플
    """
    with wave.open(str(wav_path), 'rb') as wf:
        frames = wf.readframes(wf.getnframes())
        audio = np.frombuffer(frames, dtype=np.int16)
        rms = float(np.sqrt(np.mean(audio.astype(np.float32) ** 2)))
    
    return rms < silence_threshold, rms


def transcribe_audio(
    audio_path: Union[str, Path],
    config: Optional[WhisperConfig] = None,
    api_key: Optional[str] = None,
    skip_silent: bool = True,
    silence_threshold: float = 500,
) -> TranscriptionResult:
    """오디오 파일을 Whisper API로 전사합니다.
    
    Args:
        audio_path: 오디오 파일 경로
        config: Whisper 설정
        api_key: OpenAI API 키 (None이면 환경변수 사용)
        skip_silent: 무음 파일 건너뛰기
        silence_threshold: 무음 판정 임계값
    
    Returns:
        TranscriptionResult 객체
    """
    try:
        import openai
    except ImportError:
        raise ImportError(
            "Whisper 기능을 사용하려면 openai를 설치하세요: pip install openai"
        )
    
    audio_path = Path(audio_path)
    config = config or WhisperConfig()
    
    # API 키 설정
    if api_key:
        openai.api_key = api_key
    elif os.getenv("OPENAI_API_KEY"):
        openai.api_key = os.getenv("OPENAI_API_KEY")
    else:
        raise ValueError("OpenAI API 키가 필요합니다.")
    
    # 오디오 파일 정보
    with wave.open(str(audio_path), 'rb') as wf:
        duration = wf.getnframes() / wf.getframerate()
    
    # 무음 체크
    is_silent, rms = check_audio_for_silence(audio_path, silence_threshold)
    
    if skip_silent and is_silent:
        logger.info(f"무음 파일 건너뜀: {audio_path.name} (RMS: {rms:.2f})")
        return TranscriptionResult(
            text="",
            file_path=audio_path,
            duration=duration,
            is_silent=True,
            rms_level=rms,
        )
    
    # Whisper API 호출
    with open(audio_path, "rb") as audio_file:
        kwargs = {"model": config.model, "file": audio_file}
        
        if config.language:
            kwargs["language"] = config.language
        if config.prompt:
            kwargs["prompt"] = config.prompt
        if config.temperature > 0:
            kwargs["temperature"] = config.temperature
        
        client = openai.OpenAI()
        transcription = client.audio.transcriptions.create(**kwargs)
    
    logger.info(f"전사 완료: {audio_path.name} ({duration:.1f}초)")
    
    return TranscriptionResult(
        text=transcription.text,
        file_path=audio_path,
        duration=duration,
        is_silent=False,
        rms_level=rms,
    )


def transcribe_directory(
    directory: Union[str, Path],
    output_json: Optional[Union[str, Path]] = None,
    config: Optional[WhisperConfig] = None,
    api_key: Optional[str] = None,
    skip_silent: bool = True,
) -> list[TranscriptionResult]:
    """디렉토리 내 모든 WAV 파일을 전사합니다.
    
    Args:
        directory: WAV 파일이 있는 디렉토리
        output_json: 결과를 저장할 JSON 파일 경로
        config: Whisper 설정
        api_key: OpenAI API 키
        skip_silent: 무음 파일 건너뛰기
    
    Returns:
        TranscriptionResult 리스트
    """
    directory = Path(directory)
    
    # WAV 파일 찾기 및 숫자 기준 정렬
    wav_files = list(directory.glob("*.wav"))
    
    def extract_number(path: Path) -> int:
        match = re.search(r'(\d+)', path.stem)
        return int(match.group(1)) if match else 999999
    
    wav_files.sort(key=extract_number)
    
    logger.info(f"총 {len(wav_files)}개의 WAV 파일 발견")
    
    results = []
    for wav_file in wav_files:
        try:
            result = transcribe_audio(
                wav_file,
                config=config,
                api_key=api_key,
                skip_silent=skip_silent,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"전사 실패: {wav_file.name} - {e}")
    
    # JSON 저장
    if output_json:
        output_json = Path(output_json)
        data = [
            {
                "file": r.file_path.name if r.file_path else "",
                "text": r.text,
                "duration": r.duration,
                "is_silent": r.is_silent,
                "rms_level": r.rms_level,
            }
            for r in results
        ]
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"결과 저장: {output_json}")
    
    return results


def prepare_audio_for_whisper(
    audio_data: np.ndarray,
    original_sample_rate: int,
    target_sample_rate: int = 16000,
) -> np.ndarray:
    """오디오 데이터를 Whisper에 최적화된 형식으로 변환합니다.
    
    Args:
        audio_data: 원본 오디오 데이터
        original_sample_rate: 원본 샘플 레이트
        target_sample_rate: 목표 샘플 레이트 (기본 16000)
    
    Returns:
        리샘플링된 오디오 데이터
    """
    from scipy import signal
    
    if original_sample_rate == target_sample_rate:
        return audio_data
    
    # 리샘플링
    num_samples = int(len(audio_data) * target_sample_rate / original_sample_rate)
    resampled = signal.resample(audio_data, num_samples)
    
    return resampled.astype(audio_data.dtype)
