from __future__ import annotations

import re
from typing import Dict


class PostProcessor:
    """
    Applies lightweight cleanup rules to model output.

    The heavy-duty validators (fact/voice/length) still live in the legacy
    pipeline for now; this class focuses on simple deterministic fixes so we
    can reuse it across both the old and new implementations.
    """

    THINK_TAG_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
    EXTRA_NEWLINES = re.compile(r"\n{3,}")

    def run(self, text: str, *, strip_instructions: bool = True) -> str:
        cleaned = self.THINK_TAG_RE.sub("", text)
        cleaned = self.EXTRA_NEWLINES.sub("\n\n", cleaned)
        cleaned = cleaned.strip()

        if strip_instructions:
            cleaned = self._strip_instruction_markers(cleaned)

        return cleaned

    @staticmethod
    def _strip_instruction_markers(text: str) -> str:
        patterns = [
            r"(?im)^\s*🎲.*$",
            r"(?im)^\s*(start with|begin with|you must start|instructions:).*$",
        ]

        for pattern in patterns:
            text = re.sub(pattern, "", text, flags=re.MULTILINE)

        return text.strip()


