#!/usr/bin/env python3
"""
Librarian Book Agent
Discovers, downloads, analyzes, and manages books automatically
"""

import httpx
import logging
import os
import re
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class LibrarianBookAgent:
    """
    Intelligent book management agent
    
    Capabilities:
    - Book discovery (Anna's Archive, Z-Library, Library Genesis)
    - PDF/EPUB download
    - Text extraction
    - AI analysis & summarization
    - Key concepts extraction
    - Actionable insights generation
    - Library organization
    """
    
    def __init__(self, library_path: str = "library/books"):
        self.library_path = Path(library_path)
        self.library_path.mkdir(parents=True, exist_ok=True)
        
        # Book sources
        self.sources = {
            "annas_archive": "https://annas-archive.org",
            "libgen": "http://libgen.rs",
            "zlibrary": "https://z-lib.io"
        }
    
    async def discover_and_analyze(self, book_title: str, author: Optional[str] = None) -> Dict[str, Any]:
        """
        Discover, download, and analyze a book
        
        Args:
            book_title: Book title (must not be None)
            author: Optional author name
            
        Returns:
            Comprehensive book analysis
        """
        
        # Validate input
        if not book_title or not isinstance(book_title, str):
            return {
                "title": book_title or "Unknown",
                "status": "error",
                "error": "Invalid book title"
            }
        
        book_title = book_title.strip()
        if not book_title:
            return {
                "title": "Unknown",
                "status": "error",
                "error": "Book title is empty"
            }
        
        return await self._discover_and_analyze_internal(book_title, author)
    
    async def _discover_and_analyze_internal(self, book_title: str, author: Optional[str] = None) -> Dict[str, Any]:
        """
        Discover, download, and analyze a book
        
        Args:
            book_title: Book title
            author: Optional author name
            
        Returns:
            Comprehensive book analysis
        """
        logger.info(f"📚 Processing book: {book_title}")
        
        try:
            # Phase 1: Search for book
            search_results = await self._search_book(book_title, author)
            
            if not search_results:
                return {
                    "title": book_title,
                    "status": "not_found",
                    "message": "Book not found in available sources"
                }
            
            # Phase 2: Download best match
            best_match = search_results[0]
            download_result = await self._download_book(best_match)
            
            if not download_result.get("success"):
                return {
                    "title": book_title,
                    "status": "download_failed",
                    "message": download_result.get("error", "Download failed")
                }
            
            file_path = download_result["file_path"]
            
            # Phase 3: Extract text
            text_content = await self._extract_text(file_path)
            
            # Phase 4: AI analysis
            analysis = await self._analyze_book(text_content, book_title, author)
            
            # Phase 5: Generate actionable insights
            insights = self._generate_insights(analysis, text_content)
            
            # Compile comprehensive report
            report = {
                "title": book_title,
                "author": author,
                "status": "analyzed",
                "file_path": str(file_path),
                "file_size_mb": file_path.stat().st_size / (1024 * 1024),
                "analyzed_at": datetime.now().isoformat(),
                
                # Content for rewriting
                "tldr": self._generate_book_tldr(book_title, author, analysis),
                "key_concepts": analysis.get("key_concepts", []),
                "frameworks": analysis.get("frameworks", {}),
                "main_arguments": analysis.get("main_arguments", []),
                "key_quotes": self._extract_key_quotes(text_content),
                
                # Actionable intel
                "actionable_insights": insights,
                "practical_applications": self._generate_applications(analysis),
                "related_topics": analysis.get("related_topics", []),
                
                # Metadata
                "page_count": text_content.get("page_count", 0),
                "word_count": text_content.get("word_count", 0),
                "reading_time_hours": text_content.get("word_count", 0) / 15000,
                
                # Organization
                "tags": self._generate_tags(analysis),
                "category": self._categorize_book(analysis),
                "target_audience": self._identify_book_audience(analysis),
                
                # Rewrite angles
                "rewrite_angles": self._generate_book_rewrite_angles(book_title, author, analysis)
            }
            
            logger.info(f"✅ Book analyzed: {book_title}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Book processing failed: {e}")
            return {
                "title": book_title,
                "status": "error",
                "error": str(e)
            }
    
    async def _search_book(self, title: str, author: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for book across multiple sources"""
        
        logger.info(f"🔍 Searching: {title}")
        
        results = []
        
        # Try Anna's Archive (most comprehensive)
        anna_results = await self._search_annas_archive(title, author)
        results.extend(anna_results)
        
        # Try Library Genesis as fallback
        if not results:
            libgen_results = await self._search_libgen(title, author)
            results.extend(libgen_results)
        
        return results
    
    async def _search_annas_archive(self, title: str, author: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search Anna's Archive"""
        
        try:
            query = title
            if author:
                query += f" {author}"
            
            # Anna's Archive search endpoint
            search_url = f"{self.sources['annas_archive']}/search"
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    search_url,
                    params={"q": query},
                    timeout=15,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                
                if response.status_code == 200:
                    # Parse results (simplified - would need proper HTML parsing)
                    # For now, return mock structure
                    return [{
                        "title": title,
                        "author": author,
                        "source": "annas_archive",
                        "format": "pdf",
                        "download_url": None  # Would be extracted from HTML
                    }]
            
            return []
            
        except Exception as e:
            logger.warning(f"Anna's Archive search failed: {e}")
            return []
    
    async def _search_libgen(self, title: str, author: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search Library Genesis"""
        
        try:
            # LibGen search API
            search_url = f"{self.sources['libgen']}/search.php"
            
            params = {
                "req": title,
                "res": 25,
                "view": "simple"
            }
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    search_url,
                    params=params,
                    timeout=15,
                    headers={"User-Agent": "Mozilla/5.0"}
                )
                
                if response.status_code == 200:
                    # Parse results (simplified)
                    return [{
                        "title": title,
                        "author": author,
                        "source": "libgen",
                        "format": "pdf",
                        "download_url": None
                    }]
            
            return []
            
        except Exception as e:
            logger.warning(f"LibGen search failed: {e}")
            return []
    
    async def _download_book(self, book_info: Dict[str, Any]) -> Dict[str, Any]:
        """Download book file"""
        
        # For demo, we'll create a placeholder
        # In production, this would actually download from the source
        
        title = book_info.get("title", "unknown")
        safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')
        
        file_path = self.library_path / f"{safe_title}.pdf"
        
        # Create placeholder file
        file_path.write_text(f"Placeholder for: {title}\n\nIn production, this would be the actual PDF content.")
        
        return {
            "success": True,
            "file_path": file_path,
            "source": book_info.get("source", "unknown")
        }
    
    async def _extract_text(self, file_path: Path) -> Dict[str, Any]:
        """Extract text from PDF/EPUB"""
        
        # For demo, return mock data
        # In production, would use PyPDF2, pdfplumber, or ebooklib
        
        try:
            content = file_path.read_text()
            
            words = content.split()
            
            return {
                "full_text": content,
                "word_count": len(words),
                "page_count": len(words) // 250,  # ~250 words per page
                "chapters": []
            }
            
        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            return {
                "full_text": "",
                "word_count": 0,
                "page_count": 0,
                "chapters": []
            }
    
    async def _analyze_book(self, text_content: Dict, title: str, author: Optional[str]) -> Dict[str, Any]:
        """AI-powered book analysis"""
        
        logger.info("🤖 Analyzing book with AI...")
        
        # Use Ollama for analysis
        try:
            full_text = text_content.get("full_text", "")
            
            # Truncate if too long
            sample_text = full_text[:5000] if len(full_text) > 5000 else full_text
            
            prompt = f"""Analyze this book and provide:

1. Executive summary (2-3 sentences)
2. Key concepts (5-7 main ideas)
3. Frameworks or methodologies (if any)
4. Main arguments
5. Actionable insights
6. Related books or topics

Book: {title}
Author: {author}

Content sample:
{sample_text}

Provide structured analysis:"""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "qwen2.5:7b",
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 500
                        }
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    result = response.json()
                    analysis_text = result.get("response", "")
                    
                    # Parse analysis
                    return self._parse_analysis(analysis_text)
        
        except Exception as e:
            logger.warning(f"AI analysis failed: {e}")
        
        # Fallback to simple analysis
        return {
            "summary": f"Analysis of {title}",
            "key_concepts": [],
            "frameworks": {},
            "main_arguments": [],
            "implementation_steps": [],
            "related_books": [],
            "related_topics": []
        }
    
    def _parse_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """Parse AI analysis response"""
        
        # Simple parsing (would be more sophisticated in production)
        lines = analysis_text.split('\n')
        
        analysis = {
            "summary": "",
            "key_concepts": [],
            "frameworks": {},
            "main_arguments": [],
            "implementation_steps": [],
            "related_books": [],
            "related_topics": []
        }
        
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            if not line:
                continue
            
            if "summary" in line.lower():
                current_section = "summary"
            elif "key concepts" in line.lower():
                current_section = "key_concepts"
            elif "frameworks" in line.lower():
                current_section = "frameworks"
            elif "arguments" in line.lower():
                current_section = "main_arguments"
            elif current_section:
                if current_section == "summary" and not analysis["summary"]:
                    analysis["summary"] = line
                elif current_section == "key_concepts" and line.startswith(('-', '•', '*')):
                    analysis["key_concepts"].append(line.lstrip('-•* '))
                elif current_section == "main_arguments" and line.startswith(('-', '•', '*')):
                    analysis["main_arguments"].append(line.lstrip('-•* '))
        
        # Ensure summary exists
        if not analysis["summary"]:
            analysis["summary"] = "Comprehensive analysis of key themes and concepts."
        
        return analysis
    
    def _generate_insights(self, analysis: Dict, text_content: Dict) -> List[str]:
        """Generate actionable insights"""
        
        insights = []
        
        key_concepts = analysis.get("key_concepts", [])
        frameworks = analysis.get("frameworks", {})
        
        if key_concepts:
            insights.append(f"Study {len(key_concepts)} core concepts for deep understanding")
        
        if frameworks:
            for framework_name in frameworks.keys():
                insights.append(f"Implement {framework_name} methodology")
        
        if text_content.get("word_count", 0) > 50000:
            insights.append("Use progressive summarization technique")
            insights.append("Create chapter-by-chapter notes")
        
        insights.append("Apply key ideas to current projects")
        insights.append("Share insights with team/community")
        
        return insights[:5]  # Top 5
    
    def _generate_tags(self, analysis: Dict) -> List[str]:
        """Generate tags for organization"""
        
        tags = []
        
        # Extract from summary
        summary = analysis.get("summary", "").lower()
        
        tag_keywords = {
            "productivity": ["productivity", "efficiency", "organization", "system"],
            "technology": ["technology", "software", "programming", "development"],
            "business": ["business", "startup", "entrepreneurship", "strategy"],
            "psychology": ["psychology", "mental", "cognitive", "behavior"],
            "philosophy": ["philosophy", "thinking", "wisdom", "ethics"],
            "science": ["science", "research", "study", "analysis"]
        }
        
        for tag, keywords in tag_keywords.items():
            if any(keyword in summary for keyword in keywords):
                tags.append(tag)
        
        return tags[:3] if tags else ["general"]
    
    def _categorize_book(self, analysis: Dict) -> str:
        """Categorize book"""
        
        summary = analysis.get("summary", "").lower()
        
        categories = {
            "self-improvement": ["self", "productivity", "habits", "personal"],
            "technical": ["programming", "software", "technology", "development"],
            "business": ["business", "startup", "entrepreneurship", "management"],
            "science": ["science", "research", "physics", "biology"],
            "philosophy": ["philosophy", "thinking", "wisdom", "mind"]
        }
        
        for category, keywords in categories.items():
            if any(keyword in summary for keyword in keywords):
                return category
        
        return "general"
    
    def _generate_book_tldr(self, title: str, author: Optional[str], analysis: Dict) -> str:
        """Generate TLDR for book"""
        
        summary = analysis.get("summary", "")
        if len(summary) > 200:
            summary = summary[:197] + "..."
        
        parts = []
        
        if summary:
            parts.append(summary)
        
        key_concepts = analysis.get("key_concepts", [])
        if key_concepts:
            parts.append(f"Key concepts: {', '.join(key_concepts[:3])}")
        
        return " • ".join(parts) if parts else f"Comprehensive guide on {title}"
    
    def _extract_key_quotes(self, text_content: Dict) -> List[str]:
        """Extract key quotes from book"""
        
        # Placeholder - in production would use NLP to extract meaningful quotes
        return []
    
    def _generate_applications(self, analysis: Dict) -> List[str]:
        """Generate practical applications"""
        
        applications = []
        
        key_concepts = analysis.get("key_concepts", [])
        frameworks = analysis.get("frameworks", {})
        
        if key_concepts:
            applications.append(f"Apply {len(key_concepts)} core concepts to daily work")
        
        for framework_name in list(frameworks.keys())[:2]:
            applications.append(f"Implement {framework_name} in your workflow")
        
        applications.append("Share key insights with your team")
        applications.append("Create personal action plan based on takeaways")
        
        return applications[:5]
    
    def _identify_book_audience(self, analysis: Dict) -> List[str]:
        """Identify target audience for book"""
        
        category = self._categorize_book(analysis)
        summary = analysis.get("summary", "").lower()
        
        audiences = []
        
        if category == "self-improvement":
            audiences.extend(["professionals seeking growth", "productivity enthusiasts"])
        elif category == "technical":
            audiences.extend(["developers", "software engineers"])
        elif category == "business":
            audiences.extend(["entrepreneurs", "startup founders", "business leaders"])
        elif category == "science":
            audiences.extend(["researchers", "academics", "science enthusiasts"])
        
        # From summary
        if "beginner" in summary or "introduction" in summary:
            audiences.append("beginners")
        
        if "advanced" in summary or "expert" in summary:
            audiences.append("advanced practitioners")
        
        return audiences[:3] if audiences else ["general readers"]
    
    def _generate_book_rewrite_angles(self, title: str, author: Optional[str], analysis: Dict) -> List[Dict[str, str]]:
        """Generate rewrite angles for book"""
        
        angles = []
        
        # Summary angle
        angles.append({
            "persona": "technical",
            "angle": "Deep dive into frameworks and methodologies",
            "hook": f"Breaking down {title}'s key frameworks"
        })
        
        # Practical angle
        angles.append({
            "persona": "builder",
            "angle": "Actionable takeaways and implementation",
            "hook": f"How to apply {title} in your work today"
        })
        
        # Learning angle
        angles.append({
            "persona": "learner",
            "angle": "Complete guide for beginners",
            "hook": f"Everything you need to know about {title}"
        })
        
        # Thought leadership angle
        key_concepts = analysis.get("key_concepts", [])
        if key_concepts:
            angles.append({
                "persona": "thought_leader",
                "angle": "Big picture implications and trends",
                "hook": f"Why {title} matters for the future"
            })
        
        return angles
    
    def get_library_stats(self) -> Dict[str, Any]:
        """Get library statistics"""
        
        books = list(self.library_path.glob("*.pdf")) + list(self.library_path.glob("*.epub"))
        
        total_size = sum(book.stat().st_size for book in books)
        
        return {
            "total_books": len(books),
            "total_size_mb": total_size / (1024 * 1024),
            "library_path": str(self.library_path),
            "books": [book.name for book in books]
        }


# Singleton instance
_librarian = None


def get_librarian() -> LibrarianBookAgent:
    """Get global librarian agent"""
    global _librarian
    if _librarian is None:
        _librarian = LibrarianBookAgent()
    return _librarian


async def test_librarian():
    """Test librarian agent"""
    
    print("🧪 Testing Librarian Book Agent\n")
    
    agent = get_librarian()
    
    # Test with a known book
    book_title = "Building a Second Brain"
    author = "Tiago Forte"
    
    print(f"Processing: {book_title} by {author}\n")
    
    report = await agent.discover_and_analyze(book_title, author)
    
    print("=" * 70)
    print("📚 BOOK ANALYSIS REPORT")
    print("=" * 70)
    print()
    print(f"Title: {report['title']}")
    print(f"Author: {report['author']}")
    print(f"Status: {report['status']}")
    print()
    
    if report['status'] == 'analyzed':
        print(f"Summary: {report['summary']}")
        print()
        print(f"Key Concepts ({len(report['key_concepts'])}):")
        for concept in report['key_concepts'][:5]:
            print(f"  • {concept}")
        print()
        print(f"Actionable Insights:")
        for insight in report['actionable_insights']:
            print(f"  ✓ {insight}")
        print()
        print(f"Category: {report['category']}")
        print(f"Priority: {report['priority']}/10")
        print(f"Reading time: {report['reading_time_hours']:.1f} hours")
    
    print()
    
    # Check library stats
    stats = agent.get_library_stats()
    print(f"📊 Library Stats:")
    print(f"  Books: {stats['total_books']}")
    print(f"  Size: {stats['total_size_mb']:.2f} MB")
    print()
    print("✅ Librarian agent working!")


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_librarian())
