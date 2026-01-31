"""VoiceLink 로깅 설정 모듈."""

import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """VoiceLink 로깅을 설정합니다.
    
    Args:
        level: 로깅 레벨 (기본 INFO)
        log_file: 로그 파일 경로 (None이면 파일 로깅 안함)
        format_string: 로그 포맷 문자열
    
    Returns:
        설정된 logger 객체
    """
    if format_string is None:
        format_string = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    
    # 루트 voicelink 로거 가져오기
    logger = logging.getLogger('voicelink')
    logger.setLevel(level)
    
    # 기존 핸들러 제거
    logger.handlers.clear()
    
    # 포매터 생성
    formatter = logging.Formatter(format_string)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (옵션)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_logger(name: str = 'voicelink') -> logging.Logger:
    """VoiceLink 로거를 가져옵니다.
    
    Args:
        name: 로거 이름 (서브모듈용)
    
    Returns:
        Logger 객체
    """
    if not name.startswith('voicelink'):
        name = f'voicelink.{name}'
    return logging.getLogger(name)


# 기본 로거 (모듈 레벨에서 바로 사용 가능)
log = get_logger()
