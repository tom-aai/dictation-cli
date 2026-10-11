"""Dictation rewrite prompts to test.

Each active entry is sent to the Dictation API as the `llm_instruction` for a
separate request against the same recording, so you can compare how different
prompts rewrite the same audio.

To add a prompt, copy an entry and edit the two fields:
    "title":  a short name for the run (shown in the output)
    "prompt": the instruction text — just type freely between the triple quotes,
              across as many lines as you like. Leading/trailing blank lines and
              the indentation shown here are stripped automatically.

To disable a prompt, comment out its whole `{...}` entry. If every prompt is
commented out, the recording is sent once with the API's default cleanup
(filler removed, punctuation/capitalization applied).
"""

PROMPTS = [
    # {
    #     "title": "Document editing (Granola)",
    #     "prompt": """
    #         The output will be inserted into existing text, replacing [CARET]:
    #         "I think [CARET] we should go". Return only the inserted words so the
    #         combined sentence reads correctly: lowercase unless a name, no final
    #         punctuation.
    #     """,
    # },
    # {
    #     "title": "Verbatim",
    #     "prompt": """
    #         Do not include punctuation. Return exactly what the user said. 
    #     """,
    # },
    {
        "title": "Insert spoken punctuation",
        "prompt": """
            Insert spoken punctuation.
        """,
    },
    # {
    #     "title": "Strict spoken punctuation",
    #     "prompt": """
    #         Insert spoken punctuation. For example, if the user says period, then
    #         insert a period symbol like this: - input: "I am here period" -
    #         output: "I am here." Never insert your own punctuation. If you detect
    #         the end of a sentence but the user didn't say period, don't put a
    #         period. If you see punctuation that the user did not speak, then
    #         remove it from the transcript. Like this: - Input: "I just got here. I
    #         arrived a few minutes ago." - Output: "I just got here I arrived a few
    #         minutes ago."
    #     """,
    # },
]
