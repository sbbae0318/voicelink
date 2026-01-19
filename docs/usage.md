# VoiceLink Usage Guide

VoiceLink is a cross-platform Python tool for capturing system audio (Zoom calls, YouTube, etc.) and generating technical glossaries from audio content.

## Installation

### Basic Installation

```bash
pip install voicelink
```

### With Optional Features

```bash
# OpenAI streaming support
pip install voicelink[openai]

# Glossary generation (includes DSPy)
pip install voicelink[glossary]

# MP3 recording support
pip install voicelink[mp3]

# All features
pip install voicelink[all]
```

### Development Installation

```bash
git clone https://github.com/voicelink/voicelink.git
cd voicelink
pip install -e ".[all,dev]"
```

## Prerequisites

### macOS

VoiceLink requires a virtual audio driver to capture system audio:

```bash
# Install BlackHole (recommended)
brew install blackhole-2ch
```

### Windows

Download and install [VB-CABLE](https://vb-audio.com/Cable/).

### Linux

PulseAudio is usually pre-installed. If not:

```bash
# Ubuntu/Debian
sudo apt install pulseaudio

# Fedora
sudo dnf install pulseaudio

# Arch
sudo pacman -S pulseaudio
```

## Quick Start

### Check Setup

```bash
# Verify installation and driver status
voicelink setup

# List available audio devices
voicelink list-devices
```

### Record System Audio

```bash
# Record 30 seconds to a WAV file
voicelink record -o output.wav -d 30

# Record with specific device
voicelink record -o output.wav -d 60 -D 2

# Record as MP3
voicelink record -o output.mp3 -d 30 -f mp3
```

### Stream to OpenAI

```bash
# Set API key
export OPENAI_API_KEY="sk-..."

# Stream system audio to OpenAI Realtime API
voicelink stream

# Stream for 60 seconds
voicelink stream -d 60

# With custom voice
voicelink stream -v nova
```

### Generate Glossary

```bash
# Generate glossary from audio file
voicelink glossary recording.wav -o glossary.md

# With custom model
voicelink glossary recording.wav -o glossary.md -m gpt-4o
```

## Python API

### Basic Usage

```python
from voicelink import VoiceLink

# Initialize
vl = VoiceLink()

# Check setup
status = vl.check_setup()
print(f"Driver installed: {status['driver_installed']}")

# List devices
devices = vl.list_devices()
for d in devices:
    print(f"[{d.index}] {d.name}")
```

### Recording

```python
from voicelink import VoiceLink

vl = VoiceLink()

# Record to file
result = vl.capture_to_file(
    output_path="meeting.wav",
    duration=3600,  # 1 hour
    sample_rate=44100,
    channels=2,
    format="wav"
)

if result:
    print(f"Saved to: {result}")
```

### Continuous Capture

```python
from voicelink import VoiceLink
import numpy as np

vl = VoiceLink()

def process_audio(data: np.ndarray):
    # Process audio chunk
    print(f"Received {len(data)} samples")

# Start capture with callback
vl.start_capture(callback=process_audio)

# ... do something ...

# Stop capture
vl.stop_capture()
```

### OpenAI Streaming

```python
import os
from voicelink import VoiceLink

vl = VoiceLink()

def on_response(data: dict):
    event_type = data.get("type", "")
    if event_type == "response.audio_transcript.done":
        print(f"Assistant: {data.get('transcript', '')}")

stream = vl.start_streaming(
    api_key=os.environ["OPENAI_API_KEY"],
    on_response=on_response,
    model="gpt-4o-realtime-preview",
    voice="alloy",
    instructions="You are a helpful assistant."
)

# Stream runs in background
# ...

stream.stop()
```

### Glossary Generation

```python
from voicelink import VoiceLink
from voicelink.glossary import GlossaryGenerator

# Record audio first
vl = VoiceLink()
vl.capture_to_file("meeting.wav", duration=3600)

# Generate glossary
generator = GlossaryGenerator(
    api_key="sk-...",
    model="gpt-4o"
)

glossary = generator.from_audio("meeting.wav")

# Save as markdown
glossary.save("meeting_glossary.md")

# Or as JSON
glossary.save("meeting_glossary.json")

# Access entries
for entry in glossary.entries:
    print(f"{entry.term}: {entry.explanation}")
```

### Generate from Transcript

```python
from voicelink.glossary import GlossaryGenerator

generator = GlossaryGenerator(api_key="sk-...")

# From transcript text
glossary = generator.from_transcript(
    transcript="The API uses REST endpoints with OAuth2 authentication...",
    title="API Documentation Glossary",
    domain="Software Engineering"
)

print(glossary.to_markdown())
```

## Claude Skills Integration

VoiceLink provides functions compatible with Claude Skills:

```python
from voicelink import VoiceLink

vl = VoiceLink()

# List devices (returns dict format)
devices = vl.skill_list_audio_devices()

# Check setup
status = vl.skill_check_setup()

# Record audio
result = vl.skill_record_audio(
    output_path="/tmp/recording.wav",
    duration=30,
    format="wav"
)

# Get status
status = vl.skill_get_recording_status()
```

## CLI Commands Reference

| Command | Description |
|---------|-------------|
| `voicelink setup` | Check and install virtual audio drivers |
| `voicelink list-devices` | List available audio devices |
| `voicelink record` | Record system audio to file |
| `voicelink stream` | Stream to OpenAI Realtime API |
| `voicelink glossary` | Generate glossary from audio |
| `voicelink virtual-mic` | Show virtual mic setup instructions |
| `voicelink info` | Show system information |

### Record Options

```
-o, --output      Output file path (required)
-d, --duration    Recording duration in seconds (required)
-D, --device      Device index
-r, --sample-rate Sample rate in Hz (default: 44100)
-c, --channels    Number of channels (default: 2)
-f, --format      Output format: wav or mp3 (default: wav)
```

### Stream Options

```
-k, --api-key     OpenAI API key (or set OPENAI_API_KEY)
-d, --duration    Duration in seconds (optional)
-D, --device      Device index
-m, --model       Model (default: gpt-4o-realtime-preview)
-v, --voice       Voice (default: alloy)
-i, --instructions System instructions
```

## Virtual Microphone Setup

To route system audio to applications expecting microphone input:

### macOS with BlackHole

1. Install BlackHole: `brew install blackhole-2ch`
2. Open "Audio MIDI Setup" (Applications > Utilities)
3. Click "+" and select "Create Multi-Output Device"
4. Check your speakers/headphones AND BlackHole 2ch
5. Right-click and select "Use This Device For Sound Output"
6. In your app, select "BlackHole 2ch" as microphone input

### Windows with VB-CABLE

1. Install VB-CABLE from https://vb-audio.com/Cable/
2. Set VB-CABLE as default playback device
3. In your app, select "CABLE Output" as microphone input

### Linux with PulseAudio

```bash
# Create virtual sink
pactl load-module module-null-sink sink_name=VirtualMic

# Route audio
pactl load-module module-loopback source=<source>.monitor sink=VirtualMic
```

## Troubleshooting

### No loopback device found

Run `voicelink setup` to check if virtual audio drivers are installed.

### Recording is silent

1. Ensure system audio is playing
2. Check that the correct device is selected
3. On macOS, ensure Multi-Output Device is set as system output

### OpenAI streaming errors

1. Verify API key is valid
2. Check internet connection
3. Ensure you have access to the Realtime API

### MP3 recording fails

Install ffmpeg:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg

# Windows
winget install ffmpeg
```
