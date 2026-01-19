# VoiceLink

Cross-platform system audio capture tool with DSPy-powered glossary generation.

## Features

- **System Audio Capture**: Record audio from Zoom calls, YouTube, or any system audio
- **Cross-Platform**: Works on macOS, Windows, and Linux
- **OpenAI Streaming**: Stream directly to OpenAI Realtime API
- **Glossary Generation**: Extract technical terms and generate explanations using DSPy
- **Virtual Microphone**: Route system audio to apps expecting mic input
- **Claude Skills Compatible**: Use as a Python library or Claude Skill

## Quick Start

```bash
# Install
pip install voicelink[all]

# Check setup
voicelink setup

# Record 30 seconds
voicelink record -o meeting.wav -d 30

# Generate glossary
voicelink glossary meeting.wav -o glossary.md
```

## Installation

```bash
# Basic
pip install voicelink

# With all features
pip install voicelink[all]

# Development
pip install -e ".[all,dev]"
```

### Prerequisites

**macOS**: Install BlackHole
```bash
brew install blackhole-2ch
```

**Windows**: Download [VB-CABLE](https://vb-audio.com/Cable/)

**Linux**: PulseAudio (usually pre-installed)

## Usage

### Python API

```python
from voicelink import VoiceLink

vl = VoiceLink()

# Record audio
vl.capture_to_file("output.wav", duration=30)

# Stream to OpenAI
stream = vl.start_streaming(api_key="sk-...")
```

### Glossary Generation

```python
from voicelink.glossary import GlossaryGenerator

generator = GlossaryGenerator(api_key="sk-...")
glossary = generator.from_audio("meeting.wav")
glossary.save("glossary.md")
```

### CLI

```bash
voicelink list-devices      # Show audio devices
voicelink record -o out.wav -d 60  # Record 60 seconds
voicelink stream            # Stream to OpenAI
voicelink glossary audio.wav -o glossary.md  # Generate glossary
```

## Documentation

- [Usage Guide](docs/usage.md)
- [Architecture](docs/architecture.md)
- [Development Progress](docs/todo.md)

## License

MIT
