# Rewriter Flexibility & Formatting Design

## Current Issues

1. **Hard-coded formatting logic**: Platform constraints scattered throughout code (lines 660-685)
2. **No validation**: Posts can exceed platform limits without trimming
3. **Inflexible prompt structure**: Prompts are string concatenations, hard to modify
4. **No post-processing**: Raw LLM output goes directly to output
5. **Limited platform support**: Only handles Twitter/Threads/LinkedIn
6. **No formatting templates**: Same structure for all content types

## Proposed Architecture

### 1. Platform Configuration System

Create `config/platform_formats.json`:

```json
{
  "twitter": {
    "name": "Twitter/X",
    "constraints": {
      "max_length": 280,
      "max_thread_tweets": 10,
      "supports_threads": true,
      "supports_markdown": false,
      "supports_hashtags": true,
      "supports_mentions": true
    },
    "formats": {
      "single": {
        "max_chars": 280,
        "structure": "standalone",
        "guidance": "Single tweet: concise, punchy, engaging"
      },
      "thread": {
        "max_chars_per_tweet": 280,
        "min_tweets": 2,
        "max_tweets": 10,
        "numbering_format": "1/\n{content}\n\n2/\n{content}",
        "guidance": "Thread format: each tweet on own line with numbering"
      }
    }
  },
  "threads": {
    "name": "Meta Threads",
    "constraints": {
      "max_length": 500,
      "max_thread_posts": 10,
      "supports_threads": true,
      "supports_markdown": false,
      "supports_hashtags": true,
      "supports_mentions": true
    },
    "formats": {
      "single": {
        "max_chars": 500,
        "structure": "standalone",
        "guidance": "Single post: can be longer, more conversational"
      }
    }
  },
  "linkedin": {
    "name": "LinkedIn",
    "constraints": {
      "max_length": 3000,
      "supports_threads": false,
      "supports_markdown": true,
      "supports_hashtags": true,
      "supports_mentions": true
    },
    "formats": {
      "single": {
        "min_chars": 150,
        "max_chars": 1300,
        "optimal_chars": 600,
        "structure": "professional",
        "guidance": "Professional post: opening hook, body, call-to-action"
      }
    }
  },
  "telegram": {
    "name": "Telegram",
    "constraints": {
      "max_length": 4096,
      "supports_markdown": true,
      "supports_html": true,
      "supports_hashtags": true
    },
    "formats": {
      "single": {
        "max_chars": 4096,
        "structure": "flexible",
        "guidance": "Can use bold, italic, code formatting with Markdown"
      }
    }
  }
}
```

### 2. Formatting Templates

Create `config/format_templates.json`:

```json
{
  "templates": {
    "tech_news_short": {
      "description": "Quick tech news update",
      "applicable_to": ["product_launch", "feature_update"],
      "structure": [
        "{{opening}}",
        "{{key_facts}}",
        "{{insight}}"
      ],
      "max_sections": 3
    },
    "tech_analysis": {
      "description": "Deeper technical analysis",
      "applicable_to": ["trend_analysis", "research_finding"],
      "structure": [
        "{{hook}}",
        "{{data_points}}",
        "{{analysis}}",
        "{{question_or_cta}}"
      ],
      "max_sections": 4
    },
    "funding_news": {
      "description": "Funding announcements",
      "applicable_to": ["funding_news"],
      "structure": [
        "{{headline}}",
        "{{numbers}}",
        "{{context}}",
        "{{implication}}"
      ],
      "max_sections": 4
    }
  }
}
```

### 3. Post-Processing Pipeline

Implement formatting post-processor in `rewriter.py`:

