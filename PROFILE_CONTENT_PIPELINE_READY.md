# Profile-Based Content Pipeline - READY

## Summary

Built a **flexible, profile-based content pipeline system** that works for any persona (qronoya, aspandead, or future profiles). All configuration is done through JSON files and managed via UI.

**Status**: ✅ Ready for Use

---

## What Was Built

### 1. Profile Configuration System

**Location**: `config/profiles/`

Each profile has a JSON config with:
- **Basic Info**: Display name, description, voice guidelines
- **Platform Settings**: Which platforms to post to, language per platform, posting frequency
- **Content Types**: Supported content types per platform
- **Prompt Templates**: Platform-specific prompts with placeholders
- **Content Routing**: Rules for routing content based on time sensitivity
- **Source Preferences**: Reddit comment settings, etc.

**Example Profiles**:
- [config/profiles/qronoya.json](config/profiles/qronoya.json) - Threads (RU), Twitter (EN), Telegram (RU)
- [config/profiles/aspandead.json](config/profiles/aspandead.json) - Twitter (EN), Threads (EN)

### 2. ProfileContentPipeline Service

**Location**: [src/services/profile_content_pipeline.py](src/services/profile_content_pipeline.py)

**Features**:
- Load any profile configuration
- Route content to platforms based on time sensitivity
- Select appropriate prompt templates based on platform + content type
- Format prompts with actual content and metadata
- Handle platform-specific constraints (length, markdown, emojis, etc.)
- Prepare content for rewriting

**Key Methods**:
```python
pipeline = ProfileContentPipeline('qronoya')

# Route content based on time sensitivity
platforms = pipeline.route_content('same-day')  # → ['twitter', 'threads', 'telegram']

# Select prompt template
template = pipeline.select_prompt_template('twitter', 'breaking_news')

# Prepare content for rewriting
prepared = pipeline.prepare_content_for_rewrite(
    post=usable_post,
    platform='twitter',
    content_type='breaking_news'
)
```

### 3. Profile Manager UI

**Location**: [src/web/components/profile_manager_tab.py](src/web/components/profile_manager_tab.py)

**Features**:
- **List Profiles**: See all available profiles
- **Edit Profile**: 5 tab interface for editing:
  - Basic Info (name, description, voice guidelines)
  - Platform Settings (enable/disable platforms, language, frequency, content types)
  - Prompt Templates (view/edit/add templates)
  - Content Routing (configure routing rules)
  - Test Pipeline (test routing and prompt selection)
- **Create New Profile**: Form to create new profiles from UI

**Access**: Navigate to "👤 Profiles" tab in Streamlit UI

---

## How It Works

### Profile Configuration Structure

```json
{
  "profile_key": "qronoya",
  "display_name": "Qronoya",
  "description": "Technical analyst...",

  "platforms": {
    "twitter": {
      "enabled": true,
      "language": "en",
      "content_types": ["breaking_news", "insight_thread"],
      "format_preferences": {
        "max_length": 280,
        "use_emojis": false
      }
    }
  },

  "content_routing": {
    "same-day": {
      "platforms": ["twitter", "threads"],
      "priority_order": ["twitter", "threads"]
    }
  },

  "prompt_templates": {
    "twitter_en_breaking_news": "You are {profile_name}...\n{source_content}\n..."
  }
}
```

### Content Flow

```
usable_posts (Supabase)
     ↓
ProfileContentPipeline.select_posts_for_rewrite()
     ↓
Route to platforms based on relevance_window
     ↓
Select appropriate prompt template
     ↓
Format prompt with content + metadata
     ↓
Send to rewriter
     ↓
Schedule for publishing
     ↓
Publisher Worker → Platform
```

### Prompt Template Placeholders

Templates use these placeholders that get filled automatically:
- `{profile_name}` - Profile display name
- `{profile_key}` - Profile identifier
- `{source_content}` - Original post content
- `{category}` - Content category
- `{topics}` - Topics list
- `{key_concepts}` - Key concepts
- `{voice_russian}` - Russian voice guidelines
- `{voice_english}` - English voice guidelines
- `{voice_general}` - General voice guidelines

---

## Usage Examples

### Test the Pipeline

```bash
python src/services/profile_content_pipeline.py
```

### Use in Code

