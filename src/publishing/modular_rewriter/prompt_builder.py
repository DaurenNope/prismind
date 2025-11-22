from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
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

    def _load_custom_prompt(self, persona_key: str, platform: str) -> Optional[str]:
        """Load custom prompt template if it exists"""
        prompts_file = Path("config/personas/prompts") / f"{persona_key}_prompts.json"
        if not prompts_file.exists():
            return None
        
        try:
            with open(prompts_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                templates = data.get("templates", data)
                return templates.get(platform, "").strip() or None
        except Exception:
            return None

    def _build_structured_prompt(
        self, request: RewriteRequest, plan: RewritePlan
    ) -> tuple[str, Dict[str, str], int]:
        platform = request.platform.lower()
        persona_key = request.persona.key
        
        # Check for custom prompt template first
        custom_prompt = self._load_custom_prompt(persona_key, platform)
        if custom_prompt:
            # Replace placeholders in custom prompt
            prompt = self._render_custom_prompt(custom_prompt, request, plan)
            return prompt, {"builder": f"custom_{platform}"}, self.config.default_max_tokens
        
        # Use default builders
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
    
    def _render_custom_prompt(self, template: str, request: RewriteRequest, plan: RewritePlan) -> str:
        """Render custom prompt template with placeholders"""
        # Simple placeholder replacement
        replacements = {
            "{persona_name}": request.persona.name or request.persona.key,
            "{persona_language}": request.persona.language or "russian",
            "{platform}": request.platform,
            "{hook}": plan.hook or "",
            "{angle}": plan.angle or "",
            "{cta}": plan.call_to_action or "",
            "{human_draft}": plan.human_draft or "",
            "{summary}": request.analyzed_content.get("ai_summary", ""),
            "{content}": request.analyzed_content.get("content", ""),
        }
        
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, str(value))
        
        return result

    def _build_twitter_prompt(self, request: RewriteRequest, plan: RewritePlan) -> str:
        persona = request.persona
        analysis = request.analyzed_content
        summary = analysis.get("ai_summary") or analysis.get("summary") or ""
        content = analysis.get("content") or ""
        hook_line = plan.hook or "Write a sharp hook."
        human_draft = plan.human_draft

        # Detect if this is a promotional post
        is_promo = human_draft and any(keyword in human_draft.lower() for keyword in [
            "launch", "launching", "new website", "new product", "new service",
            "запуск", "запускаем", "новый сайт", "новый продукт", "новый сервис",
            "promo", "promotion", "promote"
        ]) if human_draft else False

        base = [
            f"You are {persona.name or persona.key}.",
            f"🚨 ОБЯЗАТЕЛЬНО: Пиши ТОЛЬКО на русском языке для Twitter.",
            "Тон: разговорный, личный, аутентичный. НЕ корпоративный, НЕ AI-генерированный.",
            "- МАКСИМУМ 220 символов (если не требуется тред).",
            "- Никаких хэштегов, эмодзи, воды.",
            "- Начни с хука: " + hook_line,
        ]

        if request.platform_constraints and request.platform_constraints.get("use_threads"):
            base[3] = "- If a thread is required, keep each tweet under 250 characters and use numbered segments."

        if human_draft:
            # Detect if this is a brief instruction vs full draft
            is_brief_instruction = (
                len(human_draft) < 100 
                or human_draft.lower().startswith("write")
                or human_draft.lower().startswith("напиши")
                or ":" in human_draft and len(human_draft.split(":")) == 2
            )
            
            banned_phrases = [
                "с гордостью", "с гордостью представляем", "приглашаем",
                "уважаемые клиенты", "добро пожаловать", "мы рады"
            ]
            
            if is_brief_instruction:
                if is_promo:
                    tone_instruction = (
                        "- Тон: прямой, личный, но без лишней драмы. "
                        "Говори фактами: что запустили, зачем, где найти. "
                        "Можно легкая ирония, но НЕ рассказывай про усталость/бессонные ночи.\n"
                    )
                else:
                    tone_instruction = (
                        "- Тон: уверен и хриповатый, будто друг описывает апдейт за кофе. Можно начать с «Ну всё», «Так, делаем…».\n"
                    )
                
                # Generic instruction to preserve any URLs/brands/project names from draft
                url_instruction = (
                    "- Сохрани все URL, названия проектов и бренды из задания ТОЧНО как есть.\n"
                    "  Если в задании упомянут проект/URL/бренд — используй ЕГО, не заменяй на другой.\n"
                )
                
                base.append(
                    f"\nЗадание: {human_draft}"
                    + "\n\n🚨 КРИТИЧЕСКИЕ ПРАВИЛА:\n"
                    + "- МАКСИМУМ 220 символов. Если превысил — сократи до 220.\n"
                    + "- ЯЗЫК: ТОЛЬКО РУССКИЙ. ИГНОРИРУЙ язык задания — пиши на русском.\n"
                    + "  Английский используй ТОЛЬКО для брендов/URL/названий проектов из задания.\n"
                    + "  НЕ переводи задание дословно. Извлеки СУТЬ и напиши с нуля на русском.\n"
                    + url_instruction
                    + "- Структура: Хук (1 предложение) → Суть (1 предложение) → CTA с URL (1 предложение).\n"
                    + f"- ЗАПРЕЩЕНО: {', '.join(banned_phrases)}.\n"
                    + tone_instruction
                    + "- НЕ звучи как AI. Коротко, лично, без пафоса."
                )
            else:
                if is_promo:
                    tone_instruction = (
                        "- Тон: прямой, личный, но без лишней драмы. "
                        "Говори фактами: что запустили, зачем, где найти. "
                        "Можно легкая ирония, но НЕ рассказывай про усталость/бессонные ночи.\n"
                    )
                else:
                    tone_instruction = (
                        "- Тон: уверен и хриповатый, будто друг описывает апдейт за кофе. Можно начать с «Ну всё», «Так, делаем…».\n"
                    )
                
                # Generic instruction to preserve any URLs/brands/project names from draft
                url_instruction = (
                    "- Сохрани все URL, названия проектов и бренды из черновика ТОЧНО как есть.\n"
                    "  Если в черновике упомянут проект/URL/бренд — используй ЕГО, не заменяй на другой.\n"
                )
                
                base.append(
                    "\nHuman draft provided. Use it as the backbone and polish it в голосе Qronoya:\n"
                    + human_draft
                    + "\n\n🚨 КРИТИЧЕСКИЕ ПРАВИЛА:\n"
                    + "- МАКСИМУМ 220 символов. Если превысил — сократи до 220.\n"
                    + "- ЯЗЫК: ТОЛЬКО РУССКИЙ. Если черновик на английском — переведи и перепиши на русском.\n"
                    + "  Английский используй ТОЛЬКО для брендов/URL/названий проектов из черновика.\n"
                    + url_instruction
                    + "- Сохрани все конкретные детали (названия, цифры, факты) из черновика.\n"
                    + "- Структура: Хук (1 предложение) → Суть (1 предложение) → CTA с URL (1 предложение).\n"
                    + f"- ЗАПРЕЩЕНО: {', '.join(banned_phrases)}.\n"
                    + tone_instruction
                    + "- НЕ звучи как AI. Коротко, лично, без пафоса."
                )
        else:
            base.extend(
                [
                    "\nKey summary:",
                    summary,
                    "\nSource content:",
                    content,
                ]
            )

        voice_cues = self._render_voice_cues(plan)
        if voice_cues:
            base.append(voice_cues)

        if plan.call_to_action:
            base.append(f"\nEnd with this CTA (natural tone): {plan.call_to_action}")

        return "\n".join(base) + "\n\n🚨 ФИНАЛЬНАЯ ИНСТРУКЦИЯ:\nНапиши твит на РУССКОМ языке. МАКСИМУМ 220 символов. Коротко, лично, без AI-пафоса. Пиши как живой человек, не как корпоративный бот."

    def _build_threads_prompt(self, request: RewriteRequest, plan: RewritePlan) -> str:
        persona = request.persona
        analysis = request.analyzed_content
        summary = analysis.get("ai_summary") or ""
        content = analysis.get("content") or ""
        human_draft = plan.human_draft

        # Detect if this is a promotional post
        is_promo = human_draft and any(keyword in human_draft.lower() for keyword in [
            "launch", "launching", "new website", "new product", "new service",
            "запуск", "запускаем", "новый сайт", "новый продукт", "новый сервис",
            "promo", "promotion", "promote"
        ]) if human_draft else False
        
        body = [
            f"You are {persona.name or persona.key}.",
            f"🚨 ОБЯЗАТЕЛЬНО: Пиши ТОЛЬКО на русском языке для Threads.",
            "Тон: разговорный, личный, аутентичный. НЕ корпоративный, НЕ AI-генерированный.",
            "Структура: Хук → Суть → CTA (опционально).",
        ]

        voice_cues = self._render_voice_cues(plan)
        
        if human_draft:
            # Detect if this is a brief instruction vs full draft
            is_brief_instruction = (
                len(human_draft) < 100 
                or human_draft.lower().startswith("write")
                or human_draft.lower().startswith("напиши")
                or ":" in human_draft and len(human_draft.split(":")) == 2
            )
            
            banned_phrases = [
                "с гордостью", "с гордостью сообщаю", "наш новый дом",
                "мы очень ждем", "уважаемые клиенты", "приглашаем",
                "добро пожаловать", "мы рады", "с радостью"
            ]
            
            if is_brief_instruction:
                # Brief instruction - extract topic and write from scratch
                if is_promo:
                    # Promotional post: straightforward, authentic, but not overly personal/dramatic
                    tone_instruction = (
                        "- Тон: прямой, личный, но без лишней драмы. "
                        "Говори фактами: что запустили, зачем, где найти. "
                        "Можно легкая ирония, но НЕ рассказывай про усталость/бессонные ночи/нервные срывы.\n"
                    )
                else:
                    # Personal/opinion post: can be more emotional
                    tone_instruction = (
                        "- Тон: личный, усталый, ироничный. Как друг рассказывает о запуске после бессонной ночи.\n"
                    )
                
                if is_promo:
                    structure_instruction = (
                        "- Структура: Хук (1 предложение) → Что запустили и зачем (2–3 предложения с деталями) → CTA с URL (1 предложение).\n"
                        "  Используй 350–450 символов. Добавь конкретику: что можно найти на сайте, для кого это, почему важно.\n"
                    )
                else:
                    structure_instruction = (
                        "- Структура: Хук (1 предложение) → Суть (1–2 предложения) → CTA с URL (1 предложение).\n"
                    )
                
                # Generic instruction to preserve any URLs/brands/project names from draft
                url_instruction = (
                    "- Сохрани все URL, названия проектов и бренды из задания ТОЧНО как есть.\n"
                    "  Если в задании упомянут проект/URL/бренд — используй ЕГО, не заменяй на другой.\n"
                )
                
                rules = [
                    f"\nЗадание: {human_draft}",
                    "\n🚨 КРИТИЧЕСКИЕ ПРАВИЛА:\n",
                    "- МАКСИМУМ 480 символов. Если превысил — сократи до 480.\n",
                    "- ЯЗЫК: ТОЛЬКО РУССКИЙ. ИГНОРИРУЙ язык задания — пиши на русском.\n",
                    "  Английский используй ТОЛЬКО для брендов/URL/названий проектов из задания.\n",
                    "  НЕ переводи задание дословно. Извлеки СУТЬ и напиши с нуля на русском.\n",
                    url_instruction,
                    structure_instruction,
                    f"- ЗАПРЕЩЕНО: {', '.join(banned_phrases)}.\n",
                    tone_instruction,
                    "- Можно начать с «Так, делаем официально», «Ну всё» — но не обязательно.\n",
                    "- Говори от себя (я/мы), не от компании-робота.\n",
                    "- НЕ звучи как AI. Никаких длинных описаний процесса, никакой драмы."
                ]
            else:
                # Full draft - refine it
                if is_promo:
                    tone_instruction = (
                        "- Тон: прямой, личный, но без лишней драмы. "
                        "Говори фактами: что запустили, зачем, где найти. "
                        "Можно легкая ирония, но НЕ рассказывай про усталость/бессонные ночи/нервные срывы.\n"
                    )
                else:
                    tone_instruction = (
                        "- Тон: личный, усталый, ироничный. Как друг рассказывает о запуске после бессонной ночи.\n"
                    )
                
                if is_promo:
                    structure_instruction = (
                        "- Структура: Хук (1 предложение) → Что запустили и зачем (2–3 предложения с деталями) → CTA с URL (1 предложение).\n"
                        "  Используй 350–450 символов. Добавь конкретику: что можно найти на сайте, для кого это, почему важно.\n"
                    )
                else:
                    structure_instruction = (
                        "- Структура: Хук (1 предложение) → Суть (1–2 предложения) → CTA с URL (1 предложение).\n"
                    )
                
                # Generic instruction to preserve any URLs/brands/project names from draft
                url_instruction = (
                    "- Сохрани все URL, названия проектов и бренды из черновика ТОЧНО как есть.\n"
                    "  Если в черновике упомянут проект/URL/бренд — используй ЕГО, не заменяй на другой.\n"
                )
                
                rules = [
                    "\nHuman draft to refine in Qronoya voice:\n" + human_draft,
                    "\n🚨 КРИТИЧЕСКИЕ ПРАВИЛА:\n",
                    "- МАКСИМУМ 480 символов. Если превысил — сократи до 480.\n",
                    "- ЯЗЫК: ТОЛЬКО РУССКИЙ. Если черновик на английском — переведи и перепиши на русском.\n",
                    "  Английский используй ТОЛЬКО для брендов/URL/названий проектов из черновика.\n",
                    url_instruction,
                    "- Сохрани все конкретики из черновика (названия, цифры, факты).\n",
                    structure_instruction,
                    f"- ЗАПРЕЩЕНО: {', '.join(banned_phrases)}.\n",
                    tone_instruction,
                    "- Можно начать с «Так, делаем официально», «Ну всё» — но не обязательно.\n",
                    "- Говори от себя (я/мы), не от компании-робота.\n",
                    "- НЕ звучи как AI. Никаких длинных описаний процесса, никакой драмы."
                ]
            
            if voice_cues:
                rules.append(
                    "\n🎯 ГОЛОСОВЫЕ ПРИМЕРЫ (ОБЯЗАТЕЛЬНО ИСПОЛЬЗУЙ КАК ШАБЛОН):\n"
                    + voice_cues.replace("Voice cues from authentic posts:", "")
                    + "\nЭти примеры показывают ТВОЙ реальный голос. Пиши в таком же стиле — не копируй слова, но копируй ТОН и СТРУКТУРУ."
                )
            
            body.extend(rules)
        else:
            body.extend(
                [
                    "\nStart from this summary:",
                    summary,
                    "\nDetailed content:",
                    content,
                ]
            )

        if not human_draft:
            voice_cues = self._render_voice_cues(plan)
            if voice_cues:
                body.append(voice_cues)

        if plan.angle:
            body.append(f"\nAngle to emphasize: {plan.angle}")
        if plan.call_to_action:
            body.append(f"\nCall to action: {plan.call_to_action}")

        # Adjust final instruction based on post type
        if human_draft and is_promo:
            final_instruction = (
                "\n\n🚨 ФИНАЛЬНАЯ ИНСТРУКЦИЯ:\n"
                "Напиши пост на РУССКОМ языке. Используй 350–450 символов (не меньше!). "
                "Добавь детали: что на сайте, для кого, зачем это нужно. "
                "Лично, без AI-пафоса, но с конкретикой."
            )
        else:
            final_instruction = (
                "\n\n🚨 ФИНАЛЬНАЯ ИНСТРУКЦИЯ:\n"
                "Напиши пост на РУССКОМ языке. МАКСИМУМ 480 символов. "
                "Коротко, лично, без AI-пафоса. Пиши как живой человек, не как корпоративный бот."
            )
        
        return "\n".join(body) + final_instruction

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

        voice_cues = self._render_voice_cues(plan)
        if voice_cues:
            body.append(voice_cues)

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

        voice_cues = self._render_voice_cues(plan)
        if voice_cues:
            lines.append(voice_cues)

        if plan.angle:
            lines.append(f"\nPrimary angle: {plan.angle}")
        if plan.call_to_action:
            lines.append(f"\nDesired CTA: {plan.call_to_action}")

        return "\n".join(lines) + "\n\nProduce the final post only."

    def _render_voice_cues(self, plan: RewritePlan) -> str:
        if not plan.voice_cues:
            return ""

        cues = plan.voice_cues[:3]
        lines = ["\nVoice cues from authentic posts:"]
        for cue in cues:
            summary = cue.get("summary") or cue.get("id") or "Voice cue"
            text = (cue.get("text") or "").strip()
            notes = cue.get("voice_notes")

            if len(text) > 420:
                text = text[:420].rstrip() + "…"

            lines.append(f"- {summary}: {text}")
            if notes:
                lines.append(f"  Notes: {notes}")

        return "\n".join(lines)


