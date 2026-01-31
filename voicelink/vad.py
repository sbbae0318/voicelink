"""Voice Activity Detection (VAD) 모듈.

webrtcvad를 사용하여 음성 구간만 추출하는 기능을 제공합니다.
Listener 프로젝트의 vad_processor.py에서 영감을 받아 개선된 버전입니다.
"""

import collections
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Generator, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class AudioFrame:
    """오디오 프레임을 나타내는 클래스."""
    
    data: bytes
    timestamp: float
    duration: float


@dataclass
class VADConfig:
    """VAD 설정."""
    
    aggressiveness: int = 3  # 0-3, 높을수록 더 공격적으로 무음 판정
    frame_duration_ms: int = 30  # 프레임 길이 (10, 20, 30 ms)
    padding_duration_ms: int = 300  # 음성 세그먼트 패딩
    sample_rate: int = 16000  # 8000, 16000, 32000, 48000 Hz만 지원


def is_silent(
    audio_data: Union[bytes, np.ndarray],
    threshold: float = 0.001,
    sample_width: int = 2,
) -> tuple[bool, float]:
    """오디오 데이터가 무음인지 판별합니다.
    
    Args:
        audio_data: 오디오 데이터 (bytes 또는 numpy array)
        threshold: RMS 임계값 (float32 기준) 또는 500 (int16 기준)
        sample_width: 샘플 너비 (2=16bit, 4=32bit)
    
    Returns:
        (is_silent, rms_value) 튜플
    """
    if isinstance(audio_data, bytes):
        if sample_width == 2:
            audio = np.frombuffer(audio_data, dtype=np.int16)
            rms = np.sqrt(np.mean(audio.astype(np.float32) ** 2))
            # int16 기준 임계값 조정
            return rms < (threshold * 32767 if threshold < 1 else threshold), rms
        else:
            audio = np.frombuffer(audio_data, dtype=np.float32)
    else:
        audio = audio_data
    
    rms = float(np.sqrt(np.mean(audio ** 2)))
    return rms < threshold, rms


def generate_frames(
    audio_data: bytes,
    sample_rate: int,
    frame_duration_ms: int = 30,
) -> Generator[AudioFrame, None, None]:
    """오디오 데이터를 프레임 단위로 분할합니다.
    
    Args:
        audio_data: PCM 오디오 데이터 (16비트)
        sample_rate: 샘플 레이트
        frame_duration_ms: 프레임 길이 (밀리초)
    
    Yields:
        AudioFrame 객체
    """
    # 16비트 = 2바이트
    bytes_per_sample = 2
    frame_size = int(sample_rate * (frame_duration_ms / 1000.0) * bytes_per_sample)
    
    offset = 0
    timestamp = 0.0
    duration = frame_duration_ms / 1000.0
    
    while offset + frame_size <= len(audio_data):
        yield AudioFrame(
            data=audio_data[offset:offset + frame_size],
            timestamp=timestamp,
            duration=duration,
        )
        timestamp += duration
        offset += frame_size


def extract_voice_segments(
    audio_data: bytes,
    sample_rate: int = 16000,
    config: Optional[VADConfig] = None,
) -> Generator[bytes, None, None]:
    """VAD를 사용하여 음성 구간만 추출합니다.
    
    Args:
        audio_data: PCM 오디오 데이터 (16비트 모노)
        sample_rate: 샘플 레이트 (8000, 16000, 32000, 48000 Hz)
        config: VAD 설정
    
    Yields:
        음성 구간의 오디오 데이터
    """
    try:
        import webrtcvad
    except ImportError:
        raise ImportError(
            "VAD 기능을 사용하려면 webrtcvad를 설치하세요: pip install webrtcvad"
        )
    
    if config is None:
        config = VADConfig(sample_rate=sample_rate)
    
    if sample_rate not in (8000, 16000, 32000, 48000):
        raise ValueError(f"지원하지 않는 샘플 레이트: {sample_rate}. "
                        "8000, 16000, 32000, 48000 Hz만 지원합니다.")
    
    vad = webrtcvad.Vad(config.aggressiveness)
    frames = list(generate_frames(audio_data, sample_rate, config.frame_duration_ms))
    
    num_padding_frames = int(config.padding_duration_ms / config.frame_duration_ms)
    ring_buffer = collections.deque(maxlen=num_padding_frames)
    triggered = False
    voiced_frames = []
    
    for frame in frames:
        is_speech = vad.is_speech(frame.data, sample_rate)
        
        if not triggered:
            ring_buffer.append((frame, is_speech))
            num_voiced = len([f for f, speech in ring_buffer if speech])
            
            if num_voiced > 0.9 * ring_buffer.maxlen:
                triggered = True
                voiced_frames.extend([f for f, _ in ring_buffer])
                ring_buffer.clear()
        else:
            voiced_frames.append(frame)
            ring_buffer.append((frame, is_speech))
            num_unvoiced = len([f for f, speech in ring_buffer if not speech])
            
            if num_unvoiced > 0.9 * ring_buffer.maxlen:
                triggered = False
                yield b"".join([f.data for f in voiced_frames])
                ring_buffer.clear()
                voiced_frames = []
    
    if voiced_frames:
        yield b"".join([f.data for f in voiced_frames])


def remove_silence(
    audio_data: bytes,
    sample_rate: int = 16000,
    config: Optional[VADConfig] = None,
) -> bytes:
    """오디오에서 무음 구간을 제거합니다.
    
    Args:
        audio_data: PCM 오디오 데이터 (16비트 모노)
        sample_rate: 샘플 레이트
        config: VAD 설정
    
    Returns:
        무음이 제거된 오디오 데이터
    """
    segments = list(extract_voice_segments(audio_data, sample_rate, config))
    return b"".join(segments)


def process_wav_file(
    input_path: Union[str, Path],
    output_path: Optional[Union[str, Path]] = None,
    config: Optional[VADConfig] = None,
) -> Path:
    """WAV 파일에서 무음을 제거합니다.
    
    Args:
        input_path: 입력 WAV 파일 경로
        output_path: 출력 WAV 파일 경로 (None이면 자동 생성)
        config: VAD 설정
    
    Returns:
        출력 파일 경로
    """
    import wave
    
    input_path = Path(input_path)
    
    if output_path is None:
        output_path = input_path.with_stem(f"{input_path.stem}_vad")
    else:
        output_path = Path(output_path)
    
    # WAV 파일 읽기
    with wave.open(str(input_path), 'rb') as wf:
        if wf.getnchannels() != 1:
            raise ValueError("모노 오디오 파일만 지원합니다.")
        if wf.getsampwidth() != 2:
            raise ValueError("16비트 PCM 파일만 지원합니다.")
        
        sample_rate = wf.getframerate()
        audio_data = wf.readframes(wf.getnframes())
    
    # VAD 처리
    processed_audio = remove_silence(audio_data, sample_rate, config)
    
    # 결과 저장
    with wave.open(str(output_path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(processed_audio)
    
    original_duration = len(audio_data) / (sample_rate * 2)
    processed_duration = len(processed_audio) / (sample_rate * 2)
    reduction = (1 - processed_duration / original_duration) * 100 if original_duration > 0 else 0
    
    logger.info(f"VAD 처리 완료: {input_path.name}")
    logger.info(f"  원본: {original_duration:.1f}초 → 처리 후: {processed_duration:.1f}초 ({reduction:.1f}% 감소)")
    
    return output_path
