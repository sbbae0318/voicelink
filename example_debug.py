"""VoiceLink 디버그 스크립트 - 오디오 캡처 문제 진단용"""

import logging
import sys
import time
from pathlib import Path

import numpy as np
import sounddevice as sd

# 로깅 설정 - DEBUG 레벨로 상세 로그 출력
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('voicelink_debug.log', encoding='utf-8')
    ]
)

logger = logging.getLogger('voicelink_debug')

def debug_separator(title: str):
    """디버그 섹션 구분선 출력"""
    logger.info("=" * 60)
    logger.info(f"  {title}")
    logger.info("=" * 60)

def check_system_audio():
    """시스템 오디오 상태 확인"""
    debug_separator("1. 시스템 오디오 상태 확인")
    
    # sounddevice 기본 정보
    logger.info(f"sounddevice 버전: {sd.__version__}")
    logger.info(f"PortAudio 버전: {sd.get_portaudio_version()}")
    
    # 기본 장치 확인
    default_input, default_output = sd.default.device
    logger.info(f"기본 입력 장치 인덱스: {default_input}")
    logger.info(f"기본 출력 장치 인덱스: {default_output}")
    
    if default_input is not None:
        try:
            default_input_info = sd.query_devices(default_input)
            logger.info(f"기본 입력 장치: {default_input_info['name']}")
        except Exception as e:
            logger.error(f"기본 입력 장치 조회 실패: {e}")
    
    return default_input, default_output

def list_all_devices():
    """모든 오디오 장치 나열"""
    debug_separator("2. 모든 오디오 장치 나열")
    
    devices = sd.query_devices()
    logger.info(f"총 장치 수: {len(devices)}")
    
    # 입력 가능한 장치만 필터링
    input_devices = []
    virtual_devices = []
    loopback_devices = []
    
    for idx, device in enumerate(devices):
        if device['max_input_channels'] > 0:
            input_devices.append((idx, device))
            name_lower = device['name'].lower()
            
            # Virtual 장치 확인
            if any(v in name_lower for v in ['virtual', 'cable', 'vb-audio', 'blackhole', 'loopback']):
                virtual_devices.append((idx, device))
                
            # Loopback 확인 (Windows CABLE Output)
            if 'cable output' in name_lower:
                loopback_devices.append((idx, device))
    
    logger.info(f"\n입력 가능 장치 ({len(input_devices)}개):")
    for idx, dev in input_devices:
        logger.info(f"  [{idx:3d}] {dev['name']} (채널: {dev['max_input_channels']}, SR: {dev['default_samplerate']})")
    
    logger.info(f"\n가상 오디오 장치 ({len(virtual_devices)}개):")
    for idx, dev in virtual_devices:
        logger.info(f"  [{idx:3d}] {dev['name']}")
    
    logger.info(f"\nLoopback 장치 ({len(loopback_devices)}개):")
    for idx, dev in loopback_devices:
        logger.info(f"  [{idx:3d}] {dev['name']}")
    
    return loopback_devices

def check_voicelink_device_selection():
    """VoiceLink 장치 선택 로직 확인"""
    debug_separator("3. VoiceLink 장치 선택 로직 분석")
    
    from voicelink.devices import (
        _is_loopback_device,
        _is_virtual_device,
        find_best_loopback_device,
        list_devices,
        list_loopback_devices,
    )
    from voicelink.platform_utils import Platform, get_platform
    
    platform = get_platform()
    logger.info(f"현재 플랫폼: {platform.value}")
    
    # VoiceLink가 인식하는 loopback 장치
    loopback_devs = list_loopback_devices()
    logger.info(f"\nVoiceLink가 인식한 loopback/virtual 장치 ({len(loopback_devs)}개):")
    for dev in loopback_devs:
        logger.info(f"  [{dev.index:3d}] {dev.name}")
        logger.info(f"       is_input={dev.is_input}, is_loopback={dev.is_loopback}, is_virtual={dev.is_virtual}, can_capture={dev.can_capture}")
    
    # 최적 장치 선택
    best_device = find_best_loopback_device()
    if best_device:
        logger.info(f"\n✅ 선택된 최적 장치: [{best_device.index}] {best_device.name}")
        logger.info(f"   is_input={best_device.is_input}, is_loopback={best_device.is_loopback}")
    else:
        logger.warning("\n❌ 최적 장치를 찾을 수 없음!")
    
    # Windows에서 CABLE Output 검색 로직 분석
    if platform == Platform.WINDOWS:
        logger.info("\n[Windows 장치 선택 로직 분석]")
        all_devs = list_devices()
        for dev in all_devs:
            name_lower = dev.name.lower()
            if 'cable' in name_lower:
                is_cable_output = "cable output" in name_lower
                logger.info(f"  CABLE 장치: [{dev.index}] {dev.name}")
                logger.info(f"    'cable output' 매칭: {is_cable_output}")
                logger.info(f"    is_input: {dev.is_input}")
                logger.info(f"    조건 충족 (cable output + is_input): {is_cable_output and dev.is_input}")
    
    return best_device

