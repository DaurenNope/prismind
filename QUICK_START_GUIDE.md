# Quick Start Guide - Self-Improving Voice System

## What You Have Now

A complete self-improving voice system that learns from your corrections to continuously improve Qronoya persona voice matching.

---

## 3 Commands You Need

### 1. Test the System (First Time)
```bash
python demo_full_correction_workflow.py
```

**What it does**:
- Creates sample correction data
- Tests pattern extraction
- Validates the complete workflow
- Shows you what the system learned

**Result**: You'll see learned patterns from 5 sample corrections

---

### 2. Start Collecting Real Corrections (Daily Use)
```bash
python demo_review_and_correct.py
```

**What it does**:
- Generates 2 Gemini rewrites from sample posts
- Shows you each rewrite
- You choose: ✅ Approve / ✏️ Edit / ❌ Reject / ⏭️ Skip / 🛑 Quit
- If Edit: Opens your editor (nano/vim/code) for corrections
- Logs everything to `training_data/corrections/`

**Goal**: Collect 10-20 corrections to start seeing patterns

---

### 3. Analyze Your Corrections (After 10-20 Corrections)
```bash
python scripts/update_voice_model.py
```

**What it does**:
- Loads all your corrections
- Analyzes vocabulary, structure, tone patterns
- Generates recommendations
- Saves learned patterns

**Result**: You'll see what words you consistently add/remove, structure preferences, and approval rate

---

## Your Daily Workflow

**Week 1-2: Learn the Basics**
```bash
# Day 1-3: Test with sample data
python demo_full_correction_workflow.py

# Day 4-14: Start correcting real rewrites (5-10 per day)
python demo_review_and_correct.py

# Every few days: Check what system learned
python scripts/update_voice_model.py
```

**Week 3-8: Build Training Dataset**
```bash
# Continue daily corrections
python demo_review_and_correct.py  # 5-10 corrections per day

# Weekly: Review patterns
python scripts/update_voice_model.py
```

**After 200+ Corrections: Ready for Fine-Tuning**
- You'll have a high-quality training dataset
- Can fine-tune local model (Qwen 2.5 7B)
- No more API costs

---

## What to Expect

### After 5-10 Corrections
You'll see basic patterns:
- Words you consistently remove (forced slang)
- Words you consistently add (natural vocabulary)
- Structure preferences (threads vs single posts)

### After 50 Corrections
Clear patterns emerge:
- Voice consistency across topics
- Approval rate trends
- Tone preferences

### After 200+ Corrections
Ready for fine-tuning:
- Dataset large enough for model training
- Consistent voice patterns
- Can train local model to replace Gemini API

---

## Files to Know

### Logs Your Work
- `training_data/corrections/` - All your corrections (JSONL format)
- `training_data/approved/` - Rewrites you approved (JSON format)
- `training_data/learned_patterns/` - What system learned (JSON format)

### Scripts You Run
- `demo_review_and_correct.py` - Interactive review interface
- `scripts/update_voice_model.py` - Pattern extraction
- `demo_full_correction_workflow.py` - Test workflow

---

## Tips

### Setting Your Editor
If you want a specific editor for corrections:
```bash
# Use nano (default)
export EDITOR=nano

# Use vim
export EDITOR=vim

# Use VS Code
export EDITOR=code
```

### Reviewing Your Corrections
All corrections are saved in JSONL files:
```bash
# View today's corrections
cat training_data/corrections/2025-11-04_corrections.jsonl | jq
```

### Checking Learned Patterns
```bash
# View learned patterns
cat training_data/learned_patterns/qronoya_learned_patterns.json | jq
```

---

## Current Status

### ✅ What's Working
- Gemini API integration (free tier: 200 requests/day)
- Two-stage pipeline (Qwen idea extraction → Gemini Russian writing)
- Interactive review interface
- Pattern extraction from corrections
- Automatic recommendation generation

### 🎯 Next Steps
1. **Immediate**: Start collecting real corrections (target: 50)
2. **Short-term**: Build dataset of 200+ corrections
3. **Long-term**: Fine-tune local model and eliminate API costs

---

## Cost

**Current**: $0/month (Gemini free tier)
**After fine-tuning**: $0-10/month (local or cloud GPU)

---

## Questions?

Check the full documentation:
- [SELF_IMPROVING_VOICE_SYSTEM_COMPLETE.md](SELF_IMPROVING_VOICE_SYSTEM_COMPLETE.md) - Complete system documentation
- [GEMINI_INTEGRATION_COMPLETE.md](GEMINI_INTEGRATION_COMPLETE.md) - Gemini API integration details
- [QRONOYA_VOICE_UPDATE_COMPLETE.md](QRONOYA_VOICE_UPDATE_COMPLETE.md) - Voice pattern updates

---

Last updated: 2025-11-04
