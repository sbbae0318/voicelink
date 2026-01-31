"""자동 오디오 장치 탐지 모듈.

모든 입력 장치를 스캔하여 실제로 오디오 신호가 있는 장치를 자동으로 찾습니다.
"""

import logging
import time
from dataclasses import dataclass
from typing import Optional

import numpy as np
import sounddevice as sd

from .devices import AudioDevice, list_devices

logger = logging.getLogger(__name__)


@dataclass
class DeviceProbeResult:
    """장치 프로브 결과."""
    
    device: AudioDevice
    rms_level: float
    peak_level: float
    has_signal: bool
    error: Optional[str] = None


def probe_device(
    device_index: int,
    duration: float = 0.5,
    sample_rate: int = 44100,
    threshold: float = 0.001,
) -> Optional[DeviceProbeResult]:
    """단일 장치에서 오디오 신호를 프로브합니다.
    
    Args:
        device_index: 장치 인덱스
        duration: 프로브 시간 (초)
        sample_rate: 샘플링 레이트
        threshold: 신호 감지 임계값 (RMS)
    
    Returns:
        DeviceProbeResult 또는 오류 시 None
    """
    from .devices import get_device_by_index
    
    device = get_device_by_index(device_index)
    if not device or not device.can_capture:
        return None
    
    audio_data = []
    
    def callback(indata, frames, time_info, status):
        audio_data.append(indata.copy())
    
    try:
        # 장치 정보 조회
        device_info = sd.query_devices(device_index)
        channels = min(2, device_info['max_input_channels'])
        
        if channels <= 0:
            return None
        
        # 짧은 시간 동안 오디오 캡처
        with sd.InputStream(
            device=device_index,
            samplerate=sample_rate,
            channels=channels,
            dtype='float32',
            callback=callback,
            blocksize=1024,
        ):
            time.sleep(duration)
        
        if not audio_data:
            return DeviceProbeResult(
                device=device,
                rms_level=0.0,
                peak_level=0.0,
                has_signal=False,
                error="No data captured"
            )
        
        # 오디오 레벨 분석
        combined = np.concatenate(audio_data, axis=0)
        rms = float(np.sqrt(np.mean(combined**2)))
        peak = float(np.max(np.abs(combined)))
        
        return DeviceProbeResult(
            device=device,
            rms_level=rms,
            peak_level=peak,
            has_signal=rms > threshold,
        )
        
    except Exception as e:
        logger.debug(f"장치 {device_index} 프로브 실패: {e}")
        return DeviceProbeResult(
            device=device,
            rms_level=0.0,
            peak_level=0.0,
            has_signal=False,
            error=str(e)
        )


def find_active_audio_device(
    probe_duration: float = 0.5,
    threshold: float = 0.001,
    prefer_virtual: bool = True,
    exclude_keywords: Optional[list[str]] = None,
    verbose: bool = True,
) -> Optional[AudioDevice]:
    """실제로 오디오 신호가 있는 장치를 자동으로 찾습니다.
    
    모든 입력 가능한 장치를 스캔하여 가장 높은 오디오 레벨을 가진
    장치를 반환합니다.
    
    Args:
        probe_duration: 각 장치 프로브 시간 (초)
        threshold: 신호 감지 임계값 (RMS)
        prefer_virtual: 가상 장치 우선 여부
        verbose: 상세 출력 여부
    
    Returns:
        신호가 있는 최적의 AudioDevice, 없으면 None
    """
    all_devices = list_devices()
    
    # 입력 가능한 장치만 필터링
    input_devices = [d for d in all_devices if d.can_capture]
    
    # 키워드 기반 제외
    if exclude_keywords:
        filtered = []
        for d in input_devices:
            name_lower = d.name.lower()
            if any(k in name_lower for k in exclude_keywords):
                continue
            filtered.append(d)
        input_devices = filtered
    
    if verbose:
        print(f"\n🔍 오디오 장치 자동 탐지 시작... ({len(input_devices)}개 장치)")
        print("-" * 50)
    
    # 가상 장치를 먼저 스캔 (보통 더 유용함)
    if prefer_virtual:
        virtual_devices = [d for d in input_devices if d.is_virtual or d.is_loopback]
        other_devices = [d for d in input_devices if not d.is_virtual and not d.is_loopback]
        scan_order = virtual_devices + other_devices
    else:
        scan_order = input_devices
    
    results: list[DeviceProbeResult] = []
    
    for device in scan_order:
        if verbose:
            print(f"  [{device.index:3d}] {device.name[:40]:<40}", end=" ", flush=True)
        
        result = probe_device(
            device.index,
            duration=probe_duration,
            threshold=threshold,
        )
        
        if result:
            results.append(result)
            
            if verbose:
                if result.error:
                    print(f"❌ 오류")
                elif result.has_signal:
                    print(f"🟢 RMS: {result.rms_level:.6f}")
                else:
                    print(f"⚪ 무음 (RMS: {result.rms_level:.6f})")
        else:
            if verbose:
                print(f"⏭️ 스킵")
    
    if verbose:
        print("-" * 50)
    
    # 신호가 있는 장치 중 가장 높은 레벨 선택
    active_results = [r for r in results if r.has_signal]
    
    if active_results:
        # RMS 레벨이 가장 높은 장치 선택
        best = max(active_results, key=lambda r: r.rms_level)
        
        if verbose:
            print(f"\n✅ 활성 장치 발견: [{best.device.index}] {best.device.name}")
            print(f"   RMS: {best.rms_level:.6f}, Peak: {best.peak_level:.6f}")
        
        # 레코더에서 참조할 수 있도 속성 추가
        best.device.rms_level = best.rms_level
        return best.device
    
    if verbose:
        print("\n⚠️ 활성 오디오 장치를 찾을 수 없습니다.")
        print("   → 오디오를 재생하고 다시 시도해주세요.")
    
    return None


def auto_select_capture_device(
    fallback_to_default: bool = True,
    verbose: bool = True,
) -> Optional[AudioDevice]:
    """캡처용 장치를 자동으로 선택합니다.
    
    1. 먼저 활성 오디오가 있는 장치를 찾습니다.
    2. 없으면 기존 loopback 장치 선택 로직을 사용합니다.
    3. 그래도 없으면 기본 입력 장치를 반환합니다.
    
    Args:
        fallback_to_default: 실패 시 기본 장치 사용 여부
        verbose: 상세 출력 여부
    
    Returns:
        선택된 AudioDevice 또는 None
    """
    from .devices import find_best_loopback_device, get_default_input_device
    
    # 1. 활성 오디오 장치 찾기
    active_device = find_active_audio_device(
        probe_duration=0.3,
        threshold=0.0005,
        prefer_virtual=True,
        exclude_keywords=["microphone", "mic", "마이크", "webcam"],  # 마이크 제외
        verbose=verbose,
    )
    
    if active_device:
        return active_device
    
    # 2. 기존 loopback 선택 로직
    if verbose:
        print("\n🔄 기존 loopback 장치 선택 로직 사용...")
    
    loopback_device = find_best_loopback_device()
    if loopback_device:
        if verbose:
            print(f"   선택됨: [{loopback_device.index}] {loopback_device.name}")
        return loopback_device
    
    # 3. 기본 입력 장치
    if fallback_to_default:
        if verbose:
            print("\n🔄 기본 입력 장치 사용...")
        
        default_device = get_default_input_device()
        if default_device:
            if verbose:
                print(f"   선택됨: [{default_device.index}] {default_device.name}")
            return default_device
    
    return None