```python
class FormatProcessor:
    """Post-process LLM output to ensure platform compliance"""

    def __init__(self, platform_config):
        self.config = platform_config

    def process(self, content: str, format_type: str = "single") -> Dict[str, Any]:
        """
        Process raw LLM output into platform-compliant format

        Returns:
            {
                "content": formatted_content,
                "format": "single" | "thread",
                "parts": [...],  # For threads
                "warnings": [...],  # If truncated, etc.
                "metadata": {...}
            }
        """
        # 1. Detect if thread or single
        # 2. Validate length
        # 3. Apply platform formatting
        # 4. Trim if needed
        # 5. Add metadata
        pass

    def validate_length(self, content: str, max_length: int) -> bool:
        """Check if content fits platform constraints"""
        pass

    def smart_trim(self, content: str, max_length: int) -> str:
        """Intelligently trim content preserving meaning"""
        # - Try removing trailing questions first
        # - Then trim from end sentence by sentence
        # - Add "..." if truncated
        pass

    def format_thread(self, content: str) -> List[str]:
        """Parse and format thread content"""
        # - Detect thread numbering (1/, 2/, etc.)
        # - Split into parts
        # - Validate each part length
        # - Return list of tweets
        pass
```

### 4. Dynamic Prompt Builder

Create prompt builder system:

```python
class PromptBuilder:
    """Build prompts dynamically from templates"""

    def __init__(self, templates_dir: Path):
        self.templates = self._load_templates(templates_dir)

    def build_rewrite_prompt(
        self,
        persona: Dict,
        platform: str,
        content_type: str,
        examples: List[str],
        format_config: Dict,
        **kwargs
    ) -> str:
        """
        Build prompt from template with platform-specific constraints
        """
        template = self.templates.get('rewrite_russian', self.templates['rewrite_default'])

        return template.format(
            persona_name=persona['name'],
            platform=platform,
            format_guidance=format_config['guidance'],
            max_length=format_config['max_chars'],
            examples=self._format_examples(examples),
            **kwargs
        )
```

### 5. Improved Architecture Flow

```
Input Content
    ↓
[Content Classifier]
    ↓
[Smart Example Selector]
    ↓
[Prompt Builder] ← Platform Config
    ↓
[LLM Call]
    ↓
[Format Processor] ← Platform Config
    ↓
[Length Validator]
    ↓
[Smart Trimmer] (if needed)
    ↓
Output
```

## Implementation Plan

### Phase 1: Configuration Layer (Priority: HIGH)
- [x] Create `config/platform_formats.json`
- [ ] Create `config/format_templates.json`
- [ ] Create `config/prompt_templates/` directory
- [ ] Add platform config loader to rewriter

### Phase 2: Post-Processing (Priority: HIGH)
- [ ] Implement `FormatProcessor` class
- [ ] Add length validation
- [ ] Add smart trimming logic
- [ ] Add thread parsing/formatting
- [ ] Add metadata generation

### Phase 3: Dynamic Prompts (Priority: MEDIUM)
- [ ] Implement `PromptBuilder` class
- [ ] Create prompt templates for Russian/English
- [ ] Migrate existing prompts to templates
- [ ] Add template variable system

### Phase 4: Enhanced Features (Priority: LOW)
- [ ] Add Markdown formatting for platforms that support it
- [ ] Add link shortening
- [ ] Add hashtag suggestions
- [ ] Add image description generation
- [ ] Add preview generation

## Benefits

1. **Maintainability**: All platform rules in one config file
2. **Extensibility**: Add new platforms without code changes
3. **Reliability**: Validation ensures posts never exceed limits
4. **Flexibility**: Templates allow easy prompt modifications
5. **Quality**: Smart trimming preserves meaning when shortening
6. **Testing**: Easy to test each component independently

## Example Usage

```python
# Old way (hard-coded)
if platform == "twitter":
    format_constraint = "Single tweet: <280 chars"

# New way (config-driven)
platform_config = self.platform_configs[platform]
format_config = platform_config['formats'][format_type]
format_constraint = format_config['guidance']

# With post-processing
raw_output = await self._call_llm(prompt)
processor = FormatProcessor(platform_config)
result = processor.process(raw_output, format_type="single")

if result['warnings']:
    logger.warning(f"Post processing warnings: {result['warnings']}")

return {
    "content": result['content'],
    "format": result['format'],
    "metadata": result['metadata']
}
```

## Migration Strategy

1. Keep existing code working
2. Add new config system in parallel
3. Implement post-processor
4. Migrate one platform at a time
5. Add tests for each platform
6. Remove old hard-coded logic once all platforms migrated

## Open Questions

1. Should we support custom format templates per persona?
2. How to handle multi-language formatting differences?
3. Should trimming be aggressive or conservative by default?
4. Do we need A/B testing for different format styles?
