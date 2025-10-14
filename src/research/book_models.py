#!/usr/bin/env python3
"""
Book data models for PrisMind
"""

from dataclasses import dataclass, asdict
from typing import Dict, List, Any, Optional
from datetime import datetime


@dataclass
class Book:
    """Book data structure"""
    title: str
    authors: List[str]
    isbn: Optional[str] = None
    publication_year: Optional[int] = None
    publisher: Optional[str] = None
    description: Optional[str] = None
    categories: List[str] = None
    language: str = "en"
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Book':
        """Create from dictionary"""
        return cls(**data)


@dataclass
class BookEntry:
    """Book entry with metadata and file information"""
    book: Book
    file_path: str
    file_hash: str
    added_date: datetime
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    tags: List[str] = None
    notes: Optional[str] = None
    rating: Optional[int] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.rating is not None:
            self.rating = max(1, min(5, self.rating))  # Ensure rating is 1-5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        # Convert datetime objects to ISO strings
        data['added_date'] = self.added_date.isoformat()
        if self.last_accessed:
            data['last_accessed'] = self.last_accessed.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BookEntry':
        """Create from dictionary"""
        # Convert ISO strings back to datetime objects
        if isinstance(data['added_date'], str):
            data['added_date'] = datetime.fromisoformat(data['added_date'])
        if data.get('last_accessed') and isinstance(data['last_accessed'], str):
            data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        
        # Extract book data
        book_data = data.pop('book')
        book = Book.from_dict(book_data)
        data['book'] = book
        
        return cls(**data)
    
    def update_access(self):
        """Update access statistics"""
        self.last_accessed = datetime.now()
        self.access_count += 1
    
    def add_tag(self, tag: str):
        """Add a tag"""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def remove_tag(self, tag: str):
        """Remove a tag"""
        if tag in self.tags:
            self.tags.remove(tag)
    
    def set_rating(self, rating: int):
        """Set rating (1-5)"""
        self.rating = max(1, min(5, rating))
    
    def get_summary(self) -> str:
        """Get a summary of the book entry"""
        summary = f"Title: {self.book.title}\n"
        summary += f"Authors: {', '.join(self.book.authors)}\n"
        if self.book.publication_year:
            summary += f"Year: {self.book.publication_year}\n"
        if self.book.publisher:
            summary += f"Publisher: {self.book.publisher}\n"
        if self.tags:
            summary += f"Tags: {', '.join(self.tags)}\n"
        if self.rating:
            summary += f"Rating: {'★' * self.rating}\n"
        summary += f"Access count: {self.access_count}\n"
        return summary





