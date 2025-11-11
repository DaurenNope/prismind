# Aspandead Rewriter Quality Issues - Root Cause & Fix

## Problem Statement

Aspandead rewrites are **awful** - they sound academic and analytical instead of raw, vulnerable, and literary.

### Bad Example Output:
```
Труднее всего в расставании – не сам разрыв. А момент, когда до тебя доходит,
что бывший уже живет дальше, а ты все еще оплакиваешь то, что было.
Исследования показывают, что боль осознания часто сильнее, чем боль прощания.
```

**Issues**:
- "Исследования показывают" (Research shows) - too academic
- Analytical tone, explaining feelings
- Missing raw emotional authenticity

### What It Should Sound Like:
```
Худшее в расставании — не сам разрыв. Это момент, когда ты понимаешь,
что им уже все равно, а ты все ещё истекаешь кровью. Они уже живут дальше,
а ты застрял в том, что было. Больно пиздец.
```

**Good qualities**:
- Raw emotion ("истекаешь кровью", "больно пиздец")
- Vulnerable, not analytical
- Literary without being academic
- Feels like confession, not explanation

## Root Cause

Found in [src/publishing/rewriter.py:1056-1062](src/publishing/rewriter.py#L1056-L1062):

```python
GUIDELINES:
- Platform: {platform} ({format_constraint})
- Write in RUSSIAN language (professional tech account)  # ❌ WRONG
- Audience: {target_audience}
- Be yourself - knowledgeable but approachable  # ❌ WRONG for aspandead
- Add your perspective and analysis, not just facts  # ❌ WRONG
- NO emojis, NO hashtags
```

This prompt was **hardcoded for qronoya** (professional tech account, analytical, add analysis), but it's used for **ALL Russian personas** including aspandead!

### Why This Fails for Aspandead

**Aspandead persona traits** (from `config/personas/aspandead.json`):
- "Deep raw vulnerability without filters"
- "Literary writer who captures universal human pain"
- "Anonymous soul's garbage disposal"
- "Poetic but not pretentious"
- "Writes from lived experience, not research"

**What the old prompt tells it**:
- "Be knowledgeable and approachable" → sounds like a therapist
- "Add your perspective and analysis" → sounds like a blog post
- "Professional tech account" → wrong persona entirely

## The Fix

### Changed From:
```python
GUIDELINES:
- Platform: {platform} ({format_constraint})
- Write in RUSSIAN language (professional tech account)
- Audience: {target_audience}
- Be yourself - knowledgeable but approachable
- Add your perspective and analysis, not just facts
- NO emojis, NO hashtags
```

### Changed To:
```python
GUIDELINES:
- Platform: {platform} ({format_constraint})
- Write in RUSSIAN language
- Audience: {target_audience}
- Voice traits: {', '.join(persona_info.get('traits', [])[:3])}
- NO emojis, NO hashtags
```

Now it pulls the **actual persona traits** from the config:
- **Qronoya**: "Technical expert", "Thoughtful analyst", "Curious observer"
- **Aspandead**: "Deep raw vulnerability", "Literary writer", "Emotional honesty"

## Files Modified

1. **[src/publishing/rewriter.py:1056-1062](src/publishing/rewriter.py#L1056-L1062)**
   - Removed hardcoded qronoya-specific instructions
   - Now uses dynamic `persona_info.get('traits')` instead
   - Applies correct voice for each persona

## Testing

### Before Fix:
```
Aspandead output: "Исследования показывают, что боль осознания часто сильнее"
❌ Academic, analytical, mentioning research
```

### After Fix (Expected):
```
Aspandead output: Raw, vulnerable, literary - like the voice examples:
"Иногда любви недостаточно. Иногда два человека могут глубоко заботиться
друг о друге и всё равно не подходить."
```

## Impact

### Who This Affects:
- ✅ **Aspandead**: CRITICAL FIX - was completely broken
- ✅ **Qronoya**: Should improve (uses actual traits instead of hardcoded text)
- ✅ **Any future Russian personas**: Will automatically use correct traits

### What Improves:
1. **Aspandead rewrites sound authentic** - raw, vulnerable, literary
2. **Qronoya stays professional** - traits specify analytical/technical
3. **System is more maintainable** - no hardcoded persona assumptions
4. **Better prompt hygiene** - one prompt template adapts to all personas

## Why the Tests Showed Old Behavior

The test logs showed "Using TWO-STAGE pipeline: Qwen extraction → Vikhr writing" but the code says "Gemini extraction → Gemini writing".

This suggests:
1. **Python bytecode cache** - old `.pyc` files with old code
2. **Import cache** - Python cached old module in memory
3. **Running old version** - tests might be using different code path

**Solution**: Clear caches and restart:
```bash
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

## Next Steps

1. ✅ **Fix applied** - Updated prompt to use dynamic persona traits
2. ⏳ **Testing blocked** - Gemini rate limit hit
3. **Wait and test** - Test aspandead output after rate limit resets
4. **Verify fix** - Run `python test_aspandead_single.py`
5. **Check for**:
   - No academic language ("исследования показывают", "анализ")
   - Raw emotional language ("больно", "пиздец", "истекаешь кровью")
   - Literary but authentic voice

## Expected Outcome

Aspandead should now produce content like:

```
Труднее всего в расставании – не сам разрыв. А момент осознания. Когда понимаешь,
что им уже плевать, а ты все ещё чувствуешь все это. Они живут дальше.
А ты застрял. Больно до невозможности.
```

**Characteristics**:
- ✅ Short, punchy sentences
- ✅ Raw emotional truth
- ✅ Literary rhythm without being academic
- ✅ Feels like confession in darkness
- ✅ No research references, no analysis
- ❌ No emojis, no hashtags
- ❌ No corporate/helpful tone

---

**Status**: ✅ Fix Applied, ⏳ Testing Pending (Rate Limit)
**Priority**: CRITICAL - Aspandead was completely unusable before
**Generated**: 2025-11-07
