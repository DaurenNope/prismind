#!/usr/bin/env python3
import logging

logger = logging.getLogger(__name__)
"""
Book Library Operations for BEYONDLINES
Handles basic CRUD operations for book library
"""

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .book_models import Book, BookEntry


class BookLibraryOperations:
    """Operations for managing a book library"""

    def __init__(self, library_path: str = "data/books"):
        self.library_path = Path(library_path)
        self.library_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.library_path / "index.json"
        self.entries: Dict[str, BookEntry] = {}
        self._load_index()

    def _load_index(self):
        """Load the book index from file"""
        if self.index_file.exists():
            try:
                with open(self.index_file, "r") as f:
                    data = json.load(f)
                    for entry_data in data.get("entries", []):
                        entry = BookEntry.from_dict(entry_data)
                        self.entries[entry.file_hash] = entry
                logger.info(f"✅ Loaded {len(self.entries)} books from index")
            except Exception as e:
                logger.error(f"⚠️ Error loading book index: {e}")
                self.entries = {}
        else:
            logger.info("📁 No book index found, starting fresh")

    def _save_index(self):
        """Save the book index to file"""
        try:
            data = {
                "entries": [entry.to_dict() for entry in self.entries.values()],
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.index_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"✅ Saved {len(self.entries)} books to index")
        except Exception as e:
            logger.error(f"⚠️ Error saving book index: {e}")

    def _calculate_file_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        try:
            with open(file_path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"⚠️ Error calculating hash for {file_path}: {e}")
            return ""

    def add_book(
        self, file_path: str, book: Book, tags: List[str] = None, notes: str = None
    ) -> bool:
        """Add a book to the library"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"❌ File not found: {file_path}")
                return False

            file_hash = self._calculate_file_hash(file_path)
            if not file_hash:
                return False

            # Check if book already exists
            if file_hash in self.entries:
                logger.warning(f"⚠️ Book already exists in library: {book.title}")
                return False

            # Create book entry
            entry = BookEntry(
                book=book,
                file_path=str(file_path),
                file_hash=file_hash,
                added_date=datetime.now(),
                tags=tags or [],
                notes=notes,
            )

            # Add to library
            self.entries[file_hash] = entry
            self._save_index()

            logger.info(f"✅ Added book: {book.title}")
            return True

        except Exception as e:
            logger.error(f"❌ Error adding book: {e}")
            return False

    def remove_book(self, file_hash: str) -> bool:
        """Remove a book from the library"""
        try:
            if file_hash in self.entries:
                entry = self.entries[file_hash]
                del self.entries[file_hash]
                self._save_index()
                logger.info(f"✅ Removed book: {entry.book.title}")
                return True
            else:
                logger.error(f"❌ Book not found: {file_hash}")
                return False
        except Exception as e:
            logger.error(f"❌ Error removing book: {e}")
            return False

    def get_book(self, file_hash: str) -> Optional[BookEntry]:
        """Get a book entry by hash"""
        return self.entries.get(file_hash)

    def get_all_books(self) -> List[BookEntry]:
        """Get all books in the library"""
        return list(self.entries.values())

    def search_books(self, query: str) -> List[BookEntry]:
        """Search books by title, author, or tags"""
        query = query.lower()
        results = []

        for entry in self.entries.values():
            # Search in title
            if query in entry.book.title.lower():
                results.append(entry)
                continue

            # Search in authors
            for author in entry.book.authors:
                if query in author.lower():
                    results.append(entry)
                    break

            # Search in tags
            for tag in entry.tags:
                if query in tag.lower():
                    results.append(entry)
                    break

        return results

    def get_books_by_author(self, author: str) -> List[BookEntry]:
        """Get books by a specific author"""
        results = []
        author_lower = author.lower()

        for entry in self.entries.values():
            for book_author in entry.book.authors:
                if author_lower in book_author.lower():
                    results.append(entry)
                    break

        return results

    def get_books_by_category(self, category: str) -> List[BookEntry]:
        """Get books by category"""
        results = []
        category_lower = category.lower()

        for entry in self.entries.values():
            for book_category in entry.book.categories:
                if category_lower in book_category.lower():
                    results.append(entry)
                    break

        return results

    def get_books_by_rating(self, min_rating: int = 1) -> List[BookEntry]:
        """Get books with minimum rating"""
        results = []

        for entry in self.entries.values():
            if entry.rating and entry.rating >= min_rating:
                results.append(entry)

        return results

    def update_book_metadata(self, file_hash: str, **kwargs) -> bool:
        """Update book metadata"""
        try:
            if file_hash not in self.entries:
                logger.error(f"❌ Book not found: {file_hash}")
                return False

            entry = self.entries[file_hash]

            # Update allowed fields
            allowed_fields = ["tags", "notes", "rating"]
            for field, value in kwargs.items():
                if field in allowed_fields:
                    setattr(entry, field, value)

            self._save_index()
            logger.info(f"✅ Updated metadata for: {entry.book.title}")
            return True

        except Exception as e:
            logger.error(f"❌ Error updating book metadata: {e}")
            return False

    def get_library_stats(self) -> Dict[str, Any]:
        """Get library statistics"""
        total_books = len(self.entries)
        total_authors = set()
        total_categories = set()
        total_tags = set()
        rated_books = 0
        total_rating = 0

        for entry in self.entries.values():
            total_authors.update(entry.book.authors)
            total_categories.update(entry.book.categories)
            total_tags.update(entry.tags)

            if entry.rating:
                rated_books += 1
                total_rating += entry.rating

        return {
            "total_books": total_books,
            "total_authors": len(total_authors),
            "total_categories": len(total_categories),
            "total_tags": len(total_tags),
            "rated_books": rated_books,
            "average_rating": total_rating / rated_books if rated_books > 0 else 0,
        }

    def export_library(self, export_path: str) -> bool:
        """Export library to a file"""
        try:
            export_path = Path(export_path)
            export_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "export_date": datetime.now().isoformat(),
                "entries": [entry.to_dict() for entry in self.entries.values()],
                "stats": self.get_library_stats(),
            }

            with open(export_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.info(f"✅ Exported library to: {export_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Error exporting library: {e}")
            return False

    def import_library(self, import_path: str) -> bool:
        """Import library from a file"""
        try:
            import_path = Path(import_path)
            if not import_path.exists():
                logger.error(f"❌ Import file not found: {import_path}")
                return False

            with open(import_path, "r") as f:
                data = json.load(f)

            imported_count = 0
            for entry_data in data.get("entries", []):
                try:
                    entry = BookEntry.from_dict(entry_data)
                    self.entries[entry.file_hash] = entry
                    imported_count += 1
                except Exception as e:
                    logger.error(f"⚠️ Error importing entry: {e}")
                    continue

            self._save_index()
            logger.info(f"✅ Imported {imported_count} books from: {import_path}")
            return True

        except Exception as e:
            logger.error(f"❌ Error importing library: {e}")
            return False
