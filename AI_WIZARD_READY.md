# 🧙 AI Profile Wizard - READY TO TEST

## What We Built

The **AI Profile Onboarding Wizard** - the "sellable feature" that converts profile setup from a technical manual process into a 10-minute conversational experience.

## Key Features

### 1. **Conversational Interview**
- 4-step guided conversation
- Natural language (no technical jargon)
- Progressive disclosure (one question at a time)
- Beautiful step progress indicator

### 2. **AI-Powered Generation**
Uses Claude (Anthropic API) to:
- Extract structured data from conversations
- Generate comprehensive voice guidelines
- Expand 5-10 topics into 50-100 content ideas
- Create platform-specific prompt templates
- Build complete profile configuration

### 3. **Complete Profile Output**
Generates:
- Profile metadata (key, name, description)
- Voice guidelines (tone, style, do's and don'ts)
- 50-100 content topics
- Platform configurations (Twitter, Threads, LinkedIn, etc.)
- Posting frequencies per platform
- Format preferences (length, emojis, hashtags)
- Prompt templates for each platform + language + content type
- Content routing rules
- Reply strategies

## How to Test

1. **Refresh your browser** (http://localhost:8503)
2. Click the **"🧙 AI Wizard"** tab
3. Click **"🚀 Start Wizard"**
4. Answer the AI's questions naturally

### Example Flow:

**Step 1: Project Info (2-3 min)**
```
AI: "What's your project about? Tell me what you're building."
You: "It's a DeFi protocol for yield optimization"

AI: "Who are you trying to reach?"
You: "Crypto traders and DeFi power users"

AI: "What makes you different?"
You: "We use AI-powered rebalancing algorithms"
```

**Step 2: Voice & Style (2-3 min)**
```
AI: "How do you want to sound? Pick any: Technical, Casual, Professional..."
You: "Technical, Data-driven, Casual"

AI: "Share 2-3 example posts you like"
You: [paste example tweets]

AI: "What should you NEVER sound like?"
You: "No corporate jargon, no hype language"
```

**Step 3: Platforms & Content (3-4 min)**
```
AI: "Which platforms do you want to use?"
You: "Twitter, Threads, Telegram"

AI: "How often to post on Twitter?"
You: "2-3x daily"

AI: "Give me 5-10 topics to get started"
You: "DeFi trends, yield strategies, protocol comparisons..."
```

**Step 4: Engagement (1-2 min)**
```
AI: "Want to auto-reply to relevant conversations?"
You: "Yes"

AI: "What types of posts should I reply to?"
You: "Questions about yield farming, discussions about DeFi protocols"
```

**Step 5: Generate (30 seconds)**
- AI generates complete profile config
- Saves to `/config/profiles/{profile_key}.json`
- Shows success message with summary

## Files Created

### Backend:
- **`src/services/profile_wizard.py`** - AI wizard service
  - `ProfileWizard` class with conversational interview logic
  - `WizardState` dataclass for tracking progress
  - Methods for extracting data, generating configs, expanding topics
  - Uses Anthropic Claude API for AI generation

### Frontend:
- **`src/web/components/profile_wizard_tab.py`** - Wizard UI
  - Welcome screen with benefits overview
  - Conversational chat interface
  - Progress bar showing 5 steps
  - Real-time data extraction display (debug mode)
  - Success screen with config preview

### Integration:
- **`src/web/app.py`** - Added wizard tab
  - New tab: "🧙 AI Wizard"
  - Positioned between Rewriter Lab and Profile Manager

## Technical Details

### API Requirements
- Requires `ANTHROPIC_API_KEY` in `.env`
- Uses `claude-3-5-sonnet-20241022` model
- Each profile generation: ~5-10 API calls

### Data Flow
```
User Input
  ↓
Profile Wizard (conversational AI)
  ↓
Extract structured data
  ↓
Generate voice guidelines (AI)
  ↓
Expand content topics (AI)
  ↓
Generate prompt templates (AI)
  ↓
Build platform config
  ↓
Save to config/profiles/{key}.json
  ↓
Ready to use!
```

## Monetization Impact

This feature transforms the product from:
- ❌ **Technical tool** (requires JSON editing, config knowledge)
- ✅ **User-friendly product** (10-minute guided setup)

### Target Customers Can Now:
1. **Solo founders** - Set up profiles for multiple projects quickly
2. **Agencies** - Onboard client accounts in a sales call
3. **Marketers** - Create profiles without technical knowledge
4. **Crypto projects** - Launch social presence same day

### Pricing Justification:
- **Before**: Free/cheap (manual setup is painful)
- **After**: $99-$699/month (AI wizard saves hours, enables scale)

## Next Steps

1. **Test the wizard** with your new startup profile
2. **Validate the generated config** looks good
3. **Test the full pipeline** with the AI-generated profile
4. **Iterate on questions** based on what info is missing
5. **Add voice example analysis** (AI analyzes example posts better)
6. **Add multi-language support** (ask which languages they want)

## Potential Improvements

### Short-term:
- Add "Skip" button for optional questions
- Show real-time preview of generated config
- Add "Edit" mode to refine answers
- Better error handling for API failures

### Medium-term:
- Analyze example posts with vision (if they paste images)
- Multi-language setup (not just English)
- Import existing profiles for refinement
- A/B test generated prompts

### Long-term:
- Learn from successful profiles (what works)
- Suggest improvements based on performance
- Industry-specific templates (crypto, SaaS, etc.)
- White-label for agencies

## Success Metrics

Track:
- ✅ Setup completion rate
- ✅ Time to complete wizard (target: <10 min)
- ✅ Generated profiles that get used
- ✅ Voice consistency scores for generated rewrites
- ✅ User satisfaction with generated configs

## Demo Script for Sales

> "Let me show you how easy it is to set up a new profile.
>
> [Click AI Wizard]
>
> See? The AI just asks you simple questions about your project.
> No technical stuff, no JSON files, no config syntax.
>
> [Walk through 4 steps]
>
> In 10 minutes, you get:
> - Complete voice guidelines
> - 50-100 content topic ideas
> - Platform setup for Twitter, LinkedIn, etc.
> - Custom prompts for each platform
> - Reply strategies for engagement
>
> All automatically generated by AI based on your answers.
>
> Your competitor? They're spending hours figuring out config files.
> You? You're already posting."

---

## Testing Checklist

- [ ] Wizard welcome screen loads
- [ ] Start button works
- [ ] Step 1: Can answer project questions
- [ ] Step 2: Can define voice/style
- [ ] Step 3: Can select platforms and topics
- [ ] Step 4: Can set engagement strategy
- [ ] Step 5: Profile generates successfully
- [ ] Config file saved to `/config/profiles/`
- [ ] Generated profile works in Profile Manager
- [ ] Can test rewrites with new profile
- [ ] Voice guidelines make sense
- [ ] Content topics are relevant
- [ ] Prompt templates work for rewriting

**Ready to test!** 🚀
