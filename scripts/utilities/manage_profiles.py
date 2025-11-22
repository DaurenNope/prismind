#!/usr/bin/env python3
"""
Profile Management Helper Script
Manage the 3-profile system: Qronoya, Aspandead, Claimzilla
"""

import json
from pathlib import Path
from typing import Any, Dict, List


class ProfileManager:
    """Manage persona profiles and their configurations"""

    def __init__(self):
        self.config_dir = Path(__file__).parent / "config" / "personas"
        self.profiles = ["qronoya", "aspandead", "claimzilla"]

    def list_profiles(self) -> None:
        """List all profiles with their key info"""
        print("\n" + "=" * 80)
        print("PRISMIND PROFILES")
        print("=" * 80 + "\n")

        for profile in self.profiles:
            config_file = self.config_dir / f"{profile}.json"
            if config_file.exists():
                with open(config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                print(f"📋 {data['name'].upper()} (@{data['handle']})")
                print(f"   Language: {data['transformation_settings']['language']}")
                print(f"   Platforms: {', '.join(data.get('platforms', []))}")
                print(f"   Voice: {data['voice_description'][:100]}...")
                print(f"   Expertise: {', '.join(data['expertise'][:3])}...")
                print()

    def check_voice_examples(self) -> None:
        """Check which profiles have voice examples filled in"""
        print("\n" + "=" * 80)
        print("VOICE EXAMPLES STATUS")
        print("=" * 80 + "\n")

        for profile in self.profiles:
            examples_file = self.config_dir / f"{profile}_examples.json"
            if examples_file.exists():
                with open(examples_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    examples = data.get("examples", [])
                    filled = sum(1 for ex in examples if ex.get("content", "").strip())
                    total = len(examples)

                    status = "✅" if filled >= 10 else "⚠️" if filled > 0 else "❌"
                    print(
                        f"{status} {profile.upper()}: {filled}/{total} examples filled"
                    )
                    if filled < 10:
                        print(
                            f"   → Need {10 - filled} more examples for voice authenticity"
                        )
            else:
                print(f"❌ {profile.upper()}: Examples file not found")

            print()

    def validate_configurations(self) -> None:
        """Validate all profile configurations"""
        print("\n" + "=" * 80)
        print("CONFIGURATION VALIDATION")
        print("=" * 80 + "\n")

        required_fields = [
            "name",
            "handle",
            "voice_description",
            "expertise",
            "platforms",
            "transformation_settings",
        ]

        for profile in self.profiles:
            config_file = self.config_dir / f"{profile}.json"
            if not config_file.exists():
                print(f"❌ {profile.upper()}: Config file missing")
                continue

            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            missing = [field for field in required_fields if field not in data]

            if missing:
                print(f"⚠️  {profile.upper()}: Missing fields: {', '.join(missing)}")
            else:
                # Check language setting
                lang = data["transformation_settings"].get("language", "unknown")
                expected_lang = {
                    "qronoya": "russian",
                    "aspandead": "english",
                    "claimzilla": "english",
                }

                lang_status = "✅" if lang == expected_lang[profile] else "❌"
                print(f"{lang_status} {profile.upper()}: All required fields present")
                print(f"   Language: {lang} (expected: {expected_lang[profile]})")

            print()

    def show_profile_summary(self, profile: str) -> None:
        """Show detailed summary of a specific profile"""
        if profile not in self.profiles:
            print(f"❌ Unknown profile: {profile}")
            print(f"Available profiles: {', '.join(self.profiles)}")
            return

        config_file = self.config_dir / f"{profile}.json"
        if not config_file.exists():
            print(f"❌ Config file not found: {config_file}")
            return

        with open(config_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        print("\n" + "=" * 80)
        print(f"{data['name'].upper()} PROFILE SUMMARY")
        print("=" * 80 + "\n")

        print(f"Handle: @{data['handle']}")
        print(f"Table: {data.get('table_name', 'N/A')}")
        print(f"Language: {data['transformation_settings']['language']}")
        print(f"Platforms: {', '.join(data.get('platforms', []))}")
        print()

        print("VOICE DESCRIPTION:")
        print(f"  {data['voice_description']}")
        print()

        print("EXPERTISE:")
        for exp in data["expertise"]:
            print(f"  • {exp}")
        print()

        print("KEYWORDS:")
        keywords = data.get("filters", {}).get("keywords", [])
        print(f"  {', '.join(keywords[:10])}...")
        print()

        print("PERSONALITY PROMPT:")
        prompt = data["transformation_settings"].get("personality_prompt", "")
        print(f"  {prompt[:200]}...")
        print()

        # Check voice examples
        examples_file = self.config_dir / f"{profile}_examples.json"
        if examples_file.exists():
            with open(examples_file, "r", encoding="utf-8") as f:
                ex_data = json.load(f)
                examples = ex_data.get("examples", [])
                filled = sum(1 for ex in examples if ex.get("content", "").strip())
                print(f"VOICE EXAMPLES: {filled}/{len(examples)} filled")
        else:
            print("VOICE EXAMPLES: Not found")

        print()

    def interactive_menu(self) -> None:
        """Interactive menu for profile management"""
        while True:
            print("\n" + "=" * 80)
            print("PROFILE MANAGER - MAIN MENU")
            print("=" * 80)
            print("\n1. List all profiles")
            print("2. Check voice examples status")
            print("3. Validate configurations")
            print("4. Show profile summary (qronoya/aspandead/claimzilla)")
            print("5. Exit")
            print()

            choice = input("Select option (1-5): ").strip()

            if choice == "1":
                self.list_profiles()
            elif choice == "2":
                self.check_voice_examples()
            elif choice == "3":
                self.validate_configurations()
            elif choice == "4":
                profile = (
                    input("Enter profile name (qronoya/aspandead/claimzilla): ")
                    .strip()
                    .lower()
                )
                self.show_profile_summary(profile)
            elif choice == "5":
                print("\n👋 Goodbye!")
                break
            else:
                print("\n❌ Invalid choice. Please select 1-5.")

            input("\nPress Enter to continue...")


def main():
    """Main entry point"""
    import sys

    manager = ProfileManager()

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()

        if command == "list":
            manager.list_profiles()
        elif command == "examples":
            manager.check_voice_examples()
        elif command == "validate":
            manager.validate_configurations()
        elif command == "show" and len(sys.argv) > 2:
            manager.show_profile_summary(sys.argv[2])
        else:
            print("Usage:")
            print("  python manage_profiles.py list          - List all profiles")
            print("  python manage_profiles.py examples      - Check voice examples")
            print("  python manage_profiles.py validate      - Validate configurations")
            print("  python manage_profiles.py show <profile> - Show profile summary")
            print("  python manage_profiles.py               - Interactive menu")
    else:
        manager.interactive_menu()


if __name__ == "__main__":
    main()
