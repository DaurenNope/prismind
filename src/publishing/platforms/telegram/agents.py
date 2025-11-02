#!/usr/bin/env python3
"""
Telegram Bot Agent Commands Extension
New commands for GitHub research, book analysis, and content rewriting
"""

import logging
import html
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.services.content_rewriter import get_rewriter
from src.agents.github_research_agent import get_github_agent
from src.agents.librarian_book_agent import get_librarian
from src.services.new_database_manager import get_database_manager

logger = logging.getLogger(__name__)


async def research_repo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Deep research on a GitHub repository
    Usage: /research_repo <github_url>
    """
    args = context.args or []
    
    if not args:
        await update.message.reply_text(
            "🛠️ <b>GitHub Repository Research</b>\n\n"
            "Usage: /research_repo &lt;github_url&gt;\n\n"
            "Example:\n"
            "/research_repo https://github.com/openai/whisper\n\n"
            "This will analyze:\n"
            "• TLDR summary\n"
            "• Use cases\n"
            "• Key features\n"
            "• Quality assessment\n"
            "• Target audience\n"
            "• Rewrite angles for each persona",
            parse_mode=ParseMode.HTML
        )
        return
    
    repo_url = args[0]
    
    if "github.com" not in repo_url:
        await update.message.reply_text("❌ Please provide a valid GitHub URL")
        return
    
    msg = await update.message.reply_text(f"🔬 Researching {repo_url}...")
    
    try:
        # Run deep research
        agent = get_github_agent()
        report = await agent.research_repo(repo_url)
        
        if "error" in report:
            await msg.edit_text(f"❌ Research failed: {report['error']}")
            return
        
        # Format response
        lines = [
            "🛠️ <b>GitHub Repository Analysis</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"<b>📦 {html.escape(report['name'])}</b>",
            f"⭐ {report['stars']:,} stars • {report['language']}\n",
            f"<b>TLDR:</b>",
            html.escape(report['tldr'])[:300],
            "\n<b>Use Cases:</b>"
        ]
        
        for use_case in report['use_cases'][:5]:
            lines.append(f"  • {html.escape(use_case)}")
        
        lines.append("\n<b>Key Features:</b>")
        for feature in report['key_features'][:5]:
            lines.append(f"  • {html.escape(feature)}")
        
        lines.append(f"\n<b>Why It Matters:</b>")
        lines.append(html.escape(report['why_matters']))
        
        lines.append(f"\n<b>Quality Score:</b> {report['quality_assessment']['overall_score']}/10")
        lines.append(f"<b>Recommendation:</b> {html.escape(report['quality_assessment']['recommendation'])}")
        
        lines.append(f"\n<b>Target Audience:</b>")
        lines.append(", ".join(report['target_audience'][:3]))
        
        lines.append(f"\n💡 <b>Rewrite Angles:</b> {len(report['rewrite_angles'])} personas available")
        lines.append(f"\nUse /rewrite with this repo's post ID to transform for different personas")
        
        await msg.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Research repo failed: {e}")
        await msg.edit_text(f"❌ Research error: {e}")


async def get_book_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Download and analyze a book
    Usage: /get_book <book title> [author]
    """
    args = context.args or []
    
    if not args:
        await update.message.reply_text(
            "📚 <b>Book Download & Analysis</b>\n\n"
            "Usage: /get_book &lt;book title&gt; [author]\n\n"
            "Example:\n"
            "/get_book Building a Second Brain Tiago Forte\n\n"
            "This will:\n"
            "• Search multiple sources\n"
            "• Download PDF/EPUB\n"
            "• Extract key concepts\n"
            "• Generate TLDR\n"
            "• Identify practical applications\n"
            "• Create rewrite angles",
            parse_mode=ParseMode.HTML
        )
        return
    
    # Parse title and author
    text = " ".join(args)
    
    # Simple heuristic: if last 2-3 words look like name, treat as author
    words = text.split()
    if len(words) > 3:
        title = " ".join(words[:-2])
        author = " ".join(words[-2:])
    else:
        title = text
        author = None
    
    msg = await update.message.reply_text(f"📚 Processing: {title}...")
    
    try:
        # Run librarian agent
        librarian = get_librarian()
        report = await librarian.discover_and_analyze(title, author)
        
        if report['status'] == "error":
            await msg.edit_text(f"❌ Error: {report.get('error', 'Unknown error')}")
            return
        
        if report['status'] == "not_found":
            await msg.edit_text(
                f"❌ Book not found: {title}\n\n"
                "Try:\n"
                "• Check spelling\n"
                "• Include author name\n"
                "• Try different title variation"
            )
            return
        
        # Format response
        lines = [
            "📚 <b>Book Analysis Complete</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"<b>{html.escape(report['title'])}</b>",
            f"by {html.escape(report.get('author', 'Unknown'))}\n",
            f"<b>TLDR:</b>",
            html.escape(report['tldr'])[:300],
            "\n<b>Key Concepts:</b>"
        ]
        
        for concept in report['key_concepts'][:5]:
            lines.append(f"  • {html.escape(concept)}")
        
        if report.get('frameworks'):
            lines.append("\n<b>Frameworks:</b>")
            for name, desc in list(report['frameworks'].items())[:3]:
                lines.append(f"  • {html.escape(name)}")
        
        lines.append("\n<b>Practical Applications:</b>")
        for app in report['practical_applications'][:3]:
            lines.append(f"  • {html.escape(app)}")
        
        lines.append(f"\n<b>Category:</b> {report['category']}")
        lines.append(f"<b>Target Audience:</b> {', '.join(report['target_audience'][:2])}")
        lines.append(f"<b>Reading Time:</b> ~{report['reading_time_hours']:.1f} hours")
        
        lines.append(f"\n📁 <b>File:</b> {report['file_path']}")
        lines.append(f"💡 <b>Rewrite angles:</b> {len(report['rewrite_angles'])} available")
        
        await msg.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Get book failed: {e}")
        await msg.edit_text(f"❌ Book processing error: {e}")


