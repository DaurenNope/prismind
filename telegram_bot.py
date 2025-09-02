#!/usr/bin/env python3
"""
Telegram Bot for Prismind News Digests
Sends news digests and allows on-demand content requests
"""

import os
import sys
import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append('.')

from news_digest_generator import NewsDigestGenerator

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
except ImportError:
    print("❌ python-telegram-bot not installed. Install with: pip install python-telegram-bot")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class PrismindTelegramBot:
    def __init__(self):
        self.token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.allowed_users = os.getenv('TELEGRAM_ALLOWED_USERS', '').split(',')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        self.webhook_url = os.getenv('TELEGRAM_WEBHOOK_URL')
        self.listen_host = os.getenv('TELEGRAM_WEBHOOK_LISTEN', '0.0.0.0')
        self.listen_port = int(os.getenv('PORT', os.getenv('TELEGRAM_WEBHOOK_PORT', '8443')))
        self.news_generator = NewsDigestGenerator()
        
        # Temporarily allow all users for testing
        self.allowed_users = []
        
        if not self.token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in .env file")
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user_id = str(update.effective_user.id)
        
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
        
        welcome_message = """
🤖 **Welcome to Prismind News Bot!**

I'm your AI assistant that curates the best content from your bookmarks.

**Quick Actions:**
        """
        
        # Create inline keyboard with buttons
        keyboard = [
            [
                InlineKeyboardButton("📰 Daily Digest", callback_data="daily"),
                InlineKeyboardButton("📊 Weekly Report", callback_data="weekly")
            ],
            [
                InlineKeyboardButton("🔥 Top Posts", callback_data="top"),
                InlineKeyboardButton("🔍 Search", callback_data="search")
            ],
            [
                InlineKeyboardButton("🤖 AI News", callback_data="ai"),
                InlineKeyboardButton("💻 Tech News", callback_data="tech")
            ],
            [
                InlineKeyboardButton("📚 Help", callback_data="help")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📚 **Prismind News Bot Help**

**Commands:**
• `/daily` - Today's news digest
• `/weekly` - This week's news digest  
• `/tech` - Technology news
• `/ai` - AI-related news
• `/business` - Business news
• `/top` - Top posts by value score
• `/help` - Show this help

**🔍 Natural Language Search Examples:**
• "find me data about tensor charts"
• "show me AI news from last week"
• "what's new in machine learning?"
• "find posts about cryptocurrency"
• "show me the best tech posts"
• "find content about Python programming"
• "what are the top posts about blockchain?"

**How it works:**
1. Your bookmarked posts are analyzed by AI
2. Content is categorized and scored
3. I format it into readable news articles
4. You get curated digests on demand
5. Smart search finds relevant content

**Value Scores:**
⭐ 8-10: Must-read content
⭐ 6-7: Worth checking out
⭐ 4-5: Interesting but not urgent
⭐ 1-3: Basic information
        """
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def chat_id_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /id command - return chat and user IDs"""
        try:
            chat_id = update.effective_chat.id if update.effective_chat else None
            user_id = update.effective_user.id if update.effective_user else None
            await update.message.reply_text(f"Chat ID: {chat_id}\nYour User ID: {user_id}")
        except Exception:
            await update.message.reply_text("❌ Could not retrieve IDs here. Try DMing @userinfobot.")
    
    def search_posts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search posts using natural language query"""
        try:
            # Get all posts
            all_posts = self.news_generator.db.get_posts(limit=1000)
            
            # Convert query to lowercase for matching
            query_lower = query.lower()
            
            # Define search patterns
            search_patterns = {
                'tensor': ['tensor', 'tensorflow', 'pytorch', 'machine learning', 'ml', 'ai'],
                'charts': ['chart', 'graph', 'visualization', 'plot', 'data viz'],
                'crypto': ['crypto', 'cryptocurrency', 'bitcoin', 'ethereum', 'blockchain'],
                'ai': ['ai', 'artificial intelligence', 'machine learning', 'ml', 'neural'],
                'python': ['python', 'programming', 'code', 'developer'],
                'tech': ['tech', 'technology', 'software', 'startup'],
                'business': ['business', 'startup', 'entrepreneur', 'company'],
                'last week': ['recent', 'new', 'latest'],
                'best': ['top', 'best', 'high value', 'high score']
            }
            
            # Find matching posts
            matching_posts = []
            
            for post in all_posts:
                title = (post.get('title') or '').lower()
                content = (post.get('content') or '').lower()
                ai_summary = (post.get('ai_summary') or '').lower()
                category = (post.get('category') or '').lower()
                
                # Check if query matches any part of the post
                score = 0
                
                # Direct keyword matching
                if query_lower in title:
                    score += 10
                if query_lower in content:
                    score += 5
                if query_lower in ai_summary:
                    score += 8
                if query_lower in category:
                    score += 7
                
                # Pattern matching
                for pattern_key, pattern_words in search_patterns.items():
                    if pattern_key in query_lower:
                        for word in pattern_words:
                            if word in title or word in content or word in ai_summary:
                                score += 3
                
                # Time-based filtering
                if 'last week' in query_lower or 'recent' in query_lower:
                    created_at = post.get('created_at')
                    if created_at:
                        try:
                            if isinstance(created_at, str):
                                created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            if (datetime.now() - created_at).days <= 7:
                                score += 2
                        except:
                            pass
                
                # Value score boosting
                if 'best' in query_lower or 'top' in query_lower:
                    value_score = post.get('value_score', 0) or 0
                    score += value_score * 0.5
                
                if score > 0:
                    matching_posts.append((post, score))
            
            # Sort by relevance score
            matching_posts.sort(key=lambda x: x[1], reverse=True)
            
            # Return top results
            return [post for post, score in matching_posts[:limit]]
            
        except Exception as e:
            logger.error(f"Error searching posts: {e}")
            return []
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle button callbacks"""
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        if self.allowed_users and user_id not in self.allowed_users:
            await query.edit_message_text("❌ You are not authorized to use this bot.")
            return
        
        data = query.data
        
        try:
            if data == "daily":
                await query.edit_message_text("📰 Generating daily digest...")
                digest = self.news_generator.generate_daily_digest()
                # Get the actual posts for button generation
                recent_posts = self.news_generator.get_recent_posts(days=1, limit=5)
                await self.send_formatted_digest(query, digest, "Daily Digest", recent_posts)
                
            elif data == "weekly":
                await query.edit_message_text("📊 Generating weekly report...")
                digest = self.news_generator.generate_weekly_digest()
                await self.send_formatted_digest(query, digest, "Weekly Report")
                
            elif data == "top":
                await query.edit_message_text("🔥 Getting top posts...")
                top_posts = self.news_generator.get_top_posts(limit=5)
                await self.send_formatted_posts(query, top_posts, "Top Posts")
                
            elif data == "ai":
                await query.edit_message_text("🤖 Getting AI news...")
                digest = self.news_generator.generate_category_digest("AI")
                await self.send_formatted_digest(query, digest, "AI News")
                
            elif data == "tech":
                await query.edit_message_text("💻 Getting tech news...")
                digest = self.news_generator.generate_category_digest("Technology")
                await self.send_formatted_digest(query, digest, "Tech News")
                
            elif data == "search":
                await query.edit_message_text(
                    "🔍 **Search Your Bookmarks**\n\n"
                    "Just type what you're looking for:\n"
                    "• 'find me data about tensor charts'\n"
                    "• 'show me AI news'\n"
                    "• 'what's new in productivity?'\n"
                    "• 'find posts about cryptocurrency'",
                    parse_mode='Markdown'
                )
                
            elif data == "help":
                await self.show_help(query)
                
            elif data.startswith("read_post_"):
                post_id = data.replace("read_post_", "")
                await self.show_post_details(query, post_id)
                
            elif data == "back_to_menu":
                await self.show_main_menu(query)
                
        except Exception as e:
            logger.error(f"Error handling button callback: {e}")
            await query.edit_message_text("❌ Error processing request. Please try again.")
    
    async def send_formatted_digest(self, query, digest: str, title: str, posts: List[Dict] = None):
        """Send a formatted digest with post buttons"""
        try:
            # Create simple numbered buttons based on the digest content
            keyboard = []
            
            # If we have posts data, use that for button count
            if posts:
                post_count = len(posts)
                print(f"DEBUG: Using posts data, found {post_count} posts")
            else:
                # Count the number of posts in the digest (lines starting with 🔥, 💡, or 📝)
                lines = digest.split('\n')
                post_count = 0
                for line in lines:
                    # Look for lines that start with emoji and have a number (like "🔥 **1.**")
                    if line.strip().startswith(('🔥', '💡', '📝')) and ('**' in line and any(char.isdigit() for char in line)):
                        post_count += 1
                        print(f"DEBUG: Found post line: {line.strip()}")
                
                print(f"DEBUG: Found {post_count} posts in digest")
            
            # Create buttons for each post
            for i in range(1, min(post_count + 1, 6)):  # Max 5 buttons
                keyboard.append([InlineKeyboardButton(f"📖 Read Post {i}", callback_data=f"read_post_{i}")])
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            print(f"DEBUG: Created {len(keyboard)-1} post buttons")
            
            await query.edit_message_text(
                f"📰 **{title}**\n\n{digest}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error sending formatted digest: {e}")
            print(f"DEBUG: Exception in send_formatted_digest: {e}")
            # Fallback to simple format
            keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"📰 **{title}**\n\n{digest}",
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    async def send_formatted_posts(self, query, posts: List[Dict], title: str):
        """Send formatted posts with individual buttons"""
        if not posts:
            await query.edit_message_text(
                f"❌ No {title.lower()} found.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")
                ]])
            )
            return
        
        # Create main message with post list
        message = f"🔥 **{title}**\n\n"
        
        keyboard = []
        for i, post in enumerate(posts[:5], 1):
            title_text = post.get('title', 'No title')[:40] + "..." if len(post.get('title', '')) > 40 else post.get('title', 'No title')
            message += f"**{i}.** {title_text}\n"
            keyboard.append([InlineKeyboardButton(f"📖 Read Post {i}", callback_data=f"read_post_{post.get('id')}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=reply_markup)
    
    def _build_post_buttons(self, posts: List[Dict]) -> InlineKeyboardMarkup:
        """Build inline keyboard with numbered Read Post buttons and Back button"""
        keyboard: List[List[InlineKeyboardButton]] = []
        post_count = min(len(posts or []), 5)
        for i in range(1, post_count + 1):
            keyboard.append([InlineKeyboardButton(f"📖 Read Post {i}", callback_data=f"read_post_{i}")])
        keyboard.append([InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")])
        return InlineKeyboardMarkup(keyboard)
    
    async def show_help(self, query):
        """Show help with buttons"""
        help_text = """
📚 **How to Use Prismind Bot**

**Quick Actions:**
• Use buttons for instant access
• Type natural language queries
• Get personalized digests

**Examples:**
• "find me data about tensor charts"
• "show me AI news from last week"
• "what's new in machine learning?"

**Value Scores:**
🔥 8-10: Must-read content
💡 6-7: Worth checking out
📝 4-5: Interesting but not urgent
        """
        
        keyboard = [[InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(help_text, parse_mode='Markdown', reply_markup=reply_markup)
    
    async def show_post_details(self, query, post_id: str):
        """Show detailed post information"""
        try:
            # Try to get post by ID, if that fails, get recent posts and find by index
            try:
                post = self.news_generator.db.get_post_by_id(post_id)
            except:
                # Fallback: get recent posts and find by index
                recent_posts = self.news_generator.get_recent_posts(days=7, limit=10)
                try:
                    index = int(post_id) - 1
                    if 0 <= index < len(recent_posts):
                        post = recent_posts[index]
                    else:
                        post = None
                except:
                    post = None
            
            if not post:
                await query.edit_message_text(
                    "❌ Post not found.",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")
                    ]])
                )
                return
            
            # Format post details
            title = post.get('title', 'No title')
            content = post.get('content', 'No content')
            ai_summary = post.get('ai_summary', '')
            category = post.get('category', 'General')
            value_score = post.get('value_score', 0)
            author = post.get('author', 'Unknown')
            url = post.get('url', '')
            
            # Use AI summary if available
            summary = ai_summary if ai_summary else content[:300] + "..." if len(content) > 300 else content
            
            # Create detailed post view
            post_text = f"""
📰 **{title}**

{summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👤 **Author:** {author}
🏷️ **Category:** {category}
⭐ **Value Score:** {value_score}/10
🔗 **Source:** [Read Full Post]({url})
            """
            
            # Create keyboard with back button
            keyboard = [
                [InlineKeyboardButton("🔗 Open Original", url=url)],
                [InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                post_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error showing post details: {e}")
            await query.edit_message_text(
                "❌ Error loading post details.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Menu", callback_data="back_to_menu")
                ]])
            )
    
    async def show_main_menu(self, query):
        """Show main menu with buttons"""
        welcome_message = """
🤖 **Welcome to Prismind News Bot!**

I'm your AI assistant that curates the best content from your bookmarks.

**Quick Actions:**
        """
        
        # Create inline keyboard with buttons
        keyboard = [
            [
                InlineKeyboardButton("📰 Daily Digest", callback_data="daily"),
                InlineKeyboardButton("📊 Weekly Report", callback_data="weekly")
            ],
            [
                InlineKeyboardButton("🔥 Top Posts", callback_data="top"),
                InlineKeyboardButton("🔍 Search", callback_data="search")
            ],
            [
                InlineKeyboardButton("🤖 AI News", callback_data="ai"),
                InlineKeyboardButton("💻 Tech News", callback_data="tech")
            ],
            [
                InlineKeyboardButton("📚 Help", callback_data="help")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            welcome_message, 
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def handle_search_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle natural language search queries"""
        user_id = str(update.effective_user.id)
        
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
        
        query = update.message.text.strip()
        
        # Skip if it's a command
        if query.startswith('/'):
            return
        
        await update.message.reply_text(f"🔍 Searching for: '{query}'...")
        
        try:
            # Search for relevant posts
            matching_posts = self.search_posts(query, limit=5)
            
            if not matching_posts:
                await update.message.reply_text(
                    f"❌ No posts found matching '{query}'.\n\n"
                    "💡 Try different keywords or use commands like:\n"
                    "• /daily - Today's digest\n"
                    "• /tech - Technology news\n"
                    "• /top - Top posts"
                )
                return
            
            # Format results
            results = f"🔍 **Search Results for: '{query}'**\n\n"
            results += f"📊 Found {len(matching_posts)} relevant posts:\n\n"
            
            for i, post in enumerate(matching_posts, 1):
                title = post.get('title', 'No title')
                ai_summary = post.get('ai_summary', '')
                value_score = post.get('value_score', 0)
                category = post.get('category', 'General')
                url = post.get('url', '')
                author = post.get('author', 'Unknown')
                
                # Use AI summary if available, otherwise use content
                summary = ai_summary if ai_summary else post.get('content', '')[:150] + "..."
                
                results += f"**{i}.** {title}\n"
                results += f"📝 {summary}\n"
                results += f"⭐ {value_score}/10 | {category} | 👤 {author}\n"
                results += f"🔗 [Read More]({url})\n\n"
            
            # Split long messages
            if len(results) > 3000:
                parts = self._split_message(results, 3000)
                for i, part in enumerate(parts):
                    if i == 0:
                        await update.message.reply_text(part, parse_mode='Markdown')
                    else:
                        await update.message.reply_text(f"🔍 Search Results (Part {i+1})\n\n{part}", parse_mode='Markdown')
            else:
                await update.message.reply_text(results, parse_mode='Markdown')
                
        except Exception as e:
            logger.error(f"Error handling search query: {e}")
            await update.message.reply_text("❌ Error searching posts. Please try again.")
    
    async def daily_digest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /daily command"""
        user_id = str(update.effective_user.id)
        
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
        
        await update.message.reply_text("📰 Generating daily digest...")
        
        try:
            digest = self.news_generator.generate_daily_digest()
            # Use recent posts to build buttons
            recent_posts = self.news_generator.get_recent_posts(days=1, limit=5)
            reply_markup = self._build_post_buttons(recent_posts)
            await update.message.reply_text(digest, parse_mode='Markdown', reply_markup=reply_markup)
                
        except Exception as e:
            logger.error(f"Error generating daily digest: {e}")
            await update.message.reply_text("❌ Error generating daily digest. Please try again.")
    
    async def weekly_digest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /weekly command"""
        user_id = str(update.effective_user.id)
        
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
        
        await update.message.reply_text("📰 Generating weekly digest...")
        
        try:
            digest = self.news_generator.generate_weekly_digest()
            recent_posts = self.news_generator.get_recent_posts(days=7, limit=5)
            reply_markup = self._build_post_buttons(recent_posts)
            await update.message.reply_text(digest, parse_mode='Markdown', reply_markup=reply_markup)
                
        except Exception as e:
            logger.error(f"Error generating weekly digest: {e}")
            await update.message.reply_text("❌ Error generating weekly digest. Please try again.")
    
    async def category_digest(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle category commands like /tech, /ai, etc."""
        user_id = str(update.effective_user.id)
        
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
        
        command = update.message.text.lower().strip('/')
        category_map = {
            'tech': 'Technology',
            'ai': 'AI',
            'business': 'Business',
            'general': 'General'
        }
        
        category = category_map.get(command, command.title())
        
        await update.message.reply_text(f"📰 Generating {category} digest...")
        
        try:
            digest = self.news_generator.generate_category_digest(category)
            category_posts = self.news_generator.get_posts_by_category(category, limit=5)
            reply_markup = self._build_post_buttons(category_posts)
            await update.message.reply_text(digest, parse_mode='Markdown', reply_markup=reply_markup)
                
        except Exception as e:
            logger.error(f"Error generating {category} digest: {e}")
            await update.message.reply_text(f"❌ Error generating {category} digest. Please try again.")
    
    async def top_posts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /top command"""
        user_id = str(update.effective_user.id)
        
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("❌ You are not authorized to use this bot.")
            return
        
        await update.message.reply_text("🏆 Getting top posts...")
        
        try:
            top_posts = self.news_generator.get_top_posts(limit=5)
            if not top_posts:
                await update.message.reply_text("❌ No posts found.")
                return
            # Build a short header and attach buttons to read posts
            header = "🏆 **Top Posts by Value Score**\n\nHere are the highlights:"
            reply_markup = self._build_post_buttons(top_posts)
            await update.message.reply_text(header, parse_mode='Markdown', reply_markup=reply_markup)
                
        except Exception as e:
            logger.error(f"Error getting top posts: {e}")
            await update.message.reply_text("❌ Error getting top posts. Please try again.")
    
    def _split_message(self, message: str, max_length: int) -> list:
        """Split a long message into parts"""
        parts = []
        current_part = ""
        
        lines = message.split('\n')
        
        for line in lines:
            if len(current_part + line + '\n') <= max_length:
                current_part += line + '\n'
            else:
                if current_part:
                    parts.append(current_part.strip())
                current_part = line + '\n'
        
        if current_part:
            parts.append(current_part.strip())
        
        return parts
    
    async def send_daily_digest_to_chat(self):
        """Send daily digest to configured chat"""
        if not self.chat_id:
            logger.warning("TELEGRAM_CHAT_ID not configured")
            return
        
        try:
            digest = self.news_generator.generate_daily_digest()
            
            # Create bot application
            application = Application.builder().token(self.token).build()
            
            # Split long messages
            if len(digest) > 4000:
                parts = self._split_message(digest, 4000)
                for i, part in enumerate(parts):
                    if i == 0:
                        await application.bot.send_message(
                            chat_id=self.chat_id,
                            text=part,
                            parse_mode='Markdown'
                        )
                    else:
                        await application.bot.send_message(
                            chat_id=self.chat_id,
                            text=f"📰 Daily Digest (Part {i+1})\n\n{part}",
                            parse_mode='Markdown'
                        )
            else:
                await application.bot.send_message(
                    chat_id=self.chat_id,
                    text=digest,
                    parse_mode='Markdown'
                )
            
            logger.info("Daily digest sent successfully")
            
        except Exception as e:
            logger.error(f"Error sending daily digest: {e}")
    
    def run_bot(self):
        """Run the Telegram bot"""
        # Create application
        application = Application.builder().token(self.token).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", self.start))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("id", self.chat_id_command))
        application.add_handler(CommandHandler("daily", self.daily_digest))
        application.add_handler(CommandHandler("weekly", self.weekly_digest))
        application.add_handler(CommandHandler("top", self.top_posts))
        
        # Add category handlers
        application.add_handler(CommandHandler("tech", self.category_digest))
        application.add_handler(CommandHandler("ai", self.category_digest))
        application.add_handler(CommandHandler("business", self.category_digest))
        application.add_handler(CommandHandler("general", self.category_digest))
        
        # Add callback query handler for buttons
        application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # Add message handler for natural language search
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_search_query))
        
        # Start the bot
        if self.webhook_url:
            print("🤖 Starting Prismind Telegram Bot (webhook mode)...")
            print(f"🌐 Webhook URL: {self.webhook_url}")
            application.run_webhook(
                listen=self.listen_host,
                port=self.listen_port,
                url_path=self.token,
                webhook_url=f"{self.webhook_url}/{self.token}",
                drop_pending_updates=True
            )
        else:
            print("🤖 Starting Prismind Telegram Bot (polling mode)...")
            print("📱 Bot is ready! Use /start to begin.")
            print("🔍 You can now ask questions like 'find me data about tensor charts'")
            application.run_polling(drop_pending_updates=True)

def main():
    """Main function to run the bot"""
    try:
        bot = PrismindTelegramBot()
        bot.run_bot()
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        print("\n💡 Make sure to set up your .env file with:")
        print("   TELEGRAM_BOT_TOKEN=your_bot_token")
        print("   TELEGRAM_ALLOWED_USERS=user_id1,user_id2")
        print("   TELEGRAM_CHAT_ID=your_chat_id")

if __name__ == "__main__":
    main()
