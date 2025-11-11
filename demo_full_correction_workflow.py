#!/usr/bin/env python3
"""
Demo: Full Correction Workflow
Demonstrates the complete self-improving system end-to-end
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

load_dotenv(override=True)

from src.publishing.rewriter import ContentRewriter


def create_sample_corrections():
    """Create sample correction data for testing pattern extraction"""

    corrections_dir = Path("training_data/corrections")
    corrections_dir.mkdir(parents=True, exist_ok=True)

    # Sample corrections demonstrating patterns
    sample_corrections = [
        {
            "id": "correction_001",
            "timestamp": datetime.now().isoformat(),
            "original_content": "Chinese AI startups: 1/6th of US funding, bad press, sanctions. But after using Manus AI, Deepseek, I think the US is in trouble.",
            "extracted_ideas": "Despite having only 1/6th of US funding, bad press, and sanctions, Chinese AI startups are creating competitive products that may challenge US dominance.",
            "gemini_output": "1/x Знаете эту тему – китайские ИИ стартапы… им жёстко недосыпают бабла, если сравнивать с американскими. Прям сильно.\n\n2/x Ngl, там где в Штатах стартап поднимает $100M, китайский получит дай бог $15M-$20M. fr fr это жесть.\n\n3/x Плюс ко всему, постоянный негатив в медиа и риск санкций… Это как вообще бизнес строить?\n\n4/x Но есть варианты, как выкручиваться. Слышал про Manus AI и Deepseek – вроде, норм туллы.",
            "your_correction": "Глобальная разница в финансирование американских ИИ стартапов и китайских.\n\nТам где американские привлекают миллирдами, Китай делает аналоги за относительные копейки? В чем же разница?\n\nПонятно, то что в основном китайские модели обучены на американских лидерах, но если китаю удается сделать конкуретный продукт почему не пользоваться им?\n\nИнтересен фактор того что в каких-то моментах китайские модели уже опережают американские (например DeepSeek в недавнем тесте торговли перформит лучше всех)",
            "persona": "qronoya",
            "status": "corrected",
            "differences": {
                "added_words": ["разница", "миллирдами", "копейки", "конкуретный", "фактор", "опережают", "торговли", "перформит"],
                "removed_words": ["недосыпают", "бабла", "ngl", "fr", "жесть", "туллы", "выкручиваться"],
                "structure_change": "removed_numbered_thread",
                "length_ratio": 0.85
            },
            "category": "Technology",
            "notes": "Removed forced slang (fr fr, ngl, недосыпают бабла). Changed from 4-tweet thread to single cohesive post. Added rhetorical questions. More natural vocabulary that fits context."
        },
        {
            "id": "correction_002",
            "timestamp": datetime.now().isoformat(),
            "original_content": "Many developers ask how to transition into senior roles. Key things: take ownership, mentor juniors, think architecture.",
            "extracted_ideas": "Career progression to senior developer roles requires ownership of projects, mentoring juniors, and architectural thinking.",
            "gemini_output": "Каждый раз спрашивают – как стать сеньором? fr fr это не просто про код.\n\nВо-первых, берите ответственность за проекты. Не ждите, когда вам дадут – берите сами.\n\nВо-вторых, помогайте джунам. Это офигительно прокачивает ваше понимание.\n\nВ-третьих, думайте про архитектуру, а не только про функции.",
            "your_correction": "Переход в senior роли – частый вопрос от разработчиков.\n\nОсновное: берите ownership проектов, не ждите когда дадут задачу. Инициатива решает.\n\nПомощь младшим специалистам прокачивает ваше собственное понимание архитектуры.\n\nДумайте про систему в целом, а не только про конкретную функцию которую пишете.",
            "persona": "qronoya",
            "status": "corrected",
            "differences": {
                "added_words": ["переход", "ownership", "инициатива", "решает", "младшим", "специалистам", "систему", "конкретную"],
                "removed_words": ["fr", "офигительно", "джунам", "прокачивает"],
                "structure_change": "none",
                "length_ratio": 0.92
            },
            "category": "Career",
            "notes": "Removed 'fr fr' and 'офигительно' - not natural here. Kept 'ownership' as English tech term. More professional tone for career advice."
        },
        {
            "id": "correction_003",
            "timestamp": datetime.now().isoformat(),
            "original_content": "Working on AI automation for business tasks. The future is here.",
            "extracted_ideas": "Building AI automation solutions for business process automation.",
            "gemini_output": "Работаю над ИИ автоматизацией для бизнес задач. Будущее уже здесь, ngl это офигительно крутая тема.",
            "your_correction": "Работаю над ИИ автоматизацией бизнес процессов. С умом подходим – автоматизация должна решать реальные проблемы, а не быть AI ради AI.",
            "persona": "qronoya",
            "status": "corrected",
            "differences": {
                "added_words": ["процессов", "умом", "подходим", "решать", "реальные", "проблемы", "ради"],
                "removed_words": ["ngl", "офигительно", "крутая", "тема", "будущее"],
                "structure_change": "none",
                "length_ratio": 1.15
            },
            "category": "Technology",
            "notes": "Added philosophy 'с умом' and practical focus. Removed generic 'будущее уже здесь' cliche and forced 'ngl офигительно'."
        },
        {
            "id": "approved_001",
            "timestamp": datetime.now().isoformat(),
            "original_content": "Love Almaty but the mood swings are real. Is it the city or me?",
            "gemini_output": "Love and hate relationship с Алматы fr fr. То все супер, то хочется уехать.\n\nМожет все таки, дело не в городе? Интересно что другие думают.",
            "persona": "qronoya",
            "status": "approved",
            "category": "Personal",
            "notes": "Perfect! Natural mix of English/Russian. Philosophical question at end. Matches real post style."
        },
        {
            "id": "rejected_001",
            "timestamp": datetime.now().isoformat(),
            "original_content": "New AI tool for developers announced today.",
            "gemini_output": "Новый ИИ инструмент для разработчиков анонсировали сегодня. Посмотрим что там.",
            "persona": "qronoya",
            "status": "rejected",
            "rejection_reason": "Too generic and boring. No personality, no opinion, no value added. Just repeating news."
        }
    ]

    # Save to JSONL file
    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = corrections_dir / f"{date_str}_demo_corrections.jsonl"

    with open(filepath, 'w', encoding='utf-8') as f:
        for correction in sample_corrections:
            f.write(json.dumps(correction, ensure_ascii=False) + '\n')

    print(f"✅ Created sample corrections: {filepath}")
    print(f"   - 3 corrections (with edits)")
    print(f"   - 1 approval")
    print(f"   - 1 rejection")

    return filepath


async def test_pattern_extraction():
    """Test the pattern extraction from sample corrections"""
    print("\n" + "="*100)
    print("🔍 TESTING PATTERN EXTRACTION")
    print("="*100)

    # Import after we've created the data
    import sys
    sys.path.insert(0, str(Path(__file__).parent / "scripts"))

    from update_voice_model import VoiceModelUpdater

    updater = VoiceModelUpdater()

    # Load corrections
    print("\n📂 Loading corrections...")
    corrections = updater.load_all_corrections()
    print(f"✅ Loaded {len(corrections)} corrections")

    if not corrections:
        print("\n⚠️  No corrections found!")
        return

    # Extract patterns
    print("\n🔍 Analyzing patterns...")
    patterns = updater.extract_learned_patterns(corrections)

    # Display results
    print("\n" + "="*100)
    print("📊 EXTRACTED PATTERNS")
    print("="*100)

    vocab = patterns['vocabulary']
    print("\n🔤 VOCABULARY PATTERNS:")
    print(f"   Words you ADD frequently: {vocab['vocabulary_insights']['top_additions']}")
    print(f"   Words you REMOVE frequently: {vocab['vocabulary_insights']['top_removals']}")

    structure = patterns['structure']
    print("\n📐 STRUCTURE PATTERNS:")
    print(f"   Recommendation: {structure['insights']['recommendation']}")
    print(f"   Removed numbered threads: {structure['insights']['removed_numbered_threads']}")
    print(f"   Added numbered threads: {structure['insights']['added_numbered_threads']}")

    tone = patterns['tone']
    print("\n📏 TONE PATTERNS:")
    print(f"   Length preference: {tone['length_preference']['interpretation']}")
    print(f"   Avg correction ratio: {tone['length_preference']['avg_correction_ratio']}")

    print("\n📈 STATS:")
    print(f"   Total corrections: {tone['tone_insights']['total_corrections']}")
    print(f"   Total approvals: {tone['tone_insights']['total_approvals']}")
    print(f"   Total rejections: {tone['tone_insights']['total_rejections']}")

    # Generate recommendations
    print("\n" + "="*100)
    print("💡 RECOMMENDATIONS")
    print("="*100)

    recommendations = updater.generate_recommendations(patterns)
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec}")

    # Save learned patterns
    print("\n" + "="*100)
    updater.save_learned_patterns(patterns, "qronoya")

    return patterns


async def main():
    print("\n" + "="*100)
    print("🧪 DEMO: FULL CORRECTION WORKFLOW")
    print("="*100)
    print("\nThis demo demonstrates the complete self-improving system:")
    print("1. Create sample correction data")
    print("2. Extract patterns from corrections")
    print("3. Generate recommendations")
    print("4. Save learned patterns for future use")

    # Step 1: Create sample corrections
    print("\n" + "="*100)
    print("STEP 1: Creating Sample Correction Data")
    print("="*100)
    create_sample_corrections()

    # Step 2: Extract patterns
    print("\n" + "="*100)
    print("STEP 2: Extracting Patterns from Corrections")
    print("="*100)
    await test_pattern_extraction()

    # Summary
    print("\n" + "="*100)
    print("✅ WORKFLOW TEST COMPLETE")
    print("="*100)
    print("\n📁 Files created:")
    print("   • training_data/corrections/YYYY-MM-DD_demo_corrections.jsonl")
    print("   • training_data/learned_patterns/qronoya_learned_patterns.json")

    print("\n🚀 NEXT STEPS FOR REAL USE:")
    print("   1. Run: python demo_review_and_correct.py")
    print("      → Review real Gemini-generated rewrites")
    print("      → Make corrections to teach the system your voice")
    print("   ")
    print("   2. After 10-20 corrections, run: python scripts/update_voice_model.py")
    print("      → System analyzes your correction patterns")
    print("      → Generates recommendations for improvement")
    print("   ")
    print("   3. After 200+ corrections: Ready for fine-tuning!")
    print("      → Collect 200-1000 corrections over time")
    print("      → Fine-tune local model (Qwen 2.5 7B)")
    print("      → Deploy without API costs")

    print("\n" + "="*100)


if __name__ == "__main__":
    asyncio.run(main())
