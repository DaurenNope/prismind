#!/usr/bin/env python3
"""
Review & Publish from Database
Interactive workflow to review rewrites from database posts before publishing
"""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=True)

from src.domain.publishing.modular_rewriter.compat import create_compat_rewriter
from src.domain.publishing.scheduler import PublishingScheduler
from src.infrastructure.database.storage.db import StorageFacade


class DatabaseReviewWorkflow:
    """Interactive review workflow for database posts"""

    def __init__(self):
        self.db = StorageFacade()
        self.rewriter = create_compat_rewriter()
        self.scheduler = PublishingScheduler()

        # Language routing
        self.language_map = {
            "threads": "russian",
            "twitter": "english",
            "telegram": "russian",
            "reddit": "english",
        }

        # Output platform routing
        self.output_platforms = {
            "threads": "threads",
            "twitter": "twitter",
            "reddit": "threads",  # Reddit → Threads (Russian)
            "telegram": "telegram",
        }

        # Storage directories
        self.corrections_dir = Path("training_data/corrections")
        self.approved_dir = Path("training_data/approved")
        self.scheduled_dir = Path("scheduled_posts")

        self.corrections_dir.mkdir(parents=True, exist_ok=True)
        self.approved_dir.mkdir(parents=True, exist_ok=True)
        self.scheduled_dir.mkdir(parents=True, exist_ok=True)

    async def start_review_session(self, limit: int = 10, platform_filter: str = None):
        """Start interactive review session"""

        print("\n" + "=" * 100)
        print("🔍 DATABASE REVIEW & PUBLISH SESSION")
        print("=" * 100)
        print("\nThis workflow:")
        print("1. Pulls posts from your database (673 posts available)")
        print("2. Rewrites them with language routing:")
        print("   - Threads → Russian")
        print("   - Twitter → English")
        print("   - Telegram → Russian")
        print("3. Shows you each rewrite for review")
        print("4. You approve, edit, or reject")
        print("5. Approved posts get scheduled for publishing")
        print("6. System learns from your corrections")
        print()

        # Fetch posts
        print(f"📂 Fetching posts from database...")
        print(f"   Limit: {limit}")
        print(f"   Platform filter: {platform_filter or 'All'}")

        all_posts = self.db.get_posts(limit=limit * 3)
        posts = []

        for post in all_posts:
            if post is None:
                continue
            if platform_filter and post.get("platform") != platform_filter:
                continue
            posts.append(post)
            if len(posts) >= limit:
                break

        print(f"✅ Found {len(posts)} posts to review\n")

        if not posts:
            print("⚠️  No posts found. Check your database.")
            return

        # Review each post
        stats = {
            "total": len(posts),
            "approved": 0,
            "corrected": 0,
            "rejected": 0,
            "skipped": 0,
        }

        for idx, post in enumerate(posts, 1):
            print(f"\n{'='*100}")
            print(f"POST {idx}/{len(posts)}")
            print(f"{'='*100}")

            result = await self.review_single_post(post)

            if result == "approved":
                stats["approved"] += 1
            elif result == "corrected":
                stats["corrected"] += 1
            elif result == "rejected":
                stats["rejected"] += 1
            elif result == "skipped":
                stats["skipped"] += 1
            elif result == "quit":
                print("\n🛑 Exiting review session...")
                break

        # Session summary
        self.show_session_summary(stats)

    async def review_single_post(self, post: Dict) -> str:
        """
        Review a single post.

        Returns: 'approved', 'corrected', 'rejected', 'skipped', or 'quit'
        """

        # Extract post info
        title = post.get("title", "No title")
        content = post.get("content", "")
        source_platform = post.get("platform", "unknown")
        url = post.get("url", "")

        # Determine output platform and language
        output_platform = self.output_platforms.get(source_platform, "threads")
        language = self.language_map.get(output_platform, "russian")

        print(f"\n📝 ORIGINAL POST:")
        print("-" * 100)
        print(
            f"Source: {source_platform} → Output: {output_platform} ({language.upper()})"
        )
        print(f"Title: {title[:80]}...")
        print(f"URL: {url[:80]}...")
        print()
        print(f"Content:")
        print(content[:400])
        if len(content) > 400:
            print("...")
        print("-" * 100)

        # Generate rewrite
        print(f"\n⏳ Generating {language} rewrite for {output_platform}...")

        try:
            # Simple analysis
            analyzed = {
                "content": content,
                "category": "Technology",
                "summary": content[:200],
                "key_concepts": [],
                "topics": [],
                "rewrite_angles": [
                    {
                        "persona": "qronoya",
                        "angle": f"Rewrite in Qronoya voice",
                        "tone": "Natural",
                        "platform_fit": output_platform,
                    }
                ],
            }

            rewritten = await self.rewriter.rewrite_analyzed_post(
                analyzed_content=analyzed,
                persona="qronoya",
                platform=output_platform,
                language=language,
            )

            if "error" in rewritten:
                print(f"\n❌ Error: {rewritten['error']}")
                return "skipped"

            gemini_output = rewritten.get("rewritten_content", "")

        except Exception as e:
            print(f"\n❌ Error generating rewrite: {e}")
            return "skipped"

        # Show rewrite
        print(f"\n🤖 GEMINI REWRITE ({language.upper()}):")
        print("-" * 100)
        print(gemini_output)
        print("-" * 100)

        # Review options
        print(f"\n📊 What do you want to do?")
        print("  1. ✅ Approve & Schedule (use as-is)")
        print("  2. ✏️  Edit (fix it, then schedule)")
        print("  3. ❌ Reject (don't use)")
        print("  4. ⏭️  Skip (review later)")
        print("  5. 🛑 Quit (exit session)")

        choice = self.get_user_input("\nYour choice (1-5): ", ["1", "2", "3", "4", "5"])

        if choice == "1":
            # Approve
            return await self.handle_approval(
                post, gemini_output, output_platform, language
            )

        elif choice == "2":
            # Edit
            return await self.handle_correction(
                post, gemini_output, output_platform, language
            )

        elif choice == "3":
            # Reject
            return self.handle_rejection(post, gemini_output)

        elif choice == "4":
            # Skip
            print("\n⏭️  Skipped")
            return "skipped"

        elif choice == "5":
            # Quit
            return "quit"

    async def handle_approval(
        self, post: Dict, rewrite: str, platform: str, language: str
    ) -> str:
        """Handle approved rewrite"""

        print("\n✅ Approved!")

        # Schedule post
        decision = self.scheduler.schedule_rewritten_post(
            rewritten_content={
                "rewritten_content": rewrite,
                "viral_potential": 50,  # Default
                "time_sensitivity": "evergreen",
                "platform": platform,
            },
            platform_override=platform,
        )

        # Save scheduled post
        scheduled_post = {
            "id": f"{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "source_post": {
                "title": post.get("title", ""),
                "url": post.get("url", ""),
                "platform": post.get("platform", ""),
            },
            "rewritten_content": rewrite,
            "platform": platform,
            "language": language,
            "persona": "qronoya",
            "scheduled_for": decision.when.isoformat(),
            "priority": decision.priority,
            "reason": decision.reason,
            "status": "approved",
            "metadata": {"approved_at": datetime.now().isoformat()},
        }

        filepath = self.scheduled_dir / f"{scheduled_post['id']}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(scheduled_post, f, ensure_ascii=False, indent=2)

        print(f"📅 Scheduled for: {decision.when.strftime('%Y-%m-%d %H:%M')}")
        print(f"   Priority: {decision.priority}/100")
        print(f"💾 Saved to: {filepath}")

        # Log as approved for training
        self.log_approved(post, rewrite, platform, language)

        return "approved"

    async def handle_correction(
        self, post: Dict, gemini_output: str, platform: str, language: str
    ) -> str:
        """Handle corrected rewrite"""

        print("\n✏️  Opening editor for your correction...")

        your_correction = self.open_editor(gemini_output)

        if not your_correction or your_correction == gemini_output:
            print("\n⚠️  No changes made, skipping...")
            return "skipped"

        # Show comparison
        self.show_side_by_side(gemini_output, your_correction)

        # Analyze differences
        differences = self.analyze_differences(gemini_output, your_correction)

        print(f"\n📊 ANALYSIS:")
        print(f"  • Gemini length: {len(gemini_output)} chars")
        print(f"  • Your length: {len(your_correction)} chars")
        print(
            f"  • Word count change: {len(gemini_output.split())} → {len(your_correction.split())} words"
        )

        # Log correction
        self.log_correction(
            post, gemini_output, your_correction, differences, platform, language
        )

        # Ask for notes
        notes = input("\n💭 Any notes on what you changed? (optional): ").strip()

        # Schedule corrected version
        decision = self.scheduler.schedule_rewritten_post(
            rewritten_content={
                "rewritten_content": your_correction,
                "viral_potential": 50,
                "time_sensitivity": "evergreen",
                "platform": platform,
            },
            platform_override=platform,
        )

        # Save scheduled post
        scheduled_post = {
            "id": f"{platform}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "source_post": {
                "title": post.get("title", ""),
                "url": post.get("url", ""),
                "platform": post.get("platform", ""),
            },
            "rewritten_content": your_correction,
            "platform": platform,
            "language": language,
            "persona": "qronoya",
            "scheduled_for": decision.when.isoformat(),
            "priority": decision.priority,
            "reason": decision.reason,
            "status": "corrected",
            "correction_notes": notes,
            "metadata": {
                "corrected_at": datetime.now().isoformat(),
                "original_gemini_output": gemini_output,
            },
        }

        filepath = self.scheduled_dir / f"{scheduled_post['id']}.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(scheduled_post, f, ensure_ascii=False, indent=2)

        print(f"\n📅 Scheduled for: {decision.when.strftime('%Y-%m-%d %H:%M')}")
        print(f"💾 Saved to: {filepath}")

        return "corrected"

    def handle_rejection(self, post: Dict, gemini_output: str) -> str:
        """Handle rejected rewrite"""

        print("\n❌ Rejected")

        notes = input("\n💭 Why rejected? (helps improve system): ").strip()

        # Log rejection
        rejection_data = {
            "id": f"rejected_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "source_post": {
                "title": post.get("title", ""),
                "url": post.get("url", ""),
                "platform": post.get("platform", ""),
            },
            "gemini_output": gemini_output,
            "persona": "qronoya",
            "status": "rejected",
            "rejection_reason": notes,
        }

        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = self.corrections_dir / f"{date_str}_corrections.jsonl"

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(rejection_data, ensure_ascii=False) + "\n")

        return "rejected"

    def log_approved(self, post: Dict, rewrite: str, platform: str, language: str):
        """Log approved rewrite for training"""

        approved_data = {
            "id": f"approved_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "source_post": {
                "title": post.get("title", ""),
                "content": post.get("content", ""),
                "url": post.get("url", ""),
                "platform": post.get("platform", ""),
            },
            "persona": "qronoya",
            "gemini_output": rewrite,
            "platform": platform,
            "language": language,
            "status": "approved",
        }

        count = len(list(self.approved_dir.glob("qronoya_*.json"))) + 1
        filepath = self.approved_dir / f"qronoya_approved_{count:03d}.json"

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(approved_data, f, ensure_ascii=False, indent=2)

    def log_correction(
        self,
        post: Dict,
        gemini_output: str,
        your_correction: str,
        differences: dict,
        platform: str,
        language: str,
    ):
        """Log correction for training"""

        correction_data = {
            "id": f"correction_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "timestamp": datetime.now().isoformat(),
            "source_post": {
                "title": post.get("title", ""),
                "content": post.get("content", ""),
                "url": post.get("url", ""),
                "platform": post.get("platform", ""),
            },
            "gemini_output": gemini_output,
            "your_correction": your_correction,
            "persona": "qronoya",
            "platform": platform,
            "language": language,
            "status": "corrected",
            "differences": differences,
        }

        date_str = datetime.now().strftime("%Y-%m-%d")
        filepath = self.corrections_dir / f"{date_str}_corrections.jsonl"

        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(correction_data, ensure_ascii=False) + "\n")

    def get_user_input(self, prompt: str, valid_options: list = None) -> str:
        """Get user input with validation"""
        while True:
            response = input(prompt).strip().lower()
            if valid_options is None or response in valid_options:
                return response
            print(f"Invalid option. Please choose from: {', '.join(valid_options)}")

    def open_editor(self, initial_text: str = "") -> str:
        """Open system editor for text input"""
        editor = os.environ.get("EDITOR", "nano")

        with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as tf:
            tf.write(initial_text)
            tf.flush()
            temp_path = tf.name

        try:
            subprocess.call([editor, temp_path])
            with open(temp_path, "r", encoding="utf-8") as f:
                edited_text = f.read().strip()
            return edited_text
        finally:
            os.unlink(temp_path)

    def show_side_by_side(self, gemini_output: str, your_correction: str):
        """Display side-by-side comparison"""
        print("\n" + "=" * 100)
        print("COMPARISON: Gemini vs Your Correction")
        print("=" * 100)

        gemini_lines = gemini_output.split("\n")
        your_lines = your_correction.split("\n")
        max_lines = max(len(gemini_lines), len(your_lines))

        print(f"\n{'GEMINI OUTPUT':<50} | {'YOUR CORRECTION':<50}")
        print("-" * 50 + "-+-" + "-" * 50)

        for i in range(max_lines):
            gemini_line = gemini_lines[i] if i < len(gemini_lines) else ""
            your_line = your_lines[i] if i < len(your_lines) else ""

            gemini_line = (
                gemini_line[:47] + "..." if len(gemini_line) > 50 else gemini_line
            )
            your_line = your_line[:47] + "..." if len(your_line) > 50 else your_line

            print(f"{gemini_line:<50} | {your_line:<50}")

        print("\n" + "=" * 100)

    def analyze_differences(self, gemini_output: str, your_correction: str) -> dict:
        """Analyze differences between Gemini and your correction"""

        gemini_words = set(gemini_output.lower().split())
        your_words = set(your_correction.lower().split())

        added_words = your_words - gemini_words
        removed_words = gemini_words - your_words

        # Detect structure differences
        gemini_has_numbers = any(
            line.strip().startswith(("1/", "2/", "3/", "1.", "2.", "3."))
            for line in gemini_output.split("\n")
        )
        your_has_numbers = any(
            line.strip().startswith(("1/", "2/", "3/", "1.", "2.", "3."))
            for line in your_correction.split("\n")
        )

        structure_diff = "none"
        if gemini_has_numbers and not your_has_numbers:
            structure_diff = "removed_numbered_thread"
        elif not gemini_has_numbers and your_has_numbers:
            structure_diff = "added_numbered_thread"

        return {
            "added_words": list(added_words)[:20],
            "removed_words": list(removed_words)[:20],
            "structure_change": structure_diff,
            "length_ratio": len(your_correction) / len(gemini_output)
            if len(gemini_output) > 0
            else 0,
        }

    def show_session_summary(self, stats: dict):
        """Show session summary"""

        corrections_count = len(list(self.corrections_dir.glob("*.jsonl")))
        approved_count = len(list(self.approved_dir.glob("*.json")))
        scheduled_count = len(list(self.scheduled_dir.glob("*.json")))

        print(f"\n{'='*100}")
        print("📊 SESSION SUMMARY")
        print("=" * 100)
        print(f"Total reviewed: {stats['total']}")
        print(f"  ✅ Approved: {stats['approved']}")
        print(f"  ✏️  Corrected: {stats['corrected']}")
        print(f"  ❌ Rejected: {stats['rejected']}")
        print(f"  ⏭️  Skipped: {stats['skipped']}")
        print()
        print(f"📁 Data saved:")
        print(f"  • Corrections logged: {corrections_count} files")
        print(f"  • Approved rewrites: {approved_count} files")
        print(f"  • Scheduled posts: {scheduled_count} files")
        print()
        print(f"🚀 Next steps:")
        print(
            f"  • Continue reviewing: python review_and_publish_from_database.py --limit 10"
        )
        print(f"  • After 10-20 reviews: python scripts/update_voice_model.py")
        print(
            f"  • View scheduled posts: python review_and_publish_from_database.py --show-schedule"
        )
        print("=" * 100)


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="Review & Publish from Database")
    parser.add_argument(
        "--limit", type=int, default=5, help="Number of posts to review (default: 5)"
    )
    parser.add_argument(
        "--platform",
        choices=["threads", "twitter", "reddit", "telegram"],
        help="Filter by platform",
    )
    parser.add_argument(
        "--show-schedule", action="store_true", help="Show scheduled posts"
    )

    args = parser.parse_args()

    workflow = DatabaseReviewWorkflow()

    if args.show_schedule:
        # Show scheduled posts
        scheduled = list(workflow.scheduled_dir.glob("*.json"))
        print(f"\n📅 Scheduled posts: {len(scheduled)}")
        for filepath in sorted(scheduled)[:10]:
            with open(filepath, "r") as f:
                post = json.load(f)
                print(f"\n  [{post['platform'].upper()}] [{post['language'].upper()}]")
                print(f"  Scheduled: {post['scheduled_for']}")
                print(f"  Content: {post['rewritten_content'][:80]}...")
        return

    # Start review session
    await workflow.start_review_session(limit=args.limit, platform_filter=args.platform)


if __name__ == "__main__":
    asyncio.run(main())
