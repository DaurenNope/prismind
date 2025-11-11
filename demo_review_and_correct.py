#!/usr/bin/env python3
"""
Interactive Review & Correction Interface
Allows you to review Gemini rewrites and provide corrections for learning
"""
import asyncio
import json
import os
import sys
import tempfile
import subprocess
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

from src.publishing.rewriter import ContentRewriter


class CorrectionLogger:
    """Logs corrections for training data collection"""

    def __init__(self):
        self.corrections_dir = Path("training_data/corrections")
        self.approved_dir = Path("training_data/approved")
        self.corrections_dir.mkdir(parents=True, exist_ok=True)
        self.approved_dir.mkdir(parents=True, exist_ok=True)

    def save_correction(self, correction_data: dict):
        """Save a correction to JSONL file"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = self.corrections_dir / f"{date_str}_corrections.jsonl"

        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(json.dumps(correction_data, ensure_ascii=False) + '\n')

        print(f"\n✅ Saved correction to {filepath}")

    def save_approved(self, approved_data: dict):
        """Save an approved rewrite"""
        persona = approved_data['persona']
        count = len(list(self.approved_dir.glob(f"{persona}_*.json"))) + 1
        filepath = self.approved_dir / f"{persona}_approved_{count:03d}.json"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(approved_data, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Saved approved rewrite to {filepath}")


def get_user_input(prompt: str, valid_options: list = None) -> str:
    """Get user input with optional validation"""
    while True:
        response = input(prompt).strip().lower()
        if valid_options is None or response in valid_options:
            return response
        print(f"Invalid option. Please choose from: {', '.join(valid_options)}")


def open_editor(initial_text: str = "") -> str:
    """Open system editor for text input"""
    editor = os.environ.get('EDITOR', 'nano')

    with tempfile.NamedTemporaryFile(mode='w+', suffix='.txt', delete=False) as tf:
        tf.write(initial_text)
        tf.flush()
        temp_path = tf.name

    try:
        subprocess.call([editor, temp_path])
        with open(temp_path, 'r', encoding='utf-8') as f:
            edited_text = f.read().strip()
        return edited_text
    finally:
        os.unlink(temp_path)


def show_side_by_side(gemini_output: str, your_correction: str):
    """Display Gemini vs Your version side-by-side"""
    print("\n" + "="*100)
    print("COMPARISON: Gemini vs Your Correction")
    print("="*100)

    gemini_lines = gemini_output.split('\n')
    your_lines = your_correction.split('\n')

    max_lines = max(len(gemini_lines), len(your_lines))

    print(f"\n{'GEMINI OUTPUT':<50} | {'YOUR CORRECTION':<50}")
    print("-"*50 + "-+-" + "-"*50)

    for i in range(max_lines):
        gemini_line = gemini_lines[i] if i < len(gemini_lines) else ""
        your_line = your_lines[i] if i < len(your_lines) else ""

        # Truncate long lines
        gemini_line = gemini_line[:47] + "..." if len(gemini_line) > 50 else gemini_line
        your_line = your_line[:47] + "..." if len(your_line) > 50 else your_line

        print(f"{gemini_line:<50} | {your_line:<50}")

    print("\n" + "="*100)


async def review_session():
    """Interactive review session for generated rewrites"""

    print("\n" + "="*100)
    print("🔍 INTERACTIVE REVIEW & CORRECTION SESSION")
    print("="*100)
    print("\nThis tool helps you:")
    print("1. Review Gemini-generated rewrites")
    print("2. Approve, edit, or reject them")
    print("3. System learns from your corrections")
    print("\n")

    # Initialize
    rewriter = ContentRewriter()
    logger = CorrectionLogger()

    # Sample posts for review (you can modify this)
    SAMPLE_POSTS = [
        {
            "title": "Chinese AI startups",
            "content": "Chinese AI startups: 1/6th of US funding, bad press, sanctions. But after using Manus AI, Deepseek, Trae, Kling, Vidu, I think the US is in trouble. At this pace, China will dominate AI.",
            "persona": "qronoya",
            "category": "Technology"
        },
        {
            "title": "Career transition advice",
            "content": "Many developers ask how to transition into senior roles. Key things: take ownership of projects, mentor juniors, think about architecture not just code, communicate effectively with non-technical stakeholders.",
            "persona": "qronoya",
            "category": "Career"
        }
    ]

    for idx, post_data in enumerate(SAMPLE_POSTS, 1):
        print(f"\n{'='*100}")
        print(f"POST #{idx}: {post_data['title']}")
        print("="*100)

        print(f"\n📝 ORIGINAL CONTENT:")
        print("-" * 100)
        print(post_data['content'])
        print("-" * 100)

        # Analyze and extract ideas
        analyzed = {
            'content': post_data['content'],
            'category': post_data['category'],
            'summary': post_data['content'][:200],
            'key_concepts': [],
            'topics': [],
            'rewrite_angles': [{
                'persona': post_data['persona'],
                'angle': f'Rewrite in {post_data["persona"]} voice',
                'tone': 'Natural',
                'platform_fit': 'twitter_thread'
            }]
        }

        # Generate rewrite
        print(f"\n⏳ Generating rewrite with Gemini...")
        result = await rewriter.rewrite_analyzed_post(
            analyzed,
            post_data['persona'],
            'twitter'
        )

        gemini_output = result.get('rewritten_content', 'Error generating rewrite')
        extracted_ideas = result.get('extracted_ideas', 'N/A')

        print(f"\n🤖 GEMINI REWRITE:")
        print("-" * 100)
        print(gemini_output)
        print("-" * 100)

        # Review options
        print(f"\n📊 What do you want to do?")
        print("  1. ✅ Approve (use as-is, add to training data)")
        print("  2. ✏️  Edit (fix it, save your version)")
        print("  3. ❌ Reject (discard, don't save)")
        print("  4. ⏭️  Skip (review later)")
        print("  5. 🛑 Quit (exit session)")

        choice = get_user_input("\nYour choice (1-5): ", ['1', '2', '3', '4', '5'])

        if choice == '1':
            # Approve
            print("\n✅ Approved!")

            approved_data = {
                "id": f"approved_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "original_content": post_data['content'],
                "persona": post_data['persona'],
                "gemini_output": gemini_output,
                "extracted_ideas": extracted_ideas,
                "status": "approved",
                "category": post_data['category']
            }

            logger.save_approved(approved_data)

        elif choice == '2':
            # Edit
            print("\n✏️  Opening editor for your correction...")
            print("(Edit the text below, then save and close the editor)")

            your_correction = open_editor(gemini_output)

            if not your_correction:
                print("\n⚠️  No text entered, skipping...")
                continue

            # Show comparison
            show_side_by_side(gemini_output, your_correction)

            # Analyze differences (simple version for now)
            differences = analyze_differences(gemini_output, your_correction)

            print(f"\n📊 ANALYSIS:")
            print(f"  • Gemini length: {len(gemini_output)} chars")
            print(f"  • Your length: {len(your_correction)} chars")
            print(f"  • Word count change: {len(gemini_output.split())} → {len(your_correction.split())} words")

            # Save correction
            correction_data = {
                "id": f"correction_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "original_content": post_data['content'],
                "extracted_ideas": extracted_ideas,
                "gemini_output": gemini_output,
                "your_correction": your_correction,
                "persona": post_data['persona'],
                "status": "corrected",
                "differences": differences,
                "category": post_data['category']
            }

            logger.save_correction(correction_data)

            # Ask for notes
            notes = input("\n💭 Any notes on what you changed? (optional): ").strip()
            if notes:
                correction_data['notes'] = notes
                logger.save_correction(correction_data)

        elif choice == '3':
            # Reject
            print("\n❌ Rejected. Not saving this rewrite.")

            # Still log rejection for analysis
            rejection_data = {
                "id": f"rejected_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "timestamp": datetime.now().isoformat(),
                "original_content": post_data['content'],
                "gemini_output": gemini_output,
                "persona": post_data['persona'],
                "status": "rejected"
            }

            notes = input("\n💭 Why rejected? (helps improve system): ").strip()
            if notes:
                rejection_data['rejection_reason'] = notes

            logger.save_correction(rejection_data)

        elif choice == '4':
            # Skip
            print("\n⏭️  Skipped. Moving to next post...")
            continue

        elif choice == '5':
            # Quit
            print("\n🛑 Exiting review session...")
            break

    # Session summary
    corrections_count = len(list(Path("training_data/corrections").glob("*.jsonl")))
    approved_count = len(list(Path("training_data/approved").glob("*.json")))

    print(f"\n{'='*100}")
    print("📊 SESSION SUMMARY")
    print("="*100)
    print(f"Total corrections logged: {corrections_count}")
    print(f"Total approved rewrites: {approved_count}")
    print(f"\nData saved in:")
    print(f"  • training_data/corrections/ (for learning)")
    print(f"  • training_data/approved/ (for fine-tuning)")
    print("\nNext steps:")
    print("  • After 50 corrections: Run python scripts/update_voice_model.py")
    print("  • After 200 corrections: Run python scripts/fine_tune_model.py")
    print("="*100)


def analyze_differences(gemini_output: str, your_correction: str) -> dict:
    """Simple difference analysis between Gemini and your correction"""

    gemini_words = set(gemini_output.lower().split())
    your_words = set(your_correction.lower().split())

    added_words = your_words - gemini_words
    removed_words = gemini_words - your_words

    # Detect structure differences
    gemini_has_numbers = any(line.strip().startswith(('1/', '2/', '3/', '1.', '2.', '3.'))
                             for line in gemini_output.split('\n'))
    your_has_numbers = any(line.strip().startswith(('1/', '2/', '3/', '1.', '2.', '3.'))
                          for line in your_correction.split('\n'))

    structure_diff = "none"
    if gemini_has_numbers and not your_has_numbers:
        structure_diff = "removed_numbered_thread"
    elif not gemini_has_numbers and your_has_numbers:
        structure_diff = "added_numbered_thread"

    return {
        "added_words": list(added_words)[:20],  # Top 20
        "removed_words": list(removed_words)[:20],  # Top 20
        "structure_change": structure_diff,
        "length_ratio": len(your_correction) / len(gemini_output) if len(gemini_output) > 0 else 0
    }


if __name__ == "__main__":
    asyncio.run(review_session())
