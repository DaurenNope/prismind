from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from .content_planner import RewritePlan
from .schemas import RewriteDraft, RewriteRequest


@dataclass(slots=True)
class PromptBuilderConfig:
    default_max_tokens: int = 800
    twitter_max_tokens: int = 320
    twitter_thread_max_tokens: int = 640


class PromptBuilder:
    """
    Builds platform-aware prompts that respect persona language, planner
    decisions, and optional human drafts.
    """

    def __init__(self, config: PromptBuilderConfig | None = None) -> None:
        self.config = config or PromptBuilderConfig()

    def build(self, request: RewriteRequest, plan: RewritePlan) -> RewriteDraft:
        if request.custom_prompt:
            prompt = request.custom_prompt
            metadata = {"builder": "custom"}
            max_tokens = self.config.default_max_tokens
        else:
            prompt, metadata, max_tokens = self._build_structured_prompt(request, plan)

        return RewriteDraft(
            prompt=prompt,
            max_tokens=max_tokens,
            prompt_metadata=metadata,
        )

    def _build_structured_prompt(
        self, request: RewriteRequest, plan: RewritePlan
    ) -> tuple[str, Dict[str, str], int]:
        platform = request.platform.lower()
        if platform == "twitter":
            prompt = self._build_twitter_prompt(request, plan)
            max_tokens = (
                self.config.twitter_thread_max_tokens
                if request.platform_constraints and request.platform_constraints.get("use_threads")
                else self.config.twitter_max_tokens
            )
            return prompt, {"builder": "twitter"}, max_tokens
        if platform == "threads":
            prompt = self._build_threads_prompt(request, plan)
            return prompt, {"builder": "threads"}, self.config.default_max_tokens
        if platform == "telegram":
            prompt = self._build_telegram_prompt(request, plan)
            return prompt, {"builder": "telegram"}, self.config.default_max_tokens

        prompt = self._build_generic_prompt(request, plan)
        return prompt, {"builder": "generic"}, self.config.default_max_tokens

    def _build_twitter_prompt(self, request: RewriteRequest, plan: RewritePlan) -> str:
        persona = request.persona
        analysis = request.analyzed_content
        summary = analysis.get("ai_summary") or analysis.get("summary") or ""
        content = analysis.get("content") or ""
        hook_line = plan.hook or "Write a sharp hook."
        human_draft = plan.human_draft

        base = [
            f"You are {persona.name or persona.key}, writing for Twitter in {persona.language}.",
            "Rules:",
            "- Keep the tweet under 220 characters (unless explicitly told to create a thread).",
            "- No hashtags, no emojis, no fluff.",
            "- Lead with a hook: " + hook_line,
        ]

        if request.platform_constraints and request.platform_constraints.get("use_threads"):
            base[2] = "- If a thread is required, keep each tweet under 250 characters and use numbered segments."

        if human_draft:
            base.append("\nHuman draft provided. Use it as the backbone and polish it in persona voice:\n" + human_draft)
        else:
            base.extend(
                [
                    "\nKey summary:",
                    summary,
                    "\nSource content:",
                    content,
                ]
            )

        if plan.call_to_action:
            base.append(f"\nEnd with this CTA (natural tone): {plan.call_to_action}")

        return "\n".join(base) + "\n\nWrite only the tweet(s)."

    def _build_threads_prompt(self, request: RewriteRequest, plan: RewritePlan) -> str:
        persona = request.persona
        analysis = request.analyzed_content
        summary = analysis.get("ai_summary") or ""
        content = analysis.get("content") or ""
        human_draft = plan.human_draft

        body = [
            f"You are {persona.name or persona.key}, writing in {persona.language} for Threads.",
            "Tone: conversational, insightful, technical when needed.",
            "Structure: Hook → Context → Insight → CTA (optional).",
        ]

        if human_draft:
            body.append("\nHuman draft to refine:\n" + human_draft)
        else:
            body.extend(
                [
                    "\nStart from this summary:",
                    summary,
                    "\nDetailed content:",
                    content,
                ]
            )

        if plan.angle:
            body.append(f"\nAngle to emphasize: {plan.angle}")
        if plan.call_to_action:
            body.append(f"\nCall to action: {plan.call_to_action}")

        return "\n".join(body) + "\n\nWrite the final post with clean paragraphs."

    def _build_telegram_prompt(self, request: RewriteRequest, plan: RewritePlan) -> str:
        persona = request.persona
        analysis = request.analyzed_content
        summary = analysis.get("ai_summary") or ""
        content = analysis.get("content") or ""
        human_draft = plan.human_draft

        body = [
            f"You are {persona.name or persona.key}, preparing a Telegram post in {persona.language}.",
            "Use Markdown for emphasis. Structure:",
            "1. Bold intro with the core idea.",
            "2. Context and analysis (2-3 short paragraphs).",
            "3. Takeaways or recommendations.",
        ]

        if human_draft:
            body.append("\nHuman draft to start from:\n" + human_draft)
        else:
            body.extend(
                [
                    "\nSummary to cover:",
                    summary,
                    "\nSupporting details:",
                    content,
                ]
            )

        if plan.human_notes:
            body.append(f"\nHuman notes to incorporate: {plan.human_notes}")
        if plan.call_to_action:
            body.append(f"\nCall to action: {plan.call_to_action}")

        return "\n".join(body) + "\n\nWrite the final Telegram post."

    def _build_generic_prompt(self, request: RewriteRequest, plan: RewritePlan) -> str:
        persona = request.persona
        analysis = request.analyzed_content
        summary = analysis.get("ai_summary") or analysis.get("summary") or ""
        content = analysis.get("content") or ""
        human_draft = plan.human_draft

        lines = [
            f"You are {persona.name or persona.key} writing in {persona.language} for {request.platform}.",
            f"Tone: {persona.tone or 'authentic and authoritative'}.",
        ]

        if human_draft:
            lines.append("\nRefine this human draft, keeping their intent but elevating clarity:\n" + human_draft)
        else:
            lines.extend(
                [
                    "\nKey points:",
                    summary,
                    "\nFull source content:",
                    content,
                ]
            )

        if plan.angle:
            lines.append(f"\nPrimary angle: {plan.angle}")
        if plan.call_to_action:
            lines.append(f"\nDesired CTA: {plan.call_to_action}")

        return "\n".join(lines) + "\n\nProduce the final post only."