```python
from src.services.profile_content_pipeline import ProfileContentPipeline

# Initialize for a profile
pipeline = ProfileContentPipeline('qronoya')

# Get routing platforms
platforms = pipeline.route_content('same-day')
# → ['twitter', 'threads', 'telegram']

# Prepare content for rewriting
post = {
    'content': 'AI news...',
    'category': 'tech_trend',
    'tags': ['ai', 'ml'],
    ...
}

prepared = pipeline.prepare_content_for_rewrite(
    post=post,
    platform='twitter',
    content_type='breaking_news'
)

# prepared contains:
# - prompt: Formatted prompt ready for LLM
# - constraints: Platform constraints (max_length, etc.)
# - metadata: All post metadata
```

### Manage Profiles from UI

1. Open Streamlit: `http://localhost:8501`
2. Navigate to **"👤 Profiles"** tab
3. Select a profile to edit
4. Use the 5 sub-tabs to configure:
   - Basic Info
   - Platforms
   - Prompts
   - Routing
   - Test

---

## Key Features

### ✅ Flexible & Extensible

- Works with **any profile** - not hardcoded to qronoya
- Add new profiles through UI or by creating JSON files
- Each profile has independent configuration

### ✅ Platform-Specific Prompts

- Different prompts for:
  - **Platform**: twitter, threads, telegram, etc.
  - **Language**: en, ru, etc.
  - **Content Type**: tech_news, breaking_news, tutorial, etc.

Example: `twitter_en_breaking_news` vs `threads_ru_tech_news` vs `telegram_ru_deep_analysis`

### ✅ Smart Content Routing

- Routes content based on time sensitivity:
  - `same-day` → Twitter (EN) first, then Threads (RU), then Telegram (RU)
  - `24-72h` → Threads (RU), then Twitter (EN)
  - `this-week` → Telegram (RU), then Threads (RU)
  - `evergreen` → Telegram (RU) only

- Priority order configurable per profile

### ✅ Language Support

- Each platform can have its own language
- Example: Qronoya posts to:
  - Twitter in **English**
  - Threads in **Russian**
  - Telegram in **Russian**

### ✅ Platform Constraints

- Max length per platform
- Markdown support (Telegram)
- Emojis enabled/disabled
- Hashtags enabled/disabled
- Thread support

---

## Next Steps

### Immediate (To Complete Pipeline)

1. **Build Content Selector** - Query `usable_posts` for posts ready to rewrite
2. **Integrate with Rewriter** - Connect pipeline to existing rewriter
3. **Add Scheduling** - Schedule prepared content for publishing
4. **Reddit Comment Extraction** - Enrich Reddit posts with top comments

### Near Future

1. **Batch Processing** - Process multiple posts at once
2. **Analytics Dashboard** - Track performance per profile/platform
3. **A/B Testing** - Test different prompts and track results
4. **Auto-Learning** - Adjust prompts based on engagement

---

## Files Created

- [config/profiles/qronoya.json](config/profiles/qronoya.json) - Qronoya profile config
- [config/profiles/aspandead.json](config/profiles/aspandead.json) - Aspandead profile config
- [src/services/profile_content_pipeline.py](src/services/profile_content_pipeline.py) - Pipeline service
- [src/web/components/profile_manager_tab.py](src/web/components/profile_manager_tab.py) - UI for managing profiles
- [config/qronoya_prompts.json](config/qronoya_prompts.json) - Reference prompt templates (can be moved to profile configs)
- [docs/QRONOYA_CONTENT_PIPELINE.md](docs/QRONOYA_CONTENT_PIPELINE.md) - Architecture documentation

---

## Configuration Reference

### Platform Options

- `twitter` - Twitter/X
- `threads` - Meta Threads
- `telegram` - Telegram Channel
- `instagram` - Instagram
- `linkedin` - LinkedIn

### Language Options

- `en` - English
- `ru` - Russian

### Content Type Examples

- **Tech**: `tech_news`, `ai_discussion`, `tool_review`, `dev_insight`
- **Design**: `design_news`, `creative_insight`, `tool_showcase`
- **Formats**: `breaking_news`, `insight_thread`, `tutorial_guide`, `deep_analysis`, `weekly_roundup`

### Time Sensitivity Values

- `same-day` - Breaking news, urgent content
- `24-72h` - Recent trending content
- `this-week` - Weekly updates
- `evergreen` - Timeless content

---

**Created**: 2025-11-09
**Status**: ✅ Ready for Integration
