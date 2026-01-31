"""자동 장치 전환 테스트 스크립트."""

import logging
import threading
import time
from unittest.mock import MagicMock, patch

from voicelink.chunked_recorder import ChunkedRecorder
from voicelink.config import VoiceLinkConfig
from voicelink.logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

def test_auto_switch():
    logger.info("테스트 시작: 자동 장치 전환")
    
    # 설정: 5초 무음 후 전환 시도
    config = VoiceLinkConfig()
    config.device.auto_switch = True
    config.device.silence_timeout_for_switch = 2.0  # 테스트를 위해 2초로 단축
    
    # 레코더 초기화
    recorder = ChunkedRecorder(config=config)
    
    # 이벤트 감지용 이벤트 객체
    switch_event = threading.Event()
    
    def on_device_changed(idx, name):
        logger.info(f"✅ 콜백 수신: 장치가 {idx} ({name}) 로 변경됨")
        switch_event.set()
        
    recorder.on_device_changed(on_device_changed)
    
    # 1. 녹음 시작 (가짜 장치로 가정)
    logger.info("1. 녹음 시작...")
    if not recorder.start():
        logger.error("녹음 시작 실패")
        return

    # 2. 강제로 무음 상태 유지 (실제 소리가 안 나면 무음일 것임)
    logger.info("2. 3초간 대기 (무음 상태)...")
    time.sleep(3.0)
    
    # 3. auto_detect.find_active_audio_device 모의 (Mock)
    logger.info("3. 다른 장치에서 소리가 감지된 상황 시뮬레이션...")
    
    # MagicMock을 사용하여 AudioDevice 객체를 흉내냅니다.
    mock_device = MagicMock()
    mock_device.index = 999
    mock_device.name = "Mock Active Device"
    mock_device.max_input_channels = 2
    mock_device.is_loopback = False
    mock_device.rms_level = 0.5  # 아주 큰 소리
    mock_device.has_signal = True
    
    # switch_device 내부의 sd.InputStream도 모의해야 에러가 안 남
    with patch("voicelink.auto_detect.find_active_audio_device", return_value=mock_device), \
         patch("sounddevice.InputStream"), \
         patch("sounddevice.query_devices", return_value={'name': "Mock Active Device"}):
        
        # 강제로 스캔 트리거 (시간 체크 우회)
        recorder._last_device_scan_time = 0 
        recorder._check_alternative_devices()
        
        # 스레드 실행 대기
        time.sleep(1.0)
        
    # 4. 장치 변경 확인
    if switch_event.is_set():
        logger.info("✅ 성공: 장치 변경 이벤트가 감지되었습니다.")
    else:
        logger.error("❌ 실패: 장치 변경 이벤트가 발생하지 않았습니다.")
    
    recorder.stop()
    logger.info("테스트 종료")

if __name__ == "__main__":
    test_auto_switch()
