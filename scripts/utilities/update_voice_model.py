#!/usr/bin/env python3
"""
Auto-Update Voice Model from Corrections
Analyzes your corrections and updates voice patterns dynamically
"""
import json
import re
from pathlib import Path
from datetime import datetime
from collections import Counter
from typing import List, Dict, Any


class VoiceModelUpdater:
    """Learns from corrections and updates voice patterns"""

    def __init__(self):
        self.corrections_dir = Path("training_data/corrections")
        self.learned_patterns_dir = Path("training_data/learned_patterns")
        self.config_dir = Path("config")

        self.learned_patterns_dir.mkdir(parents=True, exist_ok=True)

    def load_all_corrections(self) -> List[Dict[str, Any]]:
        """Load all corrections from JSONL files"""
        corrections = []

        for filepath in self.corrections_dir.glob("*.jsonl"):
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        corrections.append(json.loads(line))

        return corrections

    def analyze_vocabulary_patterns(self, corrections: List[Dict]) -> Dict:
        """Extract vocabulary preferences from corrections"""

        preferred_words = Counter()
        avoided_words = Counter()

        for corr in corrections:
            if corr.get('status') != 'corrected':
                continue

            diffs = corr.get('differences', {})
            preferred_words.update(diffs.get('added_words', []))
            avoided_words.update(diffs.get('removed_words', []))

        return {
            "frequently_used_by_you": [word for word, count in preferred_words.most_common(50)],
            "frequently_avoided_by_you": [word for word, count in avoided_words.most_common(50)],
            "vocabulary_insights": {
                "total_unique_added": len(preferred_words),
                "total_unique_removed": len(avoided_words),
                "top_additions": dict(preferred_words.most_common(10)),
                "top_removals": dict(avoided_words.most_common(10))
            }
        }

    def analyze_structure_patterns(self, corrections: List[Dict]) -> Dict:
        """Extract structure preferences from corrections"""

        structure_changes = Counter()

        for corr in corrections:
            if corr.get('status') != 'corrected':
                continue

            diffs = corr.get('differences', {})
            structure_change = diffs.get('structure_change', 'none')

            if structure_change != 'none':
                structure_changes[structure_change] += 1

        return {
            "structural_preferences": dict(structure_changes),
            "insights": {
                "removed_numbered_threads": structure_changes.get('removed_numbered_thread', 0),
                "added_numbered_threads": structure_changes.get('added_numbered_thread', 0),
                "recommendation": self._get_structure_recommendation(structure_changes)
            }
        }

    def _get_structure_recommendation(self, structure_changes: Counter) -> str:
        """Generate structure recommendation based on patterns"""

        removed_threads = structure_changes.get('removed_numbered_thread', 0)
        added_threads = structure_changes.get('added_numbered_thread', 0)

        if removed_threads > added_threads * 2:
            return "User prefers single cohesive posts over numbered threads"
        elif added_threads > removed_threads * 2:
            return "User prefers numbered thread format"
        else:
            return "No strong preference detected yet"

    def analyze_tone_patterns(self, corrections: List[Dict]) -> Dict:
        """Extract tone preferences from corrections"""

        length_ratios = []
        rejection_reasons = []

        for corr in corrections:
            if corr.get('status') == 'corrected':
                diffs = corr.get('differences', {})
                ratio = diffs.get('length_ratio', 1.0)
                length_ratios.append(ratio)

            if corr.get('status') == 'rejected':
                reason = corr.get('rejection_reason', '')
                if reason:
                    rejection_reasons.append(reason)

        avg_length_ratio = sum(length_ratios) / len(length_ratios) if length_ratios else 1.0

        return {
            "length_preference": {
                "avg_correction_ratio": round(avg_length_ratio, 2),
                "interpretation": self._interpret_length_ratio(avg_length_ratio)
            },
            "rejection_patterns": rejection_reasons[:10],
            "tone_insights": {
                "total_corrections": len([c for c in corrections if c.get('status') == 'corrected']),
                "total_rejections": len([c for c in corrections if c.get('status') == 'rejected']),
                "total_approvals": len([c for c in corrections if c.get('status') == 'approved'])
            }
        }

    def _interpret_length_ratio(self, ratio: float) -> str:
        """Interpret length ratio changes"""
        if ratio < 0.7:
            return "User prefers significantly shorter, more concise posts"
        elif ratio < 0.9:
            return "User prefers slightly shorter posts"
        elif ratio > 1.3:
            return "User prefers significantly longer, more detailed posts"
        elif ratio > 1.1:
            return "User prefers slightly longer posts"
        else:
            return "User length preference similar to Gemini output"

    def extract_learned_patterns(self, corrections: List[Dict]) -> Dict:
        """Extract all learned patterns from corrections"""

        vocab_patterns = self.analyze_vocabulary_patterns(corrections)
        structure_patterns = self.analyze_structure_patterns(corrections)
        tone_patterns = self.analyze_tone_patterns(corrections)

        return {
            "metadata": {
                "total_corrections": len(corrections),
                "last_updated": datetime.now().isoformat(),
                "learning_version": "1.0"
            },
            "vocabulary": vocab_patterns,
            "structure": structure_patterns,
            "tone": tone_patterns
        }

    def save_learned_patterns(self, patterns: Dict, persona: str = "qronoya"):
        """Save learned patterns to file"""

        filepath = self.learned_patterns_dir / f"{persona}_learned_patterns.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(patterns, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Saved learned patterns to {filepath}")

    def generate_recommendations(self, patterns: Dict) -> List[str]:
        """Generate actionable recommendations based on learned patterns"""

        recommendations = []

        # Vocabulary recommendations
        avoided = patterns['vocabulary']['vocabulary_insights']['top_removals']
        if avoided:
            top_avoided = list(avoided.keys())[:3]
            recommendations.append(
                f"❌ AVOID these words: {', '.join(top_avoided)} (you consistently remove them)"
            )

        preferred = patterns['vocabulary']['vocabulary_insights']['top_additions']
        if preferred:
            top_preferred = list(preferred.keys())[:3]
            recommendations.append(
                f"✅ USE these words more: {', '.join(top_preferred)} (you consistently add them)"
            )

        # Structure recommendations
        struct_rec = patterns['structure']['insights']['recommendation']
        recommendations.append(f"📐 STRUCTURE: {struct_rec}")

        # Length recommendations
        length_pref = patterns['tone']['length_preference']['interpretation']
        recommendations.append(f"📏 LENGTH: {length_pref}")

        # Approval rate
        tone_insights = patterns['tone']['tone_insights']
        total = tone_insights['total_corrections'] + tone_insights['total_rejections'] + tone_insights['total_approvals']
        if total > 0:
            approval_rate = (tone_insights['total_approvals'] / total) * 100
            recommendations.append(f"📊 APPROVAL RATE: {approval_rate:.1f}% - {'Good!' if approval_rate > 50 else 'Needs improvement'}")

        return recommendations


