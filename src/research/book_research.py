#!/usr/bin/env python3
"""
Book research module.
This module provides capabilities to research books using various APIs and databases.
"""

import sys
import os
import asyncio
import requests
from typing import List, Optional
from dataclasses import dataclass

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

@dataclass
class Book:
    """Represents a book with metadata."""
    title: str
    authors: List[str]
    description: str
    isbn: Optional[str]
    publisher: Optional[str]
    published_date: Optional[str]
    pages: Optional[int]
    url: Optional[str]
    source: str  # e.g., "Google Books", "OpenLibrary"

class BookResearcher:
    """Researcher for books using various APIs."""
    
    def __init__(self, google_books_api_key: Optional[str] = None):
        """
        Initialize the book researcher.
        
        Args:
            google_books_api_key: API key for Google Books (optional)
        """
        self.google_books_api_key = google_books_api_key
        self.google_books_base_url = "https://www.googleapis.com/books/v1/volumes"
        self.openlibrary_base_url = "https://openlibrary.org/search.json"
    
    async def search_books(self, query: str, max_results: int = 5) -> List[Book]:
        """
        Search for books using multiple sources.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of Book objects
        """
        # Search using multiple sources concurrently
        google_books_task = self._search_google_books(query, max_results // 2)
        openlibrary_task = self._search_openlibrary(query, max_results // 2)
        
        # Run both searches concurrently
        google_books, openlibrary_books = await asyncio.gather(
            google_books_task, 
            openlibrary_task,
            return_exceptions=True
        )
        
        # Handle exceptions
        if isinstance(google_books, Exception):
            print(f"Error searching Google Books: {google_books}")
            google_books = []
            
        if isinstance(openlibrary_books, Exception):
            print(f"Error searching OpenLibrary: {openlibrary_books}")
            openlibrary_books = []
        
        # Combine results
        all_books = google_books + openlibrary_books
        
        # Remove duplicates based on title and authors
        unique_books = []
        seen_books = set()
        
        for book in all_books:
            # Create a unique identifier for the book
            book_id = (book.title.lower(), tuple(sorted([a.lower() for a in book.authors])))
            if book_id not in seen_books:
                seen_books.add(book_id)
                unique_books.append(book)
        
        # Return up to max_results books
        return unique_books[:max_results]
    
    async def _search_google_books(self, query: str, max_results: int) -> List[Book]:
        """
        Search for books using Google Books API.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of Book objects
        """
        try:
            # Build parameters
            params = {
                "q": query,
                "maxResults": max_results,
                "printType": "books"
            }
            
            # Add API key if available
            if self.google_books_api_key:
                params["key"] = self.google_books_api_key
            
            # Make the request
            response = requests.get(self.google_books_base_url, params=params)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            books = []
            
            if "items" in data:
                for item in data["items"]:
                    volume_info = item.get("volumeInfo", {})
                    
                    # Extract book information
                    title = volume_info.get("title", "Unknown Title")
                    authors = volume_info.get("authors", [])
                    description = volume_info.get("description", "")
                    publisher = volume_info.get("publisher")
                    published_date = volume_info.get("publishedDate")
                    pages = volume_info.get("pageCount")
                    industry_identifiers = volume_info.get("industryIdentifiers", [])
                    
                    # Get ISBN if available
                    isbn = None
                    for identifier in industry_identifiers:
                        if identifier.get("type") in ["ISBN_10", "ISBN_13"]:
                            isbn = identifier.get("identifier")
                            break
                    
                    # Get URL
                    url = volume_info.get("previewLink")
                    
                    # Create book object
                    book = Book(
                        title=title,
                        authors=authors,
                        description=description[:500] + "..." if len(description) > 500 else description,
                        isbn=isbn,
                        publisher=publisher,
                        published_date=published_date,
                        pages=pages,
                        url=url,
                        source="Google Books"
                    )
                    
                    books.append(book)
            
            return books
            
        except Exception as e:
            print(f"Error searching Google Books: {e}")
            return []
    
    async def _search_openlibrary(self, query: str, max_results: int) -> List[Book]:
        """
        Search for books using OpenLibrary API.
        
        Args:
            query: Search query
            max_results: Maximum number of results to return
            
        Returns:
            List of Book objects
        """
        try:
            # Build parameters
            params = {
                "q": query,
                "limit": max_results
            }
            
            # Make the request
            response = requests.get(self.openlibrary_base_url, params=params)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            books = []
            
            if "docs" in data:
                for doc in data["docs"]:
                    # Extract book information
                    title = doc.get("title", "Unknown Title")
                    authors = doc.get("author_name", [])
                    publisher = doc.get("publisher", [None])[0] if doc.get("publisher") else None
                    published_date = doc.get("first_publish_year")
                    isbn_list = doc.get("isbn", [])
                    isbn = isbn_list[0] if isbn_list else None
                    pages = doc.get("number_of_pages_median")
                    
                    # Create a simple description from available data
                    description_parts = []
                    if doc.get("subtitle"):
                        description_parts.append(doc["subtitle"])
                    if doc.get("subject"):
                        description_parts.append("Subjects: " + ", ".join(doc["subject"][:3]))
                    
                    description = "; ".join(description_parts) if description_parts else "No description available."
                    
                    # Create book object
                    book = Book(
                        title=title,
                        authors=authors,
                        description=description[:500] + "..." if len(description) > 500 else description,
                        isbn=isbn,
                        publisher=publisher,
                        published_date=str(published_date) if published_date else None,
                        pages=pages,
                        url=f"https://openlibrary.org{doc.get('key', '')}" if doc.get('key') else None,
                        source="OpenLibrary"
                    )
                    
                    books.append(book)
            
            return books
            
        except Exception as e:
            print(f"Error searching OpenLibrary: {e}")
            return []

# Example usage
async def main():
    """Example usage of the book researcher."""
    print("Book Research Demo")
    print("=" * 20)
    
    # Create the book researcher
    researcher = BookResearcher()
    
    # Search for books
    query = "artificial intelligence"
    print(f"Searching for books on: {query}\n")
    
    books = await researcher.search_books(query, max_results=5)
    
    if books:
        print("Found Books:")
        print("-" * 12)
        for i, book in enumerate(books, 1):
            print(f"{i}. {book.title}")
            print(f"   Authors: {', '.join(book.authors)}")
            if book.published_date:
                print(f"   Published: {book.published_date}")
            if book.publisher:
                print(f"   Publisher: {book.publisher}")
            if book.isbn:
                print(f"   ISBN: {book.isbn}")
            if book.pages:
                print(f"   Pages: {book.pages}")
            print(f"   Description: {book.description}")
            if book.url:
                print(f"   URL: {book.url}")
            print(f"   Source: {book.source}")
            print()
    else:
        print("No books found.")

if __name__ == "__main__":
    asyncio.run(main())