#!/usr/bin/env python3
"""
Pre-compute persona expertise embeddings

This runs once to compute embeddings for each persona's expertise
and stores them in the persona JSON files.
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.indexing.embedding_service import EmbeddingService
from src.core.research.semantic_encoder import SemanticEncoder


def main():
    print("="*70)
    print("🔮 PRE-COMPUTING PERSONA EMBEDDINGS")
    print("="*70)
    
    personas_dir = Path("config/personas")
    if not personas_dir.exists():
        print(f"❌ Personas directory not found: {personas_dir}")
        return
    
    # Initialize embedding service
    embedding_service = EmbeddingService()
    semantic_encoder = SemanticEncoder()
    
    if not embedding_service.is_available() or not semantic_encoder.is_available():
        print("❌ Embedding service not available")
        print("   Install: pip install sentence-transformers")
        return
    
    print(f"\n✅ Embedding service available")
    print(f"   Model: {embedding_service.model_name}")
    print(f"   Dimensions: {embedding_service.dimension}")
    
    # Process each persona
    persona_files = list(personas_dir.glob("*.json"))
    print(f"\n📁 Found {len(persona_files)} persona files")
    
    for persona_file in persona_files:
        try:
            print(f"\n📄 Processing: {persona_file.name}")
            
            # Load persona
            with open(persona_file, 'r') as f:
                persona = json.load(f)
            
            persona_key = persona.get('key') or persona_file.stem
            expertise = persona.get('expertise', [])
            
            if not expertise:
                print(f"   ⚠️  No expertise defined, skipping")
                continue
            
            # Combine expertise into text
            expertise_text = ", ".join(expertise)
            voice_description = persona.get('voice_description', '')
            if voice_description:
                expertise_text += f". {voice_description}"
            
            print(f"   📝 Expertise: {', '.join(expertise[:3])}...")
            
            # Generate embedding
            embedding = semantic_encoder.encode_text(expertise_text)
            
            if embedding is None:
                print(f"   ❌ Failed to generate embedding")
                continue
            
            embedding_list = embedding.tolist()
            
            # Store in persona matching config
            if 'matching' not in persona:
                persona['matching'] = {}
            
            persona['matching']['expertise_embedding'] = embedding_list
            persona['matching']['expertise_embedding_model'] = embedding_service.model_name
            persona['matching']['expertise_embedding_dimensions'] = len(embedding_list)
            
            # Save updated persona
            with open(persona_file, 'w') as f:
                json.dump(persona, f, indent=2)
            
            print(f"   ✅ Saved embedding ({len(embedding_list)} dims)")
            
        except Exception as e:
            print(f"   ❌ Error processing {persona_file.name}: {e}")
    
    print("\n" + "="*70)
    print("✅ EMBEDDING PRE-COMPUTATION COMPLETE")
    print("="*70)


if __name__ == "__main__":
    main()

