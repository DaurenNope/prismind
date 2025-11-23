# Qronoya Content Pipeline Architecture

## Overview

Automated content pipeline for **Qronoya** persona across 3 platforms with platform-specific adaptations.

**Status**: 🚧 In Development

---

## Platform Strategy

### 1. Threads (Russian)
**Language**: Russian
**Style**: Conversational, analytical, tech-focused
**Format**: Single posts (up to 500 chars) or short threads
**Tone**: Professional but accessible, "думаю вслух" style
**Line Breaks**: Frequent (`\n\n`) for readability

**Content Types**:
- Tech trend analysis
- Tool/product reviews
- Development insights
- Industry observations

---

### 2. Twitter (English)
**Language**: English
**Style**: Punchy, direct, insightful
**Format**: Single tweets (280 chars) or threads
**Tone**: Technical expert, concise
**Line Breaks**: Minimal (Twitter threads use numbered format)

**Content Types**:
- Breaking tech news
- Quick insights
- Tool comparisons
- Hot takes on industry trends

---

### 3. Telegram Channel (Russian)
**Language**: Russian
**Style**: Detailed, formatted, in-depth
**Format**: Long-form (up to 4096 chars)
**Tone**: Analytical, comprehensive
**Markdown**: Enabled (**bold**, *italic*, `code`, [links])

**Content Types**:
- Detailed analysis
- Tutorials/guides
- Weekly roundups
- Deep dives on tools/frameworks

---

## Content Source: `usable_posts` Table

### Selection Criteria

Pull posts from `usable_posts` where:
- `best_persona_key = 'qronoya'`
- `rewrite_readiness IN ('excellent', 'good')`
- `quality_score >= 7.0`
- `value_score >= 7.0`

### Content Type Mapping

| Source Category | Threads (RU) | Twitter (EN) | Telegram (RU) |
|-----------------|--------------|--------------|---------------|
| `tech_trend` | ✅ Analysis | ✅ Hot take | ✅ Deep dive |
| `tool_review` | ✅ Opinion | ✅ Comparison | ✅ Tutorial |
| `ai_news` | ✅ Summary | ✅ Breaking | ✅ Analysis |
| `dev_insight` | ✅ Thought | ✅ Tip | ✅ Guide |
| `industry_analysis` | ✅ Take | ❌ Skip | ✅ Long-form |

### Time Sensitivity Routing

| Relevance Window | Platform Priority |
|------------------|-------------------|
| `same-day` | Twitter (EN) → Threads (RU) → Telegram (RU) |
| `24-72h` | Threads (RU) → Twitter (EN) |
| `this-week` | Telegram (RU) → Threads (RU) |
| `evergreen` | Telegram (RU) only |

---

## Platform-Specific Prompts

### Prompt Structure

Each platform needs distinct prompt templates based on:
1. **Language** (RU vs EN)
2. **Content Type** (news, tutorial, opinion, etc.)
3. **Format** (single post, thread, long-form)
4. **Source Platform** (Reddit, Twitter, HN, etc.)

### Prompt Template Categories

**For Threads (RU)**:
- `threads_ru_news` - Tech news analysis
- `threads_ru_opinion` - Personal take on tools/trends
- `threads_ru_review` - Product/tool review
- `threads_ru_insight` - Development insight

**For Twitter (EN)**:
- `twitter_en_breaking` - Breaking news (single tweet)
- `twitter_en_thread` - Multi-tweet thread
- `twitter_en_insight` - Quick technical insight
- `twitter_en_comparison` - Tool/tech comparison

**For Telegram (RU)**:
- `telegram_ru_analysis` - Deep analysis with formatting
- `telegram_ru_tutorial` - How-to guide
- `telegram_ru_roundup` - Weekly/topic roundup
- `telegram_ru_deepdive` - Long-form exploration

---

## Reddit Comment Integration

### Special Handling

**Problem**: Reddit posts have valuable discussions in comments that add context.

**Solution**:
1. Extract top comments (by upvotes) from Reddit posts
2. Include comment insights in the rewrite prompt
3. Add "Discussion highlights" section for Telegram
4. Use comment perspectives to enrich analysis

### Implementation

```python
def prepare_reddit_content(post):
    """
    Enhance Reddit post with comment context
    """
    content = {
        'main_post': post['content'],
        'comments_summary': extract_top_comments(post),
        'discussion_themes': identify_themes(post['comments']),
        'community_reaction': sentiment_from_comments(post['comments'])
    }
    return content
```

**Prompt Addition for Reddit**:
```
COMMUNITY DISCUSSION:
The Reddit community discussed:
- [Top insight from comment 1]
- [Top insight from comment 2]
- [Top insight from comment 3]

Overall sentiment: [positive/mixed/critical]
```

---

## Pipeline Flow

```
┌─────────────────────────────────────┐
│    Usable Posts (Supabase)          │
│  • best_persona_key = 'qronoya'    │
│  • quality_score >= 7.0             │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   Content Selection Agent           │
│  • Filter by time sensitivity       │
│  • Check if already rewritten       │
│  • Prioritize by rewrite_score      │
└─────────────────┬───────────────────┘
                  │
                  ▼
┌─────────────────────────────────────┐
│   Platform Router                   │
│  • same-day → Twitter EN            │
│  • 24-72h → Threads RU              │
│  • this-week+ → Telegram RU         │
└─────────────────┬───────────────────┘
                  │
        ┌─────────┼─────────┐
        ▼         ▼         ▼
┌──────────┐ ┌──────────┐ ┌──────────┐
│ Threads  │ │ Twitter  │ │ Telegram │
│ Rewriter │ │ Rewriter │ │ Rewriter │
│   (RU)   │ │   (EN)   │ │   (RU)   │
└─────┬────┘ └─────┬────┘ └─────┬────┘
      │            │            │
      └────────────┼────────────┘
                   ▼
        ┌─────────────────────┐
        │  Scheduling Queue   │
        │  • Priority-based   │
        │  • Time-windowed    │
        └─────────┬───────────┘
                  ▼
        ┌─────────────────────┐
        │  Platform Publisher │
        │  • Threads poster   │
        │  • Twitter poster   │
        │  • Telegram poster  │
        └─────────────────────┘
```

