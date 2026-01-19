# VoiceLink Architecture

## Overview

VoiceLink is a cross-platform Python tool for capturing system audio and generating technical glossaries. It's designed to work both as a standalone Python library and as a Claude Skill.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        VoiceLink                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │     CLI      │  │  Python API  │  │    Claude Skills     │  │
│  │   (click)    │  │  (VoiceLink) │  │   (skill_* methods)  │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘  │
│         │                 │                      │              │
│         └─────────────────┼──────────────────────┘              │
│                           │                                     │
│  ┌────────────────────────┴────────────────────────────────┐   │
│  │                    Core Modules                          │   │
│  ├──────────────┬───────────────┬───────────────┬──────────┤   │
│  │   capture    │   recorder    │    stream     │ glossary │   │
│  │              │               │               │          │   │
│  │ AudioCapture │ AudioRecorder │ OpenAIStream  │ DSPy     │   │
│  └──────┬───────┴───────┬───────┴───────┬───────┴────┬─────┘   │
│         │               │               │            │          │
│  ┌──────┴───────────────┴───────────────┴────────────┘         │
│  │                  Support Modules                             │
│  ├──────────────┬───────────────┬───────────────────────────┐  │
│  │   devices    │ platform_utils│      virtual_mic          │  │
│  └──────────────┴───────────────┴───────────────────────────┘  │
│                           │                                     │
└───────────────────────────┼─────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│                     External Dependencies                        │
├───────────────────────────┼─────────────────────────────────────┤
│  sounddevice (PortAudio)  │  OpenAI API  │  DSPy Framework     │
│  numpy/scipy              │  websockets  │  Whisper API        │
└───────────────────────────┴──────────────┴─────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────┐
│                     Platform Audio Layer                         │
├───────────────────────────┼─────────────────────────────────────┤
│  macOS: BlackHole/CoreAudio                                     │
│  Windows: VB-CABLE/WASAPI                                       │
│  Linux: PulseAudio Monitor                                      │
└─────────────────────────────────────────────────────────────────┘
```

## Module Descriptions

### Core Modules

#### `capture.py`

The audio capture engine using sounddevice.

```python
class AudioCapture:
    """Main capture class with callback support."""
    - start() -> bool
    - stop() -> None
    - add_callback(fn) -> None
    - get_audio_data() -> np.ndarray
```

- Uses sounddevice InputStream for low-latency capture
- Thread-safe callback system for real-time processing
- Queue-based buffering for async consumption
- Configurable sample rate, channels, and buffer size

#### `recorder.py`

File recording with WAV and MP3 support.

```python
class AudioRecorder:
    """Records audio to file."""
    - start() -> bool
    - stop() -> None
    - wait() -> None
```

- Wraps AudioCapture for file output
- WAV via scipy.io.wavfile
- MP3 via pydub (optional dependency)
- Thread-based duration management

#### `stream.py`

OpenAI Realtime API integration.

```python
class OpenAIRealtimeStream:
    """WebSocket streaming to OpenAI."""
    - start() -> bool
    - stop() -> None
    - commit_audio() -> None
    - create_response() -> None
```

- WebSocket connection management
- Audio buffering and base64 encoding
- Event handling for transcriptions and responses
- Async architecture with thread synchronization

#### `glossary/`

DSPy-powered glossary generation.

```
glossary/
├── __init__.py        # Module exports
├── transcriber.py     # Whisper API transcription
├── extractor.py       # DSPy term extraction
└── generator.py       # GlossaryGenerator class
```

**DSPy Pipeline:**
```
Audio File
    │
    ▼
┌─────────────┐
│ Transcriber │ (Whisper API)
└──────┬──────┘
       │ transcript
       ▼
┌─────────────┐
│ TermExtractor│ (DSPy ChainOfThought)
└──────┬──────┘
       │ terms[]
       ▼
┌─────────────┐
│TermExplainer│ (DSPy ChainOfThought)
└──────┬──────┘
       │ explanations[]
       ▼
┌─────────────────┐
│ GlossaryDocument│
└─────────────────┘
```

### Support Modules

#### `devices.py`

Audio device enumeration and selection.

```python
class AudioDevice:
    """Represents an audio device."""
    - index: int
    - name: str
    - is_input: bool
    - is_output: bool
    - is_loopback: bool
    - is_virtual: bool
```

Functions:
- `list_devices()` - All devices
- `list_loopback_devices()` - Virtual/loopback only
- `find_best_loopback_device()` - Auto-selection

#### `platform_utils.py`

Platform detection and driver management.

```python
class DriverStatus:
    """Virtual audio driver status."""
    - installed: bool
    - driver_name: str
    - device_name: str
    - install_instructions: str
```

Functions:
- `get_platform()` - Detect OS
- `check_blackhole_installed()` - macOS
- `check_vbcable_installed()` - Windows
- `check_pulseaudio_monitor()` - Linux
- `setup_driver()` - Installation helper

#### `virtual_mic.py`

Virtual microphone routing.

```python
class VirtualMicRouter:
    """Route audio between devices."""
    - start() -> bool
    - stop() -> None
