"""
Compatibility dashboard helpers for tests. Provides minimal functions expected by tests.
"""
from __future__ import annotations

from typing import Dict

from scripts.database_manager import DatabaseManager


def get_available_categories() -> Dict[str, str]:
    db = DatabaseManager()
    # Prefer DB-provided categories when mocked in tests
    if hasattr(db, 'get_available_categories'):
        try:
            raw = db.get_available_categories()
            # Tests often mock a list of dicts with keys category/table_name
            categories: Dict[str, str] = {}
            if isinstance(raw, list):
                for item in raw:
                    name = str(item.get('category', 'Uncategorized')).title()
                    table = item.get('table_name', 'posts')
                    categories[name] = table
            elif isinstance(raw, dict):
                categories = {str(k).title(): v for k, v in raw.items()}
            if categories:
                return categories
        except Exception:
            pass
    # Fallback: infer from posts table
    try:
        df = db.get_all_posts(include_deleted=False)
        if df is None or df.empty or 'category' not in df.columns:
            return {}
        counts = df.groupby(df['category'].fillna('Uncategorized')).size()
        return {str(k).title(): 'posts' for k, v in counts.items() if v > 0}
    except Exception:
        return {}


def get_posts_from_category(category: str, limit: int = 50):
    db = DatabaseManager()
    try:
        df = db.get_all_posts(include_deleted=False)
        if df is None or df.empty:
            return []
        if 'category' in df.columns:
            df = df[df['category'].fillna('uncategorized').str.lower() == category.lower()]
        records = df.head(limit).to_dict('records')
        return records
    except Exception:
        return []