def test_audio_capture(device_index: int, duration: float = 3.0):
    """특정 장치에서 오디오 캡처 테스트"""
    debug_separator(f"4. 오디오 캡처 테스트 (장치: {device_index}, {duration}초)")
    
    sample_rate = 44100
    channels = 2
    audio_data = []
    callback_count = 0
    total_samples = 0
    
    def audio_callback(indata, frames, time_info, status):
        nonlocal callback_count, total_samples
        callback_count += 1
        total_samples += frames
        
        # 오디오 레벨 계산
        rms = np.sqrt(np.mean(indata**2))
        peak = np.max(np.abs(indata))
        
        # 처음 5번과 이후 50번마다 로그
        if callback_count <= 5 or callback_count % 50 == 0:
            logger.debug(f"Callback #{callback_count}: frames={frames}, RMS={rms:.6f}, Peak={peak:.6f}, status={status}")
        
        audio_data.append(indata.copy())
    
    try:
        device_info = sd.query_devices(device_index)
        logger.info(f"테스트 장치: {device_info['name']}")
        logger.info(f"  max_input_channels: {device_info['max_input_channels']}")
        logger.info(f"  default_samplerate: {device_info['default_samplerate']}")
        
        logger.info(f"\n캡처 시작... ({duration}초)")
        
        with sd.InputStream(
            device=device_index,
            samplerate=sample_rate,
            channels=min(channels, device_info['max_input_channels']),
            dtype='float32',
            callback=audio_callback
        ):
            time.sleep(duration)
        
        logger.info(f"\n캡처 완료!")
        logger.info(f"  총 콜백 횟수: {callback_count}")
        logger.info(f"  총 샘플 수: {total_samples}")
        logger.info(f"  예상 샘플 수: {int(sample_rate * duration)}")
        
        if audio_data:
            combined = np.concatenate(audio_data, axis=0)
            overall_rms = np.sqrt(np.mean(combined**2))
            overall_peak = np.max(np.abs(combined))
            
            logger.info(f"\n[오디오 분석 결과]")
            logger.info(f"  총 데이터 shape: {combined.shape}")
            logger.info(f"  전체 RMS 레벨: {overall_rms:.6f}")
            logger.info(f"  전체 Peak 레벨: {overall_peak:.6f}")
            
            # 무음 판정
            if overall_rms < 0.0001:
                logger.warning("⚠️ 거의 무음 상태입니다! (RMS < 0.0001)")
                logger.warning("   → 시스템 오디오가 CABLE Input으로 라우팅되고 있는지 확인하세요.")
                logger.warning("   → Windows 사운드 설정에서 기본 출력 장치를 'CABLE Input'으로 변경해보세요.")
            elif overall_rms < 0.001:
                logger.warning("⚠️ 매우 낮은 오디오 레벨입니다. (RMS < 0.001)")
            else:
                logger.info("✅ 오디오 신호가 감지되었습니다!")
            
            return combined, overall_rms, overall_peak
        else:
            logger.error("❌ 오디오 데이터가 수집되지 않았습니다!")
            return None, 0, 0
            
    except Exception as e:
        logger.error(f"❌ 캡처 실패: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None, 0, 0

def test_voicelink_recording(duration: float = 5.0):
    """VoiceLink 녹음 기능 테스트"""
    debug_separator(f"5. VoiceLink 녹음 테스트 ({duration}초)")
    
    from voicelink import VoiceLink
    from voicelink.capture import AudioCapture, CaptureConfig
    from voicelink.recorder import record_audio
    
    output_path = Path("debug_output.wav")
    
    # capture 모듈 직접 테스트
    logger.info("\n[AudioCapture 직접 테스트]")
    
    config = CaptureConfig(
        device=None,  # 자동 감지
        sample_rate=44100,
        channels=2,
    )
    
    capture = AudioCapture(config)
    
    # 장치 해결 과정 로깅
    resolved_device = capture._resolve_device()
    if resolved_device:
        logger.info(f"해결된 장치: [{resolved_device.index}] {resolved_device.name}")
    else:
        logger.warning("장치 해결 실패 - 기본 입력 장치 사용 예정")
    
    audio_chunks = []
    chunk_count = 0
    
    def debug_callback(data):
        nonlocal chunk_count
        chunk_count += 1
        rms = np.sqrt(np.mean(data**2))
        if chunk_count <= 3 or chunk_count % 20 == 0:
            logger.debug(f"Chunk #{chunk_count}: shape={data.shape}, RMS={rms:.6f}")
        audio_chunks.append(data)
    
    capture.add_callback(debug_callback)
    
    logger.info("캡처 시작...")
    success = capture.start()
    
    if not success:
        logger.error(f"❌ 캡처 시작 실패: {capture.state.error}")
        return
    
    logger.info(f"캡처 중... (is_capturing={capture.is_capturing})")
    time.sleep(duration)
    
    capture.stop()
    logger.info(f"캡처 종료 - 총 {chunk_count}개 청크 수집")
    
    if audio_chunks:
        combined = np.concatenate(audio_chunks, axis=0)
        rms = np.sqrt(np.mean(combined**2))
        peak = np.max(np.abs(combined))
        
        logger.info(f"\n[녹음 결과]")
        logger.info(f"  데이터 shape: {combined.shape}")
        logger.info(f"  RMS: {rms:.6f}")
        logger.info(f"  Peak: {peak:.6f}")
        
        # WAV 파일로 저장
        from scipy.io import wavfile
        audio_int16 = (combined * 32767).astype(np.int16)
        wavfile.write(str(output_path), 44100, audio_int16)
        logger.info(f"  저장됨: {output_path.absolute()}")
        
        # 파일 크기 확인
        file_size = output_path.stat().st_size
        logger.info(f"  파일 크기: {file_size:,} bytes")
        
        if rms < 0.0001:
            logger.warning("\n⚠️ 녹음된 오디오가 무음입니다!")
    else:
        logger.error("❌ 오디오 청크가 수집되지 않았습니다!")

def main():
    """메인 디버그 실행"""
    print("\n" + "=" * 60)
    print("  VoiceLink 디버그 모드")
    print("=" * 60 + "\n")
    
    # 1. 시스템 상태 확인
    default_input, default_output = check_system_audio()
    
    # 2. 모든 장치 나열
    loopback_devices = list_all_devices()
    
    # 3. VoiceLink 장치 선택 로직
    best_device = check_voicelink_device_selection()
    
    # 4. 직접 오디오 캡처 테스트
    if best_device:
        audio_data, rms, peak = test_audio_capture(best_device.index, duration=3.0)
    elif loopback_devices:
        # fallback으로 첫 번째 loopback 장치 사용
        device_idx = loopback_devices[0][0]
        logger.info(f"\nFallback 장치 사용: {loopback_devices[0][1]['name']}")
        audio_data, rms, peak = test_audio_capture(device_idx, duration=3.0)
    else:
        logger.warning("테스트할 loopback 장치가 없습니다!")
        audio_data = None
    
    # 5. VoiceLink 녹음 테스트
    test_voicelink_recording(duration=5.0)
    
    # 결과 요약
    debug_separator("📋 디버그 결과 요약")
    
    logger.info(f"기본 입력 장치: {default_input}")
    logger.info(f"선택된 캡처 장치: {best_device.name if best_device else 'None'}")
    
    if audio_data is not None:
        if rms < 0.0001:
            logger.warning("\n🔴 문제 발견: 오디오가 무음입니다!")
            logger.info("\n[해결 방법]")
            logger.info("1. Windows 사운드 설정 열기 (작업표시줄 스피커 아이콘 우클릭 → 소리 설정)")
            logger.info("2. '출력' 섹션에서 'CABLE Input (VB-Audio Virtual Cable)' 선택")
            logger.info("3. 또는 Voicemeeter를 사용하여 오디오를 CABLE로 라우팅")
            logger.info("4. 테스트: YouTube나 음악 재생 후 다시 스크립트 실행")
        else:
            logger.info("\n🟢 오디오 캡처가 정상 작동합니다!")
    
    logger.info(f"\n상세 로그: voicelink_debug.log")
    logger.info("디버그 출력 파일: debug_output.wav")

if __name__ == "__main__":
    main()