```

Functions:
- `find_virtual_mic_devices()` - Locate virtual devices
- `check_virtual_mic_ready()` - Verify configuration
- `get_virtual_mic_setup_instructions()` - Platform guides

### Interface Layer

#### `__init__.py` - VoiceLink Class

Unified API for all functionality:

```python
class VoiceLink:
    # Device management
    list_devices() -> list[AudioDevice]
    find_best_device() -> AudioDevice
    check_setup() -> dict

    # Recording
    capture_to_file(path, duration, ...) -> Path
    start_capture(callback) -> bool
    stop_capture() -> None

    # Streaming
    start_streaming(api_key, ...) -> OpenAIRealtimeStream

    # Claude Skills
    skill_list_audio_devices() -> list[dict]
    skill_record_audio(...) -> dict
    skill_get_recording_status() -> dict
```

#### `cli.py`

Click-based command-line interface:

```
voicelink
├── setup          # Driver installation
├── list-devices   # Device enumeration
├── record         # File recording
├── stream         # OpenAI streaming
├── glossary       # Glossary generation
├── virtual-mic    # Setup instructions
└── info           # System information
```

## Data Flow

### Recording Flow

```
System Audio
    │
    ▼
┌─────────────────┐
│ Virtual Driver  │ (BlackHole/VB-CABLE/PulseAudio)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   sounddevice   │ InputStream
└────────┬────────┘
         │ numpy arrays
         ▼
┌─────────────────┐
│  AudioCapture   │ callback queue
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  AudioRecorder  │ collect chunks
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   scipy/pydub   │ file encoding
└────────┬────────┘
         │
         ▼
    WAV/MP3 File
```

### Streaming Flow

```
System Audio
    │
    ▼
┌─────────────────┐
│  AudioCapture   │
└────────┬────────┘
         │ float32 arrays
         ▼
┌─────────────────┐
│ OpenAIRealtime  │ convert to int16 + base64
│    Stream       │
└────────┬────────┘
         │ WebSocket
         ▼
┌─────────────────┐
│   OpenAI API    │ Realtime endpoint
└────────┬────────┘
         │ JSON events
         ▼
    Callbacks (transcripts, responses)
```

### Glossary Generation Flow

```
Audio File
    │
    ▼
┌─────────────────┐
│AudioTranscriber │ OpenAI Whisper API
└────────┬────────┘
         │ text
         ▼
┌─────────────────┐
│ GlossaryCompiler│ DSPy pipeline
├─────────────────┤
│ TermExtractor   │ → terms[]
│ TermExplainer   │ → explanations[]
│ Categorize      │ → categories[]
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│GlossaryDocument │
└────────┬────────┘
         │
         ▼
    Markdown/JSON
```

## Configuration

### CaptureConfig

```python
@dataclass
class CaptureConfig:
    device: Optional[int] = None     # Auto-detect if None
    sample_rate: int = 44100
    channels: int = 2
    dtype: str = "float32"
    blocksize: int = 1024
    latency: str = "low"
```

### StreamConfig

```python
@dataclass
class StreamConfig:
    api_key: str
    device: Optional[int] = None
    sample_rate: int = 24000         # OpenAI requires 24kHz
    channels: int = 1                # Mono for speech
    model: str = "gpt-4o-realtime-preview"
    voice: str = "alloy"
    instructions: Optional[str] = None
```

### TranscriptionConfig

```python
@dataclass
class TranscriptionConfig:
    api_key: str
    model: str = "whisper-1"
    language: Optional[str] = None   # Auto-detect
    response_format: str = "text"
    temperature: float = 0.0
```

## Platform Support

| Feature | macOS | Windows | Linux |
|---------|-------|---------|-------|
| Audio capture | BlackHole | VB-CABLE | PulseAudio |
| Auto-install | Homebrew | Manual | apt/dnf/pacman |
| Virtual mic | Multi-Output | VB-CABLE | null-sink |
| WAV recording | Yes | Yes | Yes |
| MP3 recording | ffmpeg | ffmpeg | ffmpeg |
| OpenAI streaming | Yes | Yes | Yes |
| Glossary gen | Yes | Yes | Yes |

## Dependencies

### Required
- `sounddevice` - Audio I/O
- `numpy` - Array operations
- `scipy` - WAV file handling
- `click` - CLI framework
- `httpx` - HTTP client
- `websockets` - WebSocket support

### Optional
- `openai` - OpenAI API client
- `dspy-ai` - DSPy framework
- `pydub` - MP3 encoding (requires ffmpeg)

## Thread Safety

- `AudioCapture`: Thread-safe callbacks with lock
- `AudioRecorder`: Background thread for duration
- `OpenAIRealtimeStream`: Async loop in separate thread
- `GlossaryGenerator`: Synchronous (DSPy manages threading)

## Error Handling

- Device not found: Falls back to default input
- No loopback device: Warning with setup instructions
- API errors: Propagated via state.error
- File errors: Raised as exceptions