def main():
    print("\n" + "="*100)
    print("🧠 VOICE MODEL AUTO-UPDATE")
    print("="*100)

    updater = VoiceModelUpdater()

    # Load corrections
    print("\n📂 Loading corrections...")
    corrections = updater.load_all_corrections()

    if not corrections:
        print("\n⚠️  No corrections found. Run demo_review_and_correct.py first!")
        return

    print(f"✅ Loaded {len(corrections)} corrections")

    # Extract patterns
    print("\n🔍 Analyzing patterns...")
    patterns = updater.extract_learned_patterns(corrections)

    # Save learned patterns
    updater.save_learned_patterns(patterns, "qronoya")

    # Generate recommendations
    print("\n" + "="*100)
    print("💡 RECOMMENDATIONS FOR VOICE MODEL")
    print("="*100)

    recommendations = updater.generate_recommendations(patterns)
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. {rec}")

    # Summary
    print("\n" + "="*100)
    print("📊 LEARNING SUMMARY")
    print("="*100)

    meta = patterns['metadata']
    vocab = patterns['vocabulary']['vocabulary_insights']
    tone = patterns['tone']['tone_insights']

    print(f"\nTotal corrections analyzed: {meta['total_corrections']}")
    print(f"Unique words you added: {vocab['total_unique_added']}")
    print(f"Unique words you removed: {vocab['total_unique_removed']}")
    print(f"\nApproved: {tone['total_approvals']}")
    print(f"Corrected: {tone['total_corrections']}")
    print(f"Rejected: {tone['total_rejections']}")

    print("\n" + "="*100)
    print("✅ NEXT STEPS")
    print("="*100)
    print("\n1. Review learned patterns in: training_data/learned_patterns/")
    print("2. Continue collecting corrections (target: 50-200)")
    print("3. System will automatically improve with more data")
    print("4. After 200+ corrections: Ready for fine-tuning!")

    print("\n" + "="*100)


if __name__ == "__main__":
    main()
