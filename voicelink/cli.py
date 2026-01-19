"""Command-line interface for VoiceLink."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import click

from . import __version__
from .devices import find_best_loopback_device, list_devices, print_devices
from .platform_utils import get_driver_status, get_platform, get_system_info, setup_driver
from .recorder import record_audio
from .virtual_mic import check_virtual_mic_ready, get_virtual_mic_setup_instructions


@click.group()
@click.version_option(version=__version__)
def main():
    """VoiceLink - System audio capture and streaming tool."""
    pass


@main.command()
@click.option("--all", "-a", "show_all", is_flag=True, help="Show all devices")
@click.option("--loopback", "-l", is_flag=True, help="Show only loopback devices")
def list_devices_cmd(show_all: bool, loopback: bool):
    """List available audio devices."""
    devices = list_devices()

    if loopback:
        devices = [d for d in devices if d.is_loopback or d.is_virtual]

    if not devices:
        click.echo("No audio devices found.")
        if loopback:
            click.echo("\nTip: Run 'voicelink setup' to install virtual audio drivers.")
        return

    print_devices(devices)


@main.command()
@click.option("--auto-install", "-y", is_flag=True, help="Auto-install drivers if missing")
def setup(auto_install: bool):
    """Check and install virtual audio drivers."""
    click.echo("Checking system configuration...\n")

    # Show system info
    info = get_system_info()
    click.echo(f"Platform: {info['platform']}")
    click.echo(f"System: {info['system']} {info['release']}")
    click.echo(f"Python: {info['python_version'].split()[0]}")
    click.echo()

    # Check driver status
    status = setup_driver(auto_install=auto_install)

    if status.installed:
        click.echo(click.style(f"[OK] {status.driver_name} is installed", fg="green"))
        if status.device_name:
            click.echo(f"     Device: {status.device_name}")

        # Check virtual mic readiness
        mic_status = check_virtual_mic_ready()
        if mic_status["ready"]:
            click.echo(click.style("\n[OK] Virtual microphone is ready", fg="green"))
            click.echo(f"     Loopback: {mic_status['loopback_device']}")
        else:
            click.echo(click.style("\n[WARN] Virtual microphone needs configuration", fg="yellow"))
            click.echo(get_virtual_mic_setup_instructions())
    else:
        click.echo(click.style(f"[MISSING] {status.driver_name}", fg="red"))
        if status.install_instructions:
            click.echo(f"\n{status.install_instructions}")


@main.command()
@click.option("--output", "-o", required=True, type=click.Path(), help="Output file path")
@click.option("--duration", "-d", required=True, type=float, help="Recording duration in seconds")
@click.option("--device", "-D", type=int, help="Device index (use list-devices to see available)")
@click.option("--sample-rate", "-r", default=44100, type=int, help="Sample rate (Hz)")
@click.option("--channels", "-c", default=2, type=int, help="Number of channels")
@click.option("--format", "-f", "output_format", default="wav", type=click.Choice(["wav", "mp3"]))
def record(
    output: str,
    duration: float,
    device: Optional[int],
    sample_rate: int,
    channels: int,
    output_format: str,
):
    """Record system audio to a file."""
    # Check if loopback device is available
    if device is None:
        loopback = find_best_loopback_device()
        if loopback:
            device = loopback.index
            click.echo(f"Using loopback device: {loopback.name}")
        else:
            click.echo(
                click.style(
                    "Warning: No loopback device found. Recording from default input.", fg="yellow"
                )
            )
            click.echo("Run 'voicelink setup' to install virtual audio drivers.\n")

    output_path = Path(output)
    click.echo(f"Recording {duration}s to {output_path} ({output_format.upper()})...")

    result = record_audio(
        output_path=output_path,
        duration=duration,
        device=device,
        sample_rate=sample_rate,
        channels=channels,
        format=output_format,
    )

    if result:
        click.echo(click.style(f"\nRecording saved: {result}", fg="green"))
    else:
        click.echo(click.style("\nRecording failed.", fg="red"))
        sys.exit(1)


@main.command()
@click.option("--api-key", "-k", envvar="OPENAI_API_KEY", help="OpenAI API key")
@click.option("--duration", "-d", type=float, help="Duration in seconds (optional)")
@click.option("--device", "-D", type=int, help="Device index")
@click.option("--model", "-m", default="gpt-4o-realtime-preview", help="OpenAI model")
@click.option("--voice", "-v", default="alloy", help="Voice for responses")
@click.option("--instructions", "-i", help="System instructions for the model")
def stream(
    api_key: Optional[str],
    duration: Optional[float],
    device: Optional[int],
    model: str,
    voice: str,
    instructions: Optional[str],
):
    """Stream system audio to OpenAI Realtime API."""
    if not api_key:
        click.echo(click.style("Error: OpenAI API key required.", fg="red"))
        click.echo("Set OPENAI_API_KEY environment variable or use --api-key option.")
        sys.exit(1)

    # Import here to avoid loading if not needed
    from .stream import OpenAIRealtimeStream, StreamConfig

    # Check for loopback device
    if device is None:
        loopback = find_best_loopback_device()
        if loopback:
            device = loopback.index
            click.echo(f"Using loopback device: {loopback.name}")
        else:
            click.echo(
                click.style(
                    "Warning: No loopback device found. Streaming from default input.", fg="yellow"
                )
            )

    config = StreamConfig(
        api_key=api_key,
        device=device,
        model=model,
        voice=voice,
        instructions=instructions,
    )

    stream_obj = OpenAIRealtimeStream(config)

    def on_transcript(data: dict):
        event_type = data.get("type", "")
        if event_type == "conversation.item.input_audio_transcription.completed":
            click.echo(f"\n[You]: {data.get('transcript', '')}")
        elif event_type == "response.audio_transcript.done":
            click.echo(f"\n[Assistant]: {data.get('transcript', '')}")

    stream_obj.add_response_callback(on_transcript)

    click.echo(f"Streaming to OpenAI ({model})...")
    if duration:
        click.echo(f"Duration: {duration}s")
    click.echo("Press Ctrl+C to stop.\n")

    stream_obj.start()

    try:
        import time

        if duration:
            time.sleep(duration)
        else:
            while stream_obj.is_streaming:
                time.sleep(1)
    except KeyboardInterrupt:
        click.echo("\n\nStopping stream...")
    finally:
        stream_obj.stop()

    if stream_obj.state.error:
        click.echo(click.style(f"\nError: {stream_obj.state.error}", fg="red"))


@main.command()
def virtual_mic():
    """Show virtual microphone setup instructions."""
    status = check_virtual_mic_ready()

    if status["ready"]:
        click.echo(click.style("Virtual microphone is ready!", fg="green"))
        click.echo(f"\nLoopback device: {status['loopback_device']}")
        if status["virtual_output_device"]:
            click.echo(f"Virtual output: {status['virtual_output_device']}")
    else:
        click.echo(click.style("Virtual microphone needs setup.\n", fg="yellow"))
        click.echo(status["instructions"] or get_virtual_mic_setup_instructions())


@main.command()
@click.argument("audio_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output glossary file")
@click.option("--api-key", "-k", envvar="OPENAI_API_KEY", help="OpenAI API key")
@click.option("--model", "-m", default="gpt-4o", help="Model for glossary generation")
def glossary(audio_file: str, output: Optional[str], api_key: Optional[str], model: str):
    """Generate a technical glossary from an audio file."""
    if not api_key:
        click.echo(click.style("Error: OpenAI API key required.", fg="red"))
        click.echo("Set OPENAI_API_KEY environment variable or use --api-key option.")
        sys.exit(1)

    try:
        from .glossary import GlossaryGenerator
    except ImportError:
        click.echo(click.style("Error: Glossary feature requires additional dependencies.", fg="red"))
        click.echo("Install with: pip install voicelink[glossary]")
        sys.exit(1)

    click.echo(f"Generating glossary from: {audio_file}")

    generator = GlossaryGenerator(api_key=api_key, model=model)
    glossary_doc = generator.from_audio(audio_file)

    if output:
        output_path = Path(output)
        glossary_doc.save(output_path)
        click.echo(click.style(f"\nGlossary saved: {output_path}", fg="green"))
    else:
        # Print to stdout
        click.echo("\n" + "=" * 60)
        click.echo(glossary_doc.to_markdown())


@main.command()
def info():
    """Show system and configuration information."""
    info = get_system_info()
    driver = get_driver_status()

    click.echo("System Information:")
    click.echo(f"  Platform: {info['platform']}")
    click.echo(f"  System: {info['system']} {info['release']}")
    click.echo(f"  Machine: {info['machine']}")
    click.echo(f"  Python: {info['python_version'].split()[0]}")

    click.echo(f"\nAudio Driver:")
    click.echo(f"  Driver: {driver.driver_name}")
    click.echo(f"  Installed: {'Yes' if driver.installed else 'No'}")
    if driver.device_name:
        click.echo(f"  Device: {driver.device_name}")

    # Check for optional dependencies
    click.echo("\nOptional Dependencies:")

    try:
        import pydub

        click.echo("  pydub (MP3): Installed")
    except ImportError:
        click.echo("  pydub (MP3): Not installed")

    try:
        import dspy

        click.echo("  dspy (Glossary): Installed")
    except ImportError:
        click.echo("  dspy (Glossary): Not installed")

    try:
        import openai

        click.echo("  openai: Installed")
    except ImportError:
        click.echo("  openai: Not installed")


if __name__ == "__main__":
    main()