async def rewrite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Rewrite content for a specific persona
    Usage: /rewrite <post_id> <persona> [platform]
    """
    args = context.args or []
    
    if len(args) < 2:
        await update.message.reply_text(
            "✍️ <b>Content Rewriter</b>\n\n"
            "Usage: /rewrite &lt;post_id&gt; &lt;persona&gt; [platform]\n\n"
            "Personas:\n"
            "  🔧 technical - Deep technical analysis\n"
            "  🚀 builder - Practical applications\n"
            "  📚 learner - Beginner-friendly\n"
            "  🔥 trendsetter - What's trending\n"
            "  💡 thought_leader - Big picture\n\n"
            "Platforms: twitter, linkedin, blog\n\n"
            "Example:\n"
            "/rewrite abc123 builder twitter\n\n"
            "Use /latest to see post IDs\n"
            "Use /personas to list all personas",
            parse_mode=ParseMode.HTML
        )
        return
    
    post_id = args[0]
    persona = args[1].lower()
    platform = args[2].lower() if len(args) > 2 else "twitter"
    
    valid_personas = ["technical", "builder", "learner", "trendsetter", "thought_leader"]
    if persona not in valid_personas:
        await update.message.reply_text(
            f"❌ Invalid persona: {persona}\n\n"
            f"Valid personas: {', '.join(valid_personas)}\n"
            "Use /personas for details"
        )
        return
    
    msg = await update.message.reply_text(f"✍️ Rewriting as {persona} for {platform}...")
    
    try:
        # Get post
        db = get_database_manager()
        post = db.get_post_by_id(post_id)
        
        if not post:
            await msg.edit_text(f"❌ Post not found: {post_id}")
            return
        
        # Prepare content for rewriting
        content = {
            "type": post.get("platform", "article"),
            "url": post.get("url", ""),
            "title": post.get("title", ""),
            "content": post.get("content", ""),
            "content_summary": post.get("content_summary", ""),
            # Add any agent analysis if available
            "tldr": post.get("tldr", ""),
            "use_cases": post.get("use_cases", []),
            "key_features": post.get("key_features", []),
            "rewrite_angles": post.get("rewrite_angles", [])
        }
        
        # Rewrite
        rewriter = get_rewriter()
        result = await rewriter.rewrite_for_persona(content, persona, platform)
        
        if "error" in result:
            await msg.edit_text(f"❌ Rewrite failed: {result['error']}")
            return
        
        # Format response
        lines = [
            f"{result['persona_emoji']} <b>{persona.upper()} VERSION</b>",
            f"Platform: {platform.title()}",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            html.escape(result['rewritten_content']),
            f"\n<b>Angle:</b> {html.escape(result.get('angle_used', 'N/A'))}",
            f"<b>Hook:</b> {html.escape(result.get('hook', 'N/A'))}"
        ]
        
        await msg.edit_text("\n".join(lines), parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Rewrite failed: {e}")
        await msg.edit_text(f"❌ Rewrite error: {e}")


async def personas_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    List all available personas
    Usage: /personas
    """
    
    rewriter = get_rewriter()
    personas = rewriter.get_available_personas()
    
    lines = [
        "🎭 <b>Available Personas</b>",
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
    ]
    
    for persona in personas:
        lines.append(f"{persona['emoji']} <b>{persona['name']}</b>")
        lines.append(f"   ID: <code>{persona['id']}</code>")
        lines.append(f"   Audience: {persona['audience']}")
        lines.append(f"   Style: {persona['style']}\n")
    
    lines.append("💡 <b>Usage:</b>")
    lines.append("/rewrite &lt;post_id&gt; &lt;persona_id&gt; [platform]")
    lines.append("\nExample:")
    lines.append("/rewrite abc123 builder twitter")
    
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)


async def library_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    View book library statistics
    Usage: /library
    """
    
    try:
        librarian = get_librarian()
        stats = librarian.get_library_stats()
        
        lines = [
            "📚 <b>Book Library</b>",
            "━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"<b>Total Books:</b> {stats['total_books']}",
            f"<b>Total Size:</b> {stats['total_size_mb']:.2f} MB",
            f"<b>Location:</b> <code>{html.escape(stats['library_path'])}</code>\n"
        ]
        
        if stats['books']:
            lines.append("<b>Books:</b>")
            for book in stats['books'][:10]:
                lines.append(f"  📖 {html.escape(book)}")
            
            if len(stats['books']) > 10:
                lines.append(f"  ... and {len(stats['books']) - 10} more")
        else:
            lines.append("No books yet. Use /get_book to add books!")
        
        lines.append("\n💡 Use /get_book &lt;title&gt; to download and analyze books")
        
        await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.HTML)
        
    except Exception as e:
        logger.error(f"Library command failed: {e}")
        await update.message.reply_text(f"❌ Library error: {e}")
