#!/usr/bin/env python3
"""
Book Content Analyzer for PrisMind
Handles content analysis and extraction from books
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from .book_library_operations import BookEntry


class BookContentAnalyzer:
    """Handles book content analysis and extraction"""
    
    def __init__(self):
        pass
    
    async def extract_relevant_sections(self, book_id: str, keywords: List[str], book_entry: BookEntry) -> List[Dict]:
        """Extract relevant sections from a book based on keywords"""
        try:
            if not book_entry.file_path or not os.path.exists(book_entry.file_path):
                return []
            
            # Read file content
            content = self._read_file_content(book_entry.file_path)
            if not content:
                return []
            
            # Extract sections
            sections = self._extract_sections(content, keywords)
            
            # Rank sections by relevance
            ranked_sections = self._rank_sections(sections, keywords)
            
            return ranked_sections[:10]  # Return top 10 sections
            
        except Exception as e:
            print(f"❌ Error extracting sections from book {book_id}: {e}")
            return []
    
    async def analyze_book_content(self, book_entry: BookEntry) -> Dict[str, Any]:
        """Analyze book content and extract insights"""
        try:
            if not book_entry.file_path or not os.path.exists(book_entry.file_path):
                return {
                    'word_count': 0,
                    'chapter_count': 0,
                    'key_topics': [],
                    'reading_time_estimate': 0,
                    'content_analysis': 'File not available'
                }
            
            # Read file content
            content = self._read_file_content(book_entry.file_path)
            if not content:
                return {
                    'word_count': 0,
                    'chapter_count': 0,
                    'key_topics': [],
                    'reading_time_estimate': 0,
                    'content_analysis': 'Content not readable'
                }
            
            # Analyze content
            word_count = len(content.split())
            chapter_count = self._count_chapters(content)
            key_topics = self._extract_key_topics(content)
            reading_time = self._estimate_reading_time(word_count)
            
            # Content summary
            content_summary = self._generate_content_summary(content, book_entry.book.title)
            
            return {
                'word_count': word_count,
                'chapter_count': chapter_count,
                'key_topics': key_topics,
                'reading_time_estimate': reading_time,
                'content_analysis': content_summary,
                'file_size': os.path.getsize(book_entry.file_path),
                'file_type': Path(book_entry.file_path).suffix
            }
            
        except Exception as e:
            print(f"❌ Error analyzing book content: {e}")
            return {
                'word_count': 0,
                'chapter_count': 0,
                'key_topics': [],
                'reading_time_estimate': 0,
                'content_analysis': f'Analysis failed: {str(e)}'
            }
    
    async def search_book_content(self, book_entry: BookEntry, search_query: str) -> List[Dict]:
        """Search for specific content within a book"""
        try:
            if not book_entry.file_path or not os.path.exists(book_entry.file_path):
                return []
            
            # Read file content
            content = self._read_file_content(book_entry.file_path)
            if not content:
                return []
            
            # Search for query
            matches = self._search_content(content, search_query)
            
            return matches[:20]  # Return top 20 matches
            
        except Exception as e:
            print(f"❌ Error searching book content: {e}")
            return []
    
    def _read_file_content(self, file_path: str) -> str:
        """Read file content with encoding detection"""
        try:
            # Try different encodings
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        return f.read()
                except UnicodeDecodeError:
                    continue
            
            # Fallback to binary read
            with open(file_path, 'rb') as f:
                content = f.read()
                return content.decode('utf-8', errors='ignore')
                
        except Exception as e:
            print(f"⚠️ Error reading file {file_path}: {e}")
            return ""
    
    def _extract_sections(self, content: str, keywords: List[str]) -> List[Dict]:
        """Extract sections containing keywords"""
        sections = []
        
        # Split content into paragraphs
        paragraphs = content.split('\n\n')
        
        for i, paragraph in enumerate(paragraphs):
            if not paragraph.strip():
                continue
            
            # Check if paragraph contains any keywords
            paragraph_lower = paragraph.lower()
            found_keywords = [kw for kw in keywords if kw.lower() in paragraph_lower]
            
            if found_keywords:
                sections.append({
                    'paragraph_index': i,
                    'content': paragraph.strip(),
                    'found_keywords': found_keywords,
                    'relevance_score': len(found_keywords),
                    'context': self._get_context(paragraphs, i)
                })
        
        return sections
    
    def _rank_sections(self, sections: List[Dict], keywords: List[str]) -> List[Dict]:
        """Rank sections by relevance"""
        for section in sections:
            # Calculate relevance score
            score = 0
            
            # Base score from keyword matches
            score += len(section['found_keywords']) * 2
            
            # Bonus for multiple keyword matches in same section
            unique_keywords = set(section['found_keywords'])
            score += len(unique_keywords) * 0.5
            
            # Bonus for longer, more detailed sections
            content_length = len(section['content'])
            if content_length > 500:
                score += 1
            elif content_length > 200:
                score += 0.5
            
            # Penalty for very short sections
            if content_length < 50:
                score *= 0.5
            
            section['relevance_score'] = score
        
        # Sort by relevance score
        return sorted(sections, key=lambda x: x['relevance_score'], reverse=True)
    
    def _search_content(self, content: str, query: str) -> List[Dict]:
        """Search for specific content"""
        matches = []
        query_lower = query.lower()
        content_lower = content.lower()
        
        # Find all occurrences
        start = 0
        while True:
            pos = content_lower.find(query_lower, start)
            if pos == -1:
                break
            
            # Extract context around match
            context_start = max(0, pos - 100)
            context_end = min(len(content), pos + len(query) + 100)
            context = content[context_start:context_end]
            
            # Highlight the match
            highlighted_context = context.replace(
                content[pos:pos + len(query)],
                f"**{content[pos:pos + len(query)]}**"
            )
            
            matches.append({
                'position': pos,
                'context': highlighted_context,
                'match': content[pos:pos + len(query)],
                'relevance_score': 1.0
            })
            
            start = pos + 1
        
        return matches
    
    def _count_chapters(self, content: str) -> int:
        """Count chapters in content"""
        # Look for common chapter patterns
        chapter_patterns = [
            r'^chapter\s+\d+',
            r'^ch\.\s*\d+',
            r'^\d+\.\s',
            r'^#+\s+chapter',
            r'^#+\s+\d+'
        ]
        
        lines = content.split('\n')
        chapter_count = 0
        
        for line in lines:
            line_lower = line.lower().strip()
            for pattern in chapter_patterns:
                if re.match(pattern, line_lower, re.IGNORECASE):
                    chapter_count += 1
                    break
        
        return max(1, chapter_count)  # At least 1 chapter
    
    def _extract_key_topics(self, content: str) -> List[str]:
        """Extract key topics from content"""
        # Simple keyword extraction
        words = re.findall(r'\b\w+\b', content.lower())
        
        # Filter out common words
        common_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by',
            'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these',
            'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        # Count word frequencies
        word_counts = {}
        for word in words:
            if len(word) > 3 and word not in common_words:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Return top 10 most frequent words
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        return [word for word, count in sorted_words[:10]]
    
    def _estimate_reading_time(self, word_count: int) -> int:
        """Estimate reading time in minutes"""
        # Average reading speed: 200-250 words per minute
        reading_speed = 225
        return max(1, round(word_count / reading_speed))
    
    def _generate_content_summary(self, content: str, title: str) -> str:
        """Generate a brief content summary"""
        # Take first few sentences as summary
        sentences = re.split(r'[.!?]+', content)
        summary_sentences = [s.strip() for s in sentences[:3] if s.strip()]
        
        if summary_sentences:
            summary = '. '.join(summary_sentences)
            if not summary.endswith('.'):
                summary += '.'
            return summary
        else:
            return f"Content analysis for '{title}' - detailed analysis available in full text."
    
    def _get_context(self, paragraphs: List[str], paragraph_index: int) -> str:
        """Get context around a paragraph"""
        start = max(0, paragraph_index - 1)
        end = min(len(paragraphs), paragraph_index + 2)
        
        context_paragraphs = paragraphs[start:end]
        return '\n\n'.join(context_paragraphs)
