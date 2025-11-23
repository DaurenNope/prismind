import logging
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from openai import OpenAI
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class VectorMemory:
    """
    Vector Memory Module for Prismind Agents.
    Stores and retrieves 'Knowledge Atoms' using OpenAI embeddings and Supabase pgvector.
    """

    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            logger.warning("Supabase credentials not found. Vector Memory will be disabled.")
            self.client = None
        else:
            self.client: Client = create_client(self.supabase_url, self.supabase_key)

        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        if self.openai_api_key:
            self.openai_client = OpenAI(api_key=self.openai_api_key)
        else:
            logger.warning("OpenAI API key not found. Embeddings will fail.")
            self.openai_client = None

        self.embedding_model = "text-embedding-3-small"

    def _get_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using OpenAI."""
        if not self.openai_client:
            raise ValueError("OpenAI API key not set")
        
        text = text.replace("\n", " ")
        response = self.openai_client.embeddings.create(
            input=[text], 
            model=self.embedding_model
        )
        return response.data[0].embedding

    async def add_memory(self, 
                         content: str, 
                         agent_id: str, 
                         source_id: Optional[str] = None, 
                         memory_type: str = "fact",
                         metadata: Dict[str, Any] = None) -> str:
        """
        Add a new memory atom to the vector store.
        """
        if not self.client:
            return "memory_disabled"

        try:
            embedding = self._get_embedding(content)
            
            data = {
                "content": content,
                "embedding": embedding,
                "agent_id": agent_id,
                "source_id": source_id,
                "type": memory_type,
                "metadata": metadata or {},
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            response = self.client.table("knowledge_atoms").insert(data).execute()
            return response.data[0]['id']
        except Exception as e:
            logger.error(f"Failed to add memory: {e}")
            raise

    async def search_memory(self, query: str, limit: int = 5, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """
        Semantic search for memories.
        """
        if not self.client:
            return []

        try:
            query_embedding = self._get_embedding(query)
            
            # Call Supabase RPC function for vector search (needs to be created in migration)
            # For now, we'll use the direct filter if RPC isn't set up, but RPC is better for similarity
            # Assuming 'match_knowledge_atoms' RPC exists or we use client-side logic (not ideal)
            
            # Ideally, we should have an RPC function. Let's assume we'll add it.
            # response = self.client.rpc(
            #     'match_knowledge_atoms',
            #     {'query_embedding': query_embedding, 'match_threshold': threshold, 'match_count': limit}
            # ).execute()
            
            # Fallback/Alternative: If using vecs or direct query if supported. 
            # Supabase-py doesn't support vector comparisons directly in .select() easily without RPC.
            # We will assume the RPC 'match_knowledge_atoms' will be created.
            
            params = {
                "query_embedding": query_embedding, 
                "match_threshold": threshold, 
                "match_count": limit
            }
            response = self.client.rpc("match_knowledge_atoms", params).execute()
            
            return response.data
        except Exception as e:
            logger.error(f"Memory search failed: {e}")
            return []

    async def get_context(self, query: str) -> str:
        """
        Retrieve relevant context as a string for LLM prompting.
        """
        memories = await self.search_memory(query)
        if not memories:
            return ""
        
        context_parts = [f"- {m['content']} (Source: {m.get('type', 'unknown')})" for m in memories]
        return "\n".join(context_parts)
