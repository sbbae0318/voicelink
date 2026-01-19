# VoiceLink Development Todo

## Current Status: v0.1.0 Initial Development Complete

## Todo Items

### High Priority
- [ ] Unit tests for core modules
- [ ] Integration tests with mock audio devices
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] PyPI package publishing
- [ ] Error handling improvements

### Medium Priority
- [ ] Core Audio Taps support (macOS 14.2+)
- [ ] WASAPI loopback support (Windows native)
- [ ] Real-time audio level visualization
- [ ] Silence detection and auto-stop
- [ ] Audio format auto-detection

### Low Priority
- [ ] GUI application (Tkinter/PyQt)
- [ ] System tray integration
- [ ] Global hotkey support
- [ ] Multiple simultaneous recordings
- [ ] Noise reduction preprocessing

### Glossary Enhancements
- [ ] DSPy optimization and compilation
- [ ] Custom extraction prompts
- [ ] Multi-language glossary support
- [ ] Incremental glossary updates
- [ ] PDF/DOCX export

### Future API Integrations
- [ ] Google Speech-to-Text
- [ ] Azure Speech Services
- [ ] Local Whisper model (whisper.cpp)
- [ ] Claude API direct integration
- [ ] Custom LLM backends

## Known Issues

1. **macOS Sequoia**: Additional permissions may be required
2. **Apple Silicon**: BlackHole requires reduced security mode
3. **Windows 11**: VB-CABLE may need administrator privileges
4. **Linux Wayland**: PulseAudio monitor compatibility varies

## Version Roadmap

### v0.2.0
- Test coverage > 80%
- PyPI release
- Bug fixes

### v0.3.0
- Native Core Audio Taps (macOS)
- WASAPI improvements (Windows)
- Performance optimizations

### v1.0.0
- Stable API
- Full documentation
- Production ready
