# Publishing Workflow - PRODUCTION READY ✅

**Date**: 2025-11-04
**Status**: Ready for daily use
**Database**: 673 posts ready to rewrite & publish

---

## What's Ready

You now have a complete workflow to rewrite your 673 database posts and publish them with language routing:

- **Threads → Russian** (Qronoya persona)
- **Twitter → English** (Qronoya persona)
- **Telegram → Russian** (Qronoya persona, future)

---

## The Workflow

### 1. Review & Publish from Database

**Command**:
```bash
python review_and_publish_from_database.py --limit 5
```

**What happens**:
1. Pulls 5 posts from your database (673 available)
2. Rewrites each with correct language routing
3. Shows you each rewrite in the terminal
4. You choose: ✅ Approve / ✏️ Edit / ❌ Reject / ⏭️ Skip / 🛑 Quit
5. If you edit: Opens your editor (nano/vim/code)
6. Approved posts get scheduled for publishing
7. System logs corrections for learning

---

## Daily Workflow

### Morning: Review & Schedule Posts (10-20 minutes)

```bash
# Review 5 posts from Threads
python review_and_publish_from_database.py --limit 5 --platform threads

# Review 5 posts from Twitter
python review_and_publish_from_database.py --limit 5 --platform twitter

# Review 5 posts from Reddit (rewrites for Threads in Russian)
python review_and_publish_from_database.py --limit 5 --platform reddit
```

**Result**: 15 posts reviewed, approved/corrected, and scheduled

---

### Check Scheduled Posts

```bash
python review_and_publish_from_database.py --show-schedule
```

Shows all scheduled posts with timing and priority.

---

### Weekly: Analyze Patterns

After you've reviewed 20-30 posts:

```bash
python scripts/update_voice_model.py
```

System analyzes your corrections and shows what it learned.

---

## Language Routing

The system automatically routes languages:

| Source Platform | Output Platform | Language | Persona |
|----------------|-----------------|----------|---------|
| Threads | Threads | **Russian** | Qronoya |
| Twitter | Twitter | **English** | Qronoya |
| Reddit | Threads | **Russian** | Qronoya |
| Telegram | Telegram | **Russian** | Qronoya |

**Why Reddit → Threads (Russian)?**
- Your Threads audience is Russian-speaking
- Reddit has good English content that can be rewritten for Threads
- Maximizes content for your primary platform

---

## Interactive Review Options

When reviewing each post, you have 5 options:

### 1. ✅ Approve
- Use the rewrite as-is
- Schedules for publishing
- Logs as approved (for training)

### 2. ✏️ Edit
- Opens your editor (nano/vim/code)
- You fix the rewrite
- System learns from your changes
- Schedules your corrected version
- Logs differences (words added/removed, structure changes)

### 3. ❌ Reject
- Don't use this rewrite
- Ask you why (helps improve system)
- Logs rejection reason

### 4. ⏭️ Skip
- Review later
- Post stays in database

### 5. 🛑 Quit
- Exit review session
- Shows summary stats

---

## What Gets Saved

### Scheduled Posts (`scheduled_posts/`)
Ready-to-publish posts with:
- Rewritten content
- Platform & language
- Scheduled time
- Priority
- Source post reference

**Format**: `{platform}_{YYYYMMDD_HHMMSS}.json`

### Corrections (`training_data/corrections/`)
Your edits for learning:
- Original Gemini output
- Your correction
- Words added/removed
- Structure changes (thread format, etc.)
- Length ratios

**Format**: `YYYY-MM-DD_corrections.jsonl`

### Approved Rewrites (`training_data/approved/`)
Rewrites you approved without changes:
- For fine-tuning dataset
- Shows what Gemini got right

**Format**: `qronoya_approved_NNN.json`

---

## Examples

### Example 1: Threads Post (Russian)

**Original (from database)**:
```
Chinese AI startups: 1/6th of US funding, bad press, sanctions. But after
using Manus AI, Deepseek, I think the US is in trouble.
```

**Gemini Rewrite (Russian)**:
```
Китайские ИИ стартапы получают в 6 раз меньше финансирования чем американские.
Плюс негатив в медиа и санкции.

Но протестировал Manus AI и Deepseek - конкурентный продукт за копейки.
При таком темпе Китай может обогнать США в AI.
```

**Your Choice**: ✅ Approve or ✏️ Edit

---

### Example 2: Twitter Post (English)

**Original (from database)**:
```
Career advice: How to transition to senior developer roles. Take ownership,
mentor juniors, think architecture.
```

**Gemini Rewrite (English)**:
```
Moving to senior roles? Three things matter:

1. Take ownership of projects before being asked
2. Mentor junior devs (teaches you to think architecturally)
3. Think systems, not just features

The title comes from consistently doing #1-3.
```

**Your Choice**: ✅ Approve or ✏️ Edit

---

### Example 3: Reddit → Threads (Russian)

**Original (Reddit post)**:
```
[Reddit discussion about AI coding assistants]
Cursor is amazing for code generation. Windsurf is catching up.
Cline is decent too.
```

