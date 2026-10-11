# Dictation API test harness

A small CLI for testing the [AssemblyAI Dictation API](https://www.assemblyai.com/docs):
speak an utterance, get back the verbatim transcript plus an LLM rewrite
(`llm_response`), and measure the post-speech wait (how long from when you stop
recording to when the transcript appears in the terminal).

## Setup

Requires [uv](https://docs.astral.sh/uv/). 

1. Add your API key:

   ```bash
   cp .env.example .env   # then put your key in .env
   ```

   `.env`:

   ```
   ASSEMBLYAI_API_KEY=your_api_key_here
   ```

2. Run it. The first run installs the dependencies, then starts the tool:

   ```bash
   uv run dictation_cli.py
   ```

## Usage

```bash
uv run dictation_cli.py                  # default: print llm_response
uv run dictation_cli.py --full           # print the entire API response
uv run dictation_cli.py --rewrite-mode smart # 'smart' or 'fast'
```

At the prompt, press **Enter** to start recording and **Enter** again to stop.
For each active prompt, the tool prints the **round-trip post-speech wait** (ms from stop to
transcript appearing in the terminal), the verbatim transcript, and the LLM rewrite.

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `-f`, `--full` | off | Print the entire API response (JSON) instead of just `llm_response`. |
| `--rewrite-mode {fast,smart}` | API default | The `rewrite_mode` param. |

### Editing the API inputs

You can change the API input parameters directly in
[`dictation_cli.py`](dictation_cli.py). The three main ones are constants at the
top of the file:

- `STT_PROMPT`: context describing the audio (steers vocabulary; it does not
  reformat).
- `KEYTERMS_PROMPT`: exact keyterms to bias the decoder toward (names, drugs,
  jargon).
- `llm_instruction`: the rewrite task. **You don't edit this in the script** —
  it is driven by [`prompts.py`](prompts.py). To change the LLM instructions,
  edit your prompts there (see [Prompts](#prompts) below).

Other settings (`LANGUAGE_CODES`, `SAMPLE_RATE`, `REGION`) are constants in the
script too. Edit the code to change them.

## Prompts

Prompts live in [`prompts.py`](prompts.py) as a list of entries, each a dict with
a `"title"` (a short name shown in the output) and a `"prompt"` (the instruction
text, written as a free-form triple-quoted string). Each active prompt is sent to
the API as the `llm_instruction` for a separate request against the same
recording, so you can compare rewrites side by side.

- **Comment out** an entry's `{...}` block to disable that prompt.
- If **every** prompt is commented out, the recording is sent once with the
  API's default cleanup (filler removed, punctuation/capitalization applied).

## Notes

- Uses the AssemblyAI Python SDK. The newly shipped `rewrite_mode` param isn't in
  the SDK's `DictationConfig` yet, so `dictation_cli.py` subclasses it to add the
  field (see `DictationConfigRM`); everything else goes through the SDK.
- The connection is pre-warmed while you speak so the handshake isn't counted in
  the post-speech wait.
