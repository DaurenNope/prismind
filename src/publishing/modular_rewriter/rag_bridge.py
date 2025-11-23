from __future__ import annotations

from typing import Dict, List, Optional

from src.domain.publishing.rag_system import ExampleVectorDatabase


class RAGBridge:
    """
    Thin wrapper over the existing vector DB so the modular pipeline can fetch
    persona examples or push new ones without touching the monolithic rewriter.
    """

    def __init__(self, vector_db: Optional[ExampleVectorDatabase] = None) -> None:
        self.vector_db = vector_db or ExampleVectorDatabase()

    def fetch_examples(self, persona: str, query: str, *, limit: int = 5) -> List[Dict]:
        try:
            return self.vector_db.search_similar(query=query, persona_id=persona, k=limit)
        except Exception:
            return []

    def add_example(self, persona: str, content: str, metadata: Dict) -> None:
        try:
            self.vector_db.add_example(persona_id=persona, content=content, metadata=metadata)
        except Exception:
            # Noise suppression for now; future versions should log observability events.
            return


