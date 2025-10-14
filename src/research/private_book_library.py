#!/usr/bin/env python3
"""
Private Book Library (Simplified)
=================================

Main orchestrator for private book library using modular components.
"""

from typing import Dict, List, Any, Optional
from .book_library_operations import BookLibraryOperations, Book, BookEntry
from .book_content_analyzer import BookContentAnalyzer


class PrivateBookLibrary:
    """Main private book library using modular components"""
    
    def __init__(self, library_path: str = "private_library"):
        self.operations = BookLibraryOperations(library_path)
        self.analyzer = BookContentAnalyzer()
        self.library_path = library_path
        print("📚 Private Book Library initialized")
    
    # Basic Operations
    async def add_book_from_research(self, book: Book, file_path: Optional[str] = None) -> BookEntry:
        """Add a book from research results"""
        return await self.operations.add_book_from_research(book, file_path)
    
    async def add_book_from_file(self, file_path: str, metadata: Optional[Dict] = None) -> BookEntry:
        """Add a book from file"""
        return await self.operations.add_book_from_file(file_path, metadata)
    
    async def search_books(self, query: str) -> List[BookEntry]:
        """Search books in library"""
        return await self.operations.search_books(query)
    
    def get_all_books(self) -> List[BookEntry]:
        """Get all books in library"""
        return self.operations.get_all_books()
    
    def get_book_by_id(self, book_id: str) -> Optional[BookEntry]:
        """Get book by ID"""
        return self.operations.get_book_by_id(book_id)
    
    def remove_book(self, book_id: str) -> bool:
        """Remove book from library"""
        return self.operations.remove_book(book_id)
    
    def update_book_metadata(self, book_id: str, updates: Dict[str, Any]) -> bool:
        """Update book metadata"""
        return self.operations.update_book_metadata(book_id, updates)
    
    def get_library_stats(self) -> Dict[str, Any]:
        """Get library statistics"""
        return self.operations.get_library_stats()
    
    # Content Analysis Operations
    async def extract_relevant_sections(self, book_id: str, keywords: List[str]) -> List[Dict]:
        """Extract relevant sections from a book based on keywords"""
        book_entry = self.operations.get_book_by_id(book_id)
        if not book_entry:
            return []
        
        return await self.analyzer.extract_relevant_sections(book_id, keywords, book_entry)
    
    async def analyze_book_content(self, book_id: str) -> Dict[str, Any]:
        """Analyze book content and extract insights"""
        book_entry = self.operations.get_book_by_id(book_id)
        if not book_entry:
            return {
                'error': 'Book not found',
                'word_count': 0,
                'chapter_count': 0,
                'key_topics': [],
                'reading_time_estimate': 0,
                'content_analysis': 'Book not found in library'
            }
        
        return await self.analyzer.analyze_book_content(book_entry)
    
    async def search_book_content(self, book_id: str, search_query: str) -> List[Dict]:
        """Search for specific content within a book"""
        book_entry = self.operations.get_book_by_id(book_id)
        if not book_entry:
            return []
        
        return await self.analyzer.search_book_content(book_entry, search_query)
    
    # Convenience Methods
    async def get_book_summary(self, book_id: str) -> Dict[str, Any]:
        """Get comprehensive book summary"""
        book_entry = self.operations.get_book_by_id(book_id)
        if not book_entry:
            return {'error': 'Book not found'}
        
        # Get basic info
        book_info = {
            'book_id': book_id,
            'title': book_entry.book.title,
            'authors': book_entry.book.authors,
            'description': book_entry.book.description,
            'categories': book_entry.book.categories,
            'added_date': book_entry.added_date,
            'access_count': book_entry.access_count,
            'tags': book_entry.tags,
            'notes': book_entry.notes
        }
        
        # Get content analysis
        content_analysis = await self.analyzer.analyze_book_content(book_entry)
        
        return {
            'book_info': book_info,
            'content_analysis': content_analysis
        }
    
    async def find_books_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Find books related to a specific topic"""
        # Search in book titles, descriptions, and categories
        all_books = self.operations.get_all_books()
        matching_books = []
        
        topic_lower = topic.lower()
        
        for book_entry in all_books:
            book = book_entry.book
            
            # Check title, description, categories, and tags
            if (topic_lower in book.title.lower() or
                (book.description and topic_lower in book.description.lower()) or
                any(topic_lower in cat.lower() for cat in book.categories) or
                any(topic_lower in tag.lower() for tag in book_entry.tags)):
                
                matching_books.append({
                    'book_id': book_entry.book_id,
                    'title': book.title,
                    'authors': book.authors,
                    'description': book.description,
                    'categories': book.categories,
                    'access_count': book_entry.access_count,
                    'relevance_score': self._calculate_relevance_score(book, book_entry, topic)
                })
        
        # Sort by relevance score
        matching_books.sort(key=lambda x: x['relevance_score'], reverse=True)
        return matching_books
    
    async def get_reading_recommendations(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get reading recommendations based on library activity"""
        all_books = self.operations.get_all_books()
        
        # Sort by access count and recency
        recommendations = []
        for book_entry in all_books:
            recommendations.append({
                'book_id': book_entry.book_id,
                'title': book_entry.book.title,
                'authors': book_entry.book.authors,
                'description': book_entry.book.description,
                'access_count': book_entry.access_count,
                'last_accessed': book_entry.last_accessed,
                'recommendation_score': self._calculate_recommendation_score(book_entry)
            })
        
        # Sort by recommendation score
        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)
        return recommendations[:limit]
    
    def _calculate_relevance_score(self, book: Book, book_entry: BookEntry, topic: str) -> float:
        """Calculate relevance score for topic matching"""
        score = 0.0
        topic_lower = topic.lower()
        
        # Title match (highest weight)
        if topic_lower in book.title.lower():
            score += 3.0
        
        # Description match
        if book.description and topic_lower in book.description.lower():
            score += 2.0
        
        # Category match
        for category in book.categories:
            if topic_lower in category.lower():
                score += 1.5
        
        # Tag match
        for tag in book_entry.tags:
            if topic_lower in tag.lower():
                score += 1.0
        
        # Access count bonus
        score += book_entry.access_count * 0.1
        
        return score
    
    def _calculate_recommendation_score(self, book_entry: BookEntry) -> float:
        """Calculate recommendation score for a book"""
        score = 0.0
        
        # Access count (how often it's been accessed)
        score += book_entry.access_count * 2.0
        
        # Recency bonus (more recent access = higher score)
        from datetime import datetime
        try:
            last_accessed = datetime.fromisoformat(book_entry.last_accessed)
            days_since_access = (datetime.now() - last_accessed).days
            
            if days_since_access < 7:
                score += 3.0
            elif days_since_access < 30:
                score += 2.0
            elif days_since_access < 90:
                score += 1.0
        except:
            pass
        
        # Content richness bonus
        if book_entry.book.description and len(book_entry.book.description) > 100:
            score += 1.0
        
        # Category diversity bonus
        if len(book_entry.book.categories) > 1:
            score += 0.5
        
        return score