**Gemini Rewrite (Russian for Threads)**:
```
Протестировал несколько AI ассистентов для кода.

Cursor - лидер, генерация кода офигительная. Windsurf набирает обороты,
единственный реальный конкурент. Cline тоже норм.

Кто чем пользуется?
```

**Your Choice**: ✅ Approve or ✏️ Edit (maybe remove "офигительная" if too forced)

---

## Scheduling Logic

Posts are scheduled based on priority:

- **High priority** (80-100): Post within 0-5 minutes
- **Medium priority** (50-79): Post within 2-8 hours
- **Low priority** (0-49): Post within 8-24 hours

Priority is calculated from:
- Viral potential (from analyzer)
- Time sensitivity (breaking/trending/timely/evergreen)
- Trend relevance (emerging/mainstream/declining)

---

## Command Reference

### Review Posts
```bash
# Review 5 posts (default)
python review_and_publish_from_database.py

# Review 10 posts
python review_and_publish_from_database.py --limit 10

# Review only Threads posts
python review_and_publish_from_database.py --platform threads

# Review only Twitter posts
python review_and_publish_from_database.py --platform twitter

# Review only Reddit posts (→ Threads Russian)
python review_and_publish_from_database.py --platform reddit
```

### Check Schedule
```bash
# Show scheduled posts
python review_and_publish_from_database.py --show-schedule
```

### Analyze Learning
```bash
# After 20-30 corrections
python scripts/update_voice_model.py
```

---

## Setting Your Editor

Default is `nano`. To use a different editor:

```bash
# Use vim
export EDITOR=vim

# Use VS Code
export EDITOR=code

# Use Sublime
export EDITOR=subl
```

Add to your `~/.bashrc` or `~/.zshrc` to make permanent.

---

## Statistics

### Your Database
- **673 posts** ready to rewrite
- **44 from Threads** (will rewrite in Russian)
- **26 from Twitter** (will rewrite in English)
- **29 from Reddit** (will rewrite for Threads in Russian)

### Gemini API Limits
- **Free tier**: 200 requests/day
- **Rate limit**: 15 requests per minute
- **Cost**: $0

### Suggested Pace
- **Daily**: 15-20 posts reviewed (10-15 minutes)
- **Weekly**: 100-140 posts
- **Month 1**: 400-600 posts completed
- **After 200 reviews**: System learns your patterns
- **After 1000 reviews**: Ready for fine-tuning

---

## What Happens Next

### Week 1-2: Learn the System
- Review 5-10 posts daily
- Get comfortable with approval/editing
- System starts learning your patterns

### Week 3-4: Build Training Dataset
- Review 15-20 posts daily
- Run `update_voice_model.py` weekly
- Check what system is learning

### Month 2: Scale Up
- Database posts getting rewritten
- Corrections feeding into learning
- Voice model improving

### Month 3-4: Fine-Tuning Ready
- 200+ corrections collected
- Consistent voice patterns detected
- Ready to fine-tune local model

### Month 5+: Full Automation
- Fine-tuned local model deployed
- Zero API costs
- Instant rewrites
- Package as service

---

## Files Created

| File | Purpose |
|------|---------|
| [review_and_publish_from_database.py](review_and_publish_from_database.py) | Main workflow - review database posts |
| [production_rewrite_and_schedule.py](production_rewrite_and_schedule.py) | Batch processing (for later automation) |
| [scripts/update_voice_model.py](scripts/update_voice_model.py) | Pattern extraction & learning |
| [demo_review_and_correct.py](demo_review_and_correct.py) | Practice with sample posts |

---

## Troubleshooting

### Issue: Editor not opening
**Solution**: Set `EDITOR` environment variable:
```bash
export EDITOR=nano  # or vim, code, etc.
```

### Issue: Gemini API error
**Solution**: Check `.env` has correct `GEMINI_API_KEY`

### Issue: No posts found
**Solution**: Check database connection:
```bash
python -c "from src.storage.db import StorageFacade; db = StorageFacade(); print(len(db.get_posts(limit=10)))"
```

### Issue: Import error
**Solution**: Reddit extractor had indentation issue, already fixed

---

## Next Steps

### Start Today
```bash
# Review your first 5 posts
python review_and_publish_from_database.py --limit 5
```

### This Week
- Review 5-10 posts daily
- Get comfortable with the workflow
- Start building correction dataset

### This Month
- Review 15-20 posts daily
- Run `update_voice_model.py` weekly
- Watch system learn your voice

---

## Summary

✅ **Database**: 673 posts ready to rewrite
✅ **Language routing**: Threads/Telegram→Russian, Twitter→English
✅ **Interactive review**: Approve, edit, or reject each rewrite
✅ **Correction logging**: System learns from your edits
✅ **Scheduling**: Smart priority-based scheduling
✅ **Pattern extraction**: Analyzes your voice patterns
✅ **Zero cost**: Gemini free tier (200/day)

**Status**: PRODUCTION READY - Start reviewing today! 🚀

---

Last updated: 2025-11-04
