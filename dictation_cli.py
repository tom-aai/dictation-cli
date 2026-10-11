#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "assemblyai>=1.5.4",
#     "sounddevice>=0.5.0",
#     "python-dotenv>=1.0.0",
# ]
# ///
"""Test harness for the AssemblyAI Dictation API.

Press Enter to start speaking, Enter again to stop. The recording is sent to the
Dictation API, which returns the verbatim transcript plus an LLM rewrite
(`llm_response`). By default we print the rewrite; pass --full to dump the whole
API response.

Prompts live in prompts.py. Comment the ones you don't want. Each active prompt
is run against the same recording so you can compare rewrites side by side.

Usage (uv manages the dependencies automatically):
    uv run dictation_cli.py                  # default: print llm_response
    uv run dictation_cli.py --full           # print the entire API response
    uv run dictation_cli.py --rewrite-mode smart
"""

import argparse
import sys
import time
from typing import List, Optional, Tuple

import assemblyai as aai
import sounddevice as sd
from assemblyai.dictation.v1 import DictationConfig, DictationResponse, DictationTranscriber
from dotenv import load_dotenv

from prompts import PROMPTS

# ==========================================================================
# Main API input parameters — edit these.
# ==========================================================================

# stt_prompt: a plain-language *description* of the audio (context for the
# transcriber — NOT instructions). Steers vocabulary; it doesn't reformat.
STT_PROMPT = ""

# keyterms_prompt: exact terms to bias the decoder toward (names, drugs, jargon).
KEYTERMS_PROMPT = [""]

# llm_instruction: the rewrite task. NOTE: this is driven by prompts.py — edit
# your prompts THERE, not here. Each active prompt is sent as the llm_instruction.

# --------------------------------------------------------------------------
# Other settings.
# --------------------------------------------------------------------------
LANGUAGE_CODES = ["en"]   # Dictation `language_codes` (always a list).
SAMPLE_RATE = 16000       # Microphone sample rate in Hz.
REGION = "global"         # "global" (nearest), "us", or "eu".

# Dictation hosts by region (global routes to the nearest).
REGION_HOSTS = {
    "global": "https://dictation.assemblyai.com",
    "us": "https://dictation.us.assemblyai.com",
    "eu": "https://dictation.eu.assemblyai.com",
}


class DictationConfigRM(DictationConfig):
    """DictationConfig plus the newly shipped `rewrite_mode` param.

    The stock DictationConfig has `extra: forbid`, so we subclass it to declare
    `rewrite_mode` as a real field. The subclass still passes the SDK's
    `isinstance(config, DictationConfig)` check and serializes `rewrite_mode`
    into the request via `.dict(exclude_none=True)`.
    """

    rewrite_mode: Optional[str] = None


def active_prompts() -> List[Tuple[Optional[str], Optional[str]]]:
    """Active prompts, or a single default-cleanup run when none are enabled.

    Each prompt in prompts.py is a dict with "title" and "prompt". The prompt
    text is written as a free-form triple-quoted string, so collapse its
    indentation and line breaks into a single clean instruction line.
    """
    if not PROMPTS:
        return [("Default cleanup", None)]
    return [(p["title"], " ".join(p["prompt"].split())) for p in PROMPTS]


def record_utterance(transcriber: DictationTranscriber) -> Optional[bytes]:
    """Record 16-bit mono PCM between two Enter presses, returning the PCM bytes.

    Returns None if the user chose to quit at the start prompt.
    """
    frames: List[bytes] = []

    def callback(indata, _frames, _time, status):
        if status:
            print(f"  (audio status: {status})", file=sys.stderr)
        frames.append(bytes(indata))

    answer = input("\nPress Enter to record, or type Q then Enter to quit: ")
    if answer.strip().lower() in {"q", "quit"}:
        return None

    stream = sd.RawInputStream(
        samplerate=SAMPLE_RATE, channels=1, dtype="int16", callback=callback
    )
    with stream:
        # Warm the connection while the user talks, so the handshake isn't part
        # of the latency we measure below.
        transcriber.warm()
        input("Recording... Press Enter to stop... ")

    return b"".join(frames)


def run_prompt(
    transcriber: DictationTranscriber,
    pcm: bytes,
    name: Optional[str],
    instruction: Optional[str],
    args: argparse.Namespace,
) -> None:
    """Send one request for a single prompt and print the result."""
    keyterms = [t for t in KEYTERMS_PROMPT if t and t.strip()]
    config = DictationConfigRM(
        sample_rate=SAMPLE_RATE,
        channels=1,
        language_codes=LANGUAGE_CODES,
        stt_prompt=STT_PROMPT.strip() or None,
        keyterms_prompt=keyterms or None,
        llm_instruction=instruction,
        rewrite_mode=args.rewrite_mode,
    )

    print("\n" + "=" * 70)
    print(f"Prompt: {name}")

    t0 = time.perf_counter()
    try:
        result: DictationResponse = transcriber.transcribe_live(pcm, config)
    except Exception as exc:  # DictationError and friends
        print(f"  Request failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"Round-trip post-speech wait:      {elapsed_ms:.0f} ms")

    if args.full:
        import json

        print("\n--- full API response ---")
        print(json.dumps(result.dict(), indent=2, ensure_ascii=False, default=str))
    else:
        print(f"\nverbatim:     {result.text}")
        if result.llm_error:
            print(f"llm_response: (rewrite failed: {result.llm_error}; falling back to verbatim)")
            print(f"              {result.final_text}")
        else:
            print(f"llm_response: {result.llm_response}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Test the AssemblyAI Dictation API.")
    parser.add_argument(
        "-f", "--full", action="store_true",
        help="print the entire API response instead of just llm_response",
    )
    parser.add_argument(
        "--rewrite-mode", choices=["fast", "smart"], default=None,
        help="rewrite_mode param (default: let the API choose)",
    )
    args = parser.parse_args()

    load_dotenv()
    import os

    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        print("ASSEMBLYAI_API_KEY not set. Put it in a .env file.", file=sys.stderr)
        return 1

    aai.settings.api_key = api_key
    aai.settings.dictation_base_url = REGION_HOSTS[REGION]
    # Keep the pooled connection alive long enough to survive the recording.
    aai.settings.keepalive_expiry = 60

    prompts = active_prompts()
    print(f"Testing {len(prompts)} prompt(s) against one recording.")
    if args.rewrite_mode:
        print(f"rewrite_mode = {args.rewrite_mode}")

    print("Record as many times as you like.")

    with DictationTranscriber() as transcriber:
        while True:
            try:
                pcm = record_utterance(transcriber)
            except (EOFError, KeyboardInterrupt):
                pcm = None
            if pcm is None:
                print("\nGoodbye!")
                break
            print(f"\nRecorded {len(pcm) / 2 / SAMPLE_RATE:.1f}s of audio.")

            for name, instruction in prompts:
                run_prompt(transcriber, pcm, name, instruction, args)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
