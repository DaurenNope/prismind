#!/usr/bin/env python3
"""
Creative Testing Script - Works Offline
Test rewrite components without API calls while APIs are exhausted
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)-8s %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def test_prompt_engineering():
    """Test prompt variations without API calls"""
    logger.info("🧪 Testing prompt engineering...")
    
    # Sample content
    sample_content = {
        'content': 'OpenAI released GPT-4 with 1.7T parameters, trained on 13T tokens. Performance: 90% on MMLU, 88% on HellaSwag.',
        'category': 'Technology',
        'summary': 'GPT-4 release with impressive specs',
        'key_concepts': ['GPT-4', 'parameters', 'training', 'benchmarks'],
        'topics': ['AI', 'machine learning', 'OpenAI']
    }
    
    # Test different prompt strategies
    prompts = {
        'short_punchy': """
        WRITING STRATEGY: SHORT & PUNCHY
        - Maximum 3-4 sentences total
        - Add line break (\\n\\n) after EVERY sentence for readability
        - Direct, minimal, no fluff
        - Each line = complete thought
        """,
        'expanded_context': """
        WRITING STRATEGY: EXPANDED WITH CONTEXT
        - Add specific details: numbers, comparisons, examples
        - Explain WHY this matters or what it means
        - Add line breaks (\\n\\n) every 1-2 sentences
        - Include background context or concrete data points
        - Make it informative and thorough (5-7 sentences)
        """,
        'provocative_story': """
        WRITING STRATEGY: PROVOCATIVE/STORY
        - Start with controversial statement or personal admission
        - Use first-person angle ("я думал X, оказалось Y")
        - Add line breaks (\\n\\n) for dramatic pauses
        - Create tension, irony, or contradiction
        - End with provocative question to audience
        """
    }
    
    logger.info(f"✅ Generated {len(prompts)} prompt variations")
    return prompts


def test_example_selection():
    """Test smart example selection logic"""
    logger.info("🧪 Testing example selection...")
    
    # Load examples
    examples_file = Path("config/personas/qronoya_examples.json")
    if not examples_file.exists():
        logger.warning(f"Examples file not found: {examples_file}")
        return {}
    
    with open(examples_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    examples = data.get('examples', [])
    logger.info(f"📚 Loaded {len(examples)} examples")
    
    # Test classification
    test_content = {
        'content': 'OpenAI привлек $10M в раунде Series A',
        'category': 'Technology',
        'topics': ['funding', 'startup']
    }
    
    # Classify content type
    content_lower = test_content['content'].lower()
    if any(kw in content_lower for kw in ['привлек', 'раунд', '$', 'инвестиц', 'funding', 'series', 'raised']):
        content_type = "funding_news"
    else:
        content_type = "trend_analysis"
    
    logger.info(f"✅ Classified as: {content_type}")
    
    # Filter examples by type
    type_matches = [
        ex for ex in examples
        if ex.get('content_type') == content_type
    ]
    
    logger.info(f"✅ Found {len(type_matches)} examples matching {content_type}")
    
    return {
        'total_examples': len(examples),
        'content_type': content_type,
        'matching_examples': len(type_matches)
    }


def test_voice_validation():
    """Test voice validation on existing rewrites"""
    logger.info("🧪 Testing voice validation...")
    
    # Sample rewrite
    sample_rewrite = """
    OpenAI выпустил GPT-4 с 1.7T параметров, обученный на 13T токенах.
    
    Производительность: 90% на MMLU, 88% на HellaSwag.
    
    Это не просто обновление - это качественный скачок в понимании контекста.
    """
    
    # Check for forbidden elements
    import re
    
    # Emojis
    emoji_pattern = re.compile('['
        u'\U0001F600-\U0001F64F'  # emoticons
        u'\U0001F300-\U0001F5FF'  # symbols & pictographs
        u'\U0001F680-\U0001F6FF'  # transport & map symbols
        u'\U0001F1E0-\U0001F1FF'  # flags
        u'\U00002702-\U000027B0'
        u'\U000024C2-\U0001F251'
        u'\U0001F900-\U0001F9FF'  # supplemental symbols
        u'\U0001FA70-\U0001FAFF'
        ']+', flags=re.UNICODE)
    
    emoji_matches = emoji_pattern.findall(sample_rewrite)
    has_emojis = len(emoji_matches) > 0
    
    # Hashtags
    hashtag_pattern = re.compile(r'#\w+')
    hashtag_matches = hashtag_pattern.findall(sample_rewrite)
    has_hashtags = len(hashtag_matches) > 0
    
    # Corporate language
    corporate_phrases = [
        'join us', 'follow for more', 'don\'t miss out', 'click the link',
        'subscribe now', 'check out our', 'visit our website', 'learn more at'
    ]
    found_corporate = [phrase for phrase in corporate_phrases if phrase in sample_rewrite.lower()]
    has_corporate = len(found_corporate) > 0
    
    logger.info(f"✅ Voice validation results:")
    logger.info(f"   Emojis: {'❌ Found' if has_emojis else '✅ None'}")
    logger.info(f"   Hashtags: {'❌ Found' if has_hashtags else '✅ None'}")
    logger.info(f"   Corporate language: {'❌ Found' if has_corporate else '✅ None'}")
    
    return {
        'has_emojis': has_emojis,
        'has_hashtags': has_hashtags,
        'has_corporate': has_corporate,
        'passed': not (has_emojis or has_hashtags or has_corporate)
    }


def test_thread_splitting():
    """Test thread splitter with sample content"""
    logger.info("🧪 Testing thread splitting...")
    
    # Long content that needs splitting
    long_content = """
    OpenAI выпустил GPT-4 с 1.7T параметров, обученный на 13T токенах.
    
    Производительность: 90% на MMLU, 88% на HellaSwag.
    
    Это не просто обновление - это качественный скачок в понимании контекста.
    
    Что это значит для разработчиков? Теперь можно создавать более умные приложения.
    
    Но есть нюанс: стоимость API выросла. Нужно считать ROI перед интеграцией.
    
    Вывод: мощный инструмент, но не для всех проектов. Оцените свои потребности.
    """
    
    # Simple splitter (simulate)
    sentences = [s.strip() for s in long_content.split('.') if s.strip()]
    
    tweets = []
    current_tweet = ""
    
    for sentence in sentences:
        if len(current_tweet) + len(sentence) + 2 <= 280:
            current_tweet += sentence + ". "
        else:
            if current_tweet:
                tweets.append(current_tweet.strip())
            current_tweet = sentence + ". "
    
    if current_tweet:
        tweets.append(current_tweet.strip())
    
    logger.info(f"✅ Split into {len(tweets)} tweets")
    for i, tweet in enumerate(tweets, 1):
        logger.info(f"   Tweet {i}: {len(tweet)} chars")
        if len(tweet) > 280:
            logger.warning(f"   ⚠️ Tweet {i} exceeds 280 chars!")
    
    return {
        'tweet_count': len(tweets),
        'max_length': max(len(t) for t in tweets) if tweets else 0,
        'all_valid': all(len(t) <= 280 for t in tweets)
    }


def test_quality_scoring():
    """Test quality scoring on sample rewrites"""
    logger.info("🧪 Testing quality scoring...")
    
    # Sample rewrites with different quality levels
    rewrites = {
        'good': """
        OpenAI выпустил GPT-4 с 1.7T параметров.
        
        Производительность: 90% на MMLU, 88% на HellaSwag.
        
        Это качественный скачок в понимании контекста.
        """,
        'bad_emoji': """
        OpenAI выпустил GPT-4 🚀 с 1.7T параметров.
        
        Производительность: 90% на MMLU, 88% на HellaSwag 💎.
        
        Это качественный скачок в понимании контекста ✨.
        """,
        'bad_hashtag': """
        OpenAI выпустил GPT-4 с 1.7T параметров.
        
        #AI #MachineLearning #OpenAI
        
        Производительность: 90% на MMLU, 88% на HellaSwag.
        """,
        'bad_corporate': """
        OpenAI выпустил GPT-4 с 1.7T параметров.
        
        Производительность: 90% на MMLU, 88% на HellaSwag.
        
        Check out our website to learn more!
        """
    }
    
    import re
    
    def score_rewrite(text: str) -> Dict[str, Any]:
        score = 100
        issues = []
        
        # Check emojis
        emoji_pattern = re.compile('['
            u'\U0001F600-\U0001F64F'
            u'\U0001F300-\U0001F5FF'
            u'\U0001F680-\U0001F6FF'
            u'\U0001F1E0-\U0001F1FF'
            u'\U00002702-\U000027B0'
            u'\U000024C2-\U0001F251'
            u'\U0001F900-\U0001F9FF'
            u'\U0001FA70-\U0001FAFF'
            ']+', flags=re.UNICODE)
        
        if emoji_pattern.findall(text):
            score -= 20
            issues.append("emojis")
        
        # Check hashtags
        if re.compile(r'#\w+').findall(text):
            score -= 15
            issues.append("hashtags")
        
        # Check corporate language
        corporate = ['join us', 'follow for more', 'check out our', 'learn more at']
        if any(phrase in text.lower() for phrase in corporate):
            score -= 10
            issues.append("corporate_language")
        
        return {
            'score': max(0, score),
            'issues': issues,
            'passed': score >= 70
        }
    
    results = {}
    for name, rewrite in rewrites.items():
        result = score_rewrite(rewrite)
        results[name] = result
        logger.info(f"   {name}: {result['score']}/100 - {'✅' if result['passed'] else '❌'} - Issues: {result['issues']}")
    
    return results


def test_fact_validation():
    """Test fact preservation validation"""
    logger.info("🧪 Testing fact validation...")
    
    original = """
    OpenAI released GPT-4 with 1.7T parameters, trained on 13T tokens.
    Performance: 90% on MMLU, 88% on HellaSwag.
    Cost: $0.03 per 1K tokens for input.
    """
    
    rewritten_good = """
    OpenAI выпустил GPT-4 с 1.7T параметров, обученный на 13T токенах.
    
    Производительность: 90% на MMLU, 88% на HellaSwag.
    
    Стоимость: $0.03 за 1K токенов для ввода.
    """
    
    rewritten_bad = """
    OpenAI выпустил GPT-4 с 2T параметров, обученный на 15T токенах.
    
    Производительность: 95% на MMLU, 90% на HellaSwag.
    
    Стоимость: $0.05 за 1K токенов.
    """
    
    # Extract numbers from original
    import re
    original_numbers = re.findall(r'\d+\.?\d*[TKM]?', original)
    logger.info(f"   Original numbers: {original_numbers}")
    
    # Check preservation
    def check_preservation(original: str, rewritten: str) -> Dict[str, Any]:
        original_nums = set(re.findall(r'\d+\.?\d*[TKM]?', original))
        rewritten_nums = set(re.findall(r'\d+\.?\d*[TKM]?', rewritten))
        
        preserved = original_nums.intersection(rewritten_nums)
        missing = original_nums - rewritten_nums
        added = rewritten_nums - original_nums
        
        preservation_rate = len(preserved) / len(original_nums) * 100 if original_nums else 0
        
        return {
            'preservation_rate': preservation_rate,
            'preserved': list(preserved),
            'missing': list(missing),
            'added': list(added),
            'passed': preservation_rate >= 70
        }
    
    good_result = check_preservation(original, rewritten_good)
    bad_result = check_preservation(original, rewritten_bad)
    
    logger.info(f"   Good rewrite: {good_result['preservation_rate']:.1f}% - {'✅' if good_result['passed'] else '❌'}")
    logger.info(f"   Bad rewrite: {bad_result['preservation_rate']:.1f}% - {'✅' if bad_result['passed'] else '❌'}")
    
    return {
        'good': good_result,
        'bad': bad_result
    }


def main():
    """Run all creative tests"""
    logger.info("=" * 80)
    logger.info("🧪 CREATIVE TESTING - OFFLINE MODE")
    logger.info("=" * 80)
    logger.info("")
    
    results = {}
    
    # Run all tests
    try:
        results['prompt_engineering'] = test_prompt_engineering()
    except Exception as e:
        logger.error(f"❌ Prompt engineering test failed: {e}")
        results['prompt_engineering'] = {'error': str(e)}
    
    try:
        results['example_selection'] = test_example_selection()
    except Exception as e:
        logger.error(f"❌ Example selection test failed: {e}")
        results['example_selection'] = {'error': str(e)}
    
    try:
        results['voice_validation'] = test_voice_validation()
    except Exception as e:
        logger.error(f"❌ Voice validation test failed: {e}")
        results['voice_validation'] = {'error': str(e)}
    
    try:
        results['thread_splitting'] = test_thread_splitting()
    except Exception as e:
        logger.error(f"❌ Thread splitting test failed: {e}")
        results['thread_splitting'] = {'error': str(e)}
    
    try:
        results['quality_scoring'] = test_quality_scoring()
    except Exception as e:
        logger.error(f"❌ Quality scoring test failed: {e}")
        results['quality_scoring'] = {'error': str(e)}
    
    try:
        results['fact_validation'] = test_fact_validation()
    except Exception as e:
        logger.error(f"❌ Fact validation test failed: {e}")
        results['fact_validation'] = {'error': str(e)}
    
    # Save results
    output_file = Path("data/creative_testing_results.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': results
        }, f, indent=2, ensure_ascii=False)
    
    logger.info("")
    logger.info("=" * 80)
    logger.info("✅ CREATIVE TESTING COMPLETE")
    logger.info(f"📄 Results saved to: {output_file}")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()