---

## Prompt Engineering Strategy

### Core Principles

1. **Language-First**: RU prompts written in Russian, EN prompts in English
2. **Platform-Aware**: Each prompt knows platform constraints
3. **Content-Type Specific**: Different prompts for news vs tutorial vs opinion
4. **Source-Aware**: Special handling for Reddit (comments), Twitter (threads), HN (discussion)

### Example: Threads RU - Tech News

```python
THREADS_RU_NEWS_PROMPT = """Ты — Qronoya, технический аналитик.

ЗАДАЧА: Перепиши эту новость для Threads на русском языке.

ИСХОДНЫЙ МАТЕРИАЛ:
{source_content}

ТВОЙ СТИЛЬ:
- Пишешь на русском
- Аналитически, но доступно
- "Думаешь вслух", делишься инсайтами
- Добавляешь контекст: почему это важно, что это значит

ФОРМАТ THREADS:
- Максимум 500 символов
- Частые переносы строк (\\n\\n) для читаемости
- Без эмодзи и хештегов (только текст)
- Структура: Новость → Твой анализ → Вывод

ВАЖНО:
- НЕ просто пересказывай, а АНАЛИЗИРУЙ
- Добавь контекст: "Это интересно, потому что..."
- Объясни значение для индустрии

Напиши пост:"""
```

### Example: Twitter EN - Breaking News

```python
TWITTER_EN_BREAKING_PROMPT = """You are Qronoya, a technical analyst.

TASK: Rewrite this breaking news for Twitter in English.

SOURCE:
{source_content}

YOUR STYLE:
- Technical but accessible
- Punchy, direct
- No fluff, straight to insights

TWITTER FORMAT:
- Max 280 characters (STRICT)
- Single tweet format
- No emojis, no hashtags
- Structure: News → Why it matters (1 sentence)

CRITICAL:
- Must be under 280 characters
- Focus on IMPACT, not just facts
- Add ONE insight that's not obvious

Write the tweet:"""
```

### Example: Telegram RU - Deep Analysis

```python
TELEGRAM_RU_ANALYSIS_PROMPT = """Ты — Qronoya, технический аналитик.

ЗАДАЧА: Напиши подробный анализ для Telegram-канала на русском.

ИСХОДНЫЙ МАТЕРИАЛ:
{source_content}

ТВОЙ СТИЛЬ:
- Глубокий технический анализ
- Структурированный текст
- Используй форматирование Markdown

ФОРМАТ TELEGRAM:
- До 4000 символов
- Используй **жирный**, *курсив*, `код`
- Частые переносы для читаемости
- Структура:
  1. Суть (2-3 предложения)
  2. Контекст и анализ (основная часть)
  3. Выводы и последствия

MARKDOWN ИНСТРУКЦИИ:
- Важные термины: **жирным**
- Акценты: *курсивом*
- Код/команды: `моноширинным`
- Ссылки: [текст](url)

ВАЖНО:
- Добавь глубину: почему, как, что дальше
- Используй примеры и сравнения
- Объясни технические детали доступно

Напиши анализ:"""
```

---

## Implementation Files

### 1. Platform Prompt Config

**File**: `config/qronoya_prompts.json`

Structure:
```json
{
  "threads_ru": {
    "news": "...",
    "opinion": "...",
    "review": "...",
    "insight": "..."
  },
  "twitter_en": {
    "breaking": "...",
    "thread": "...",
    "insight": "...",
    "comparison": "..."
  },
  "telegram_ru": {
    "analysis": "...",
    "tutorial": "...",
    "roundup": "...",
    "deepdive": "..."
  }
}
```

### 2. Content Pipeline Service

**File**: `src/services/qronoya_content_pipeline.py`

**Key Methods**:
- `select_posts_for_rewrite()` - Query usable_posts for qronoya
- `route_to_platform()` - Determine platform based on time sensitivity
- `prepare_content()` - Add Reddit comments if needed
- `select_prompt_template()` - Choose prompt based on platform + content_type
- `rewrite_for_platform()` - Call rewriter with platform-specific prompt
- `schedule_post()` - Add to publishing queue

### 3. Reddit Comment Extractor

**File**: `src/services/reddit_comment_processor.py`

**Key Methods**:
- `extract_top_comments(post_id, limit=5)` - Get top comments by upvotes
- `summarize_discussion()` - Extract key themes from comments
- `get_community_sentiment()` - Overall reaction (positive/critical/mixed)

---

## Next Steps

1. ✅ Create prompt templates for all 9 combinations (3 platforms × 3 main content types)
2. ⏳ Build `QronoyaContentPipeline` service
3. ⏳ Implement Reddit comment integration
4. ⏳ Test with sample posts from `usable_posts`
5. ⏳ Add scheduling logic
6. ⏳ Connect to existing publisher worker

---

**Created**: 2025-11-09
**Status**: 🚧 In Development
