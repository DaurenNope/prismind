# 📋 Implementation Plan - Step by Step

**From Smart Discovery Roadmap → Actionable Tasks**

---

## 🎯 Current Focus: Fix Core, Then Enhance

### Priority Order
1. **CRITICAL:** Fix Threads collector (ASAP)
2. **HIGH:** Week 1-2 tasks from roadmap
3. **MEDIUM:** Week 3-4 enhancements
4. **FUTURE:** Advanced features

---

## 🔥 CRITICAL: Fix Threads Collector (Today)

### Issue
⚠️ Threads collector not working reliably
- Cookie authentication issues
- Selectors may be outdated
- Need to test end-to-end

### Files
- `src/core/extraction/threads_extractor.py` (923 lines)
- `cookies/threads_cookies.json`
- `tests/test_threads_collector.py`

### Tasks
- [ ] **Task 1.1:** Update cookie authentication
  - Check cookie format and expiry
  - Test cookie loading
  - Add better error handling

- [ ] **Task 1.2:** Update selectors
  - Inspect current Threads HTML structure
  - Update CSS selectors
  - Test data extraction

- [ ] **Task 1.3:** Test end-to-end
  - Run `tests/test_threads_collector.py`
  - Manually test with real profile
  - Verify data saves to database

- [ ] **Task 1.4:** Document working config
  - Update cookie file format docs
  - Add troubleshooting guide
  - Document Threads URL patterns

**Time Estimate:** 2-3 hours  
**Success Criteria:** Can collect threads posts reliably

---

## 📅 Week 1: Concept Extraction (Oct 14-20)

### Goal
Extract structured concepts from discovered content using LLM

### Setup Tasks

#### Task 2.1: Create ConceptExtractor Class
**File:** `src/core/analysis/concept_extractor.py`

```python
# Create new file
class ConceptExtractor:
    """Extract structured concepts from content using LLM"""
    
    async def extract_concepts(self, content: str) -> ConceptGraph:
        """
        Extract:
        - Key concepts (AI, crypto, startups, etc.)
        - Named entities (companies, people, tech)
        - Themes (regulation, innovation, disruption)
        - Sentiment (bullish, bearish, neutral)
        - Time sensitivity (urgent, evergreen)
        """
        pass

@dataclass
class ConceptGraph:
    concepts: List[str]
    entities: List[str]
    themes: List[str]
    sentiment: Dict[str, Any]
    connections: List[str]
    time_sensitivity: str
```

**Checklist:**
- [ ] Create file structure
- [ ] Implement LLM prompt for extraction
- [ ] Test with sample content
- [ ] Add error handling
- [ ] Write tests: `tests/test_concept_extractor.py`

**Time:** 4 hours

---

#### Task 2.2: Add Database Schema
**File:** `migrations/add_content_concepts.sql`

```sql
CREATE TABLE content_concepts (
    id BIGSERIAL PRIMARY KEY,
    discovery_id BIGINT REFERENCES discoveries(id),
    concepts JSONB,
    entities JSONB,
    themes JSONB,
    sentiment JSONB,
    connections JSONB,
    time_sensitivity TEXT,
    extracted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_concepts_gin ON content_concepts USING GIN (concepts);
CREATE INDEX idx_entities_gin ON content_concepts USING GIN (entities);
CREATE INDEX idx_themes_gin ON content_concepts USING GIN (themes);
```

**Checklist:**
- [ ] Create SQL migration file
- [ ] Test locally with SQLite
- [ ] Run migration on Supabase
- [ ] Verify indexes created
- [ ] Update database manager to handle new table

**Time:** 2 hours

---

#### Task 2.3: Integrate into Discovery Pipeline
**Files:** 
- `src/services/autonomous_discovery.py`
- `src/services/new_database_manager.py`

**Changes:**
```python
# In autonomous_discovery.py, after quality filtering

async def _analyze_and_store(self, discoveries: List[Discovery]):
    """Analyze and store discoveries with concept extraction"""
    
    concept_extractor = ConceptExtractor()
    
    for discovery in discoveries:
        if discovery.quality_score > 0.7:
            # Extract concepts
            concepts = await concept_extractor.extract_concepts(
                discovery.content
            )
            
            # Store discovery
            await self.db.store_discovery(discovery)
            
            # Store concepts
            await self.db.store_concepts(discovery.id, concepts)
```

**Checklist:**
- [ ] Add ConceptExtractor to discovery pipeline
- [ ] Only extract for high-quality content (score > 0.7)
- [ ] Add batch processing (10 at a time)
- [ ] Log extraction results
- [ ] Handle API errors gracefully

**Time:** 3 hours

---

#### Task 2.4: Build UI to View Concepts
**File:** `src/web/components/discoveries_tab.py`

**Add to discoveries display:**
```python
# Show concepts with each discovery
if discovery.concepts:
    st.markdown("**Concepts:** " + ", ".join(discovery.concepts))
    
if discovery.entities:
    st.markdown("**Entities:** " + ", ".join(discovery.entities))
    
if discovery.themes:
    st.markdown("**Themes:** " + ", ".join(discovery.themes))
```

**Checklist:**
- [ ] Add concept display to discoveries tab
- [ ] Add filtering by concept
- [ ] Add concept tag cloud
- [ ] Style concept tags
- [ ] Test UI updates

**Time:** 2 hours

---

### Week 1 Deliverables
- ✅ ConceptExtractor class working
- ✅ Database schema updated
- ✅ Pipeline integration complete
- ✅ UI showing concepts
- ✅ Tests passing

**Total Time:** ~11 hours  
**By End of Week:** Can see extracted concepts in UI

---

## 📅 Week 2: Similarity Search Setup (Oct 21-27)

### Goal
Enable "find more like this" functionality using embeddings

### Setup Tasks

#### Task 3.1: Set Up pgvector in Supabase
**File:** `migrations/add_pgvector.sql`

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to discoveries
ALTER TABLE discoveries 
ADD COLUMN embedding vector(1536);  -- OpenAI ada-002 dimension

-- Create index for fast similarity search
CREATE INDEX idx_discoveries_embedding 
ON discoveries USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Checklist:**
- [ ] Enable pgvector in Supabase dashboard
- [ ] Run migration
- [ ] Verify extension working
- [ ] Test vector operations
- [ ] Document setup process

**Time:** 2 hours

---

#### Task 3.2: Create Embedding Service
**File:** `src/core/indexing/embedding_service.py` (already exists, enhance)

**Add methods:**
```python
class EmbeddingService:
    """Generate and manage embeddings"""
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI"""
        response = await openai.Embedding.create(
            input=text,
            model="text-embedding-ada-002"
        )
        return response['data'][0]['embedding']
    
    async def batch_generate(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batch"""
        # Batch up to 100 at a time
        pass
```

**Checklist:**
- [ ] Enhance existing embedding service
- [ ] Add batch processing
- [ ] Add caching
- [ ] Handle API errors
- [ ] Test with sample texts

**Time:** 3 hours

---

#### Task 3.3: Create SimilaritySearch Class
**File:** `src/core/indexing/similarity_search.py`

```python
class SimilaritySearch:
    """Semantic similarity search using embeddings"""
    
    async def index_discovery(self, discovery: Discovery):
        """Generate and store embedding"""
        # Combine title + content + concepts
        text = f"{discovery.title}\n{discovery.content}\n"
        text += " ".join(discovery.concepts or [])
        
        # Generate embedding
        embedding = await self.embedding_service.embed(text)
        
        # Store in database
        await self.db.update_embedding(discovery.id, embedding)
    
    async def find_similar(
        self, 
        discovery_id: int, 
        limit: int = 10
    ) -> List[Discovery]:
        """Find similar discoveries using vector search"""
        
        # Get embedding
        embedding = await self.db.get_embedding(discovery_id)
        
        # Vector similarity search
        query = """
            SELECT id, title, url, 
                   1 - (embedding <=> $1::vector) as similarity
            FROM discoveries
            WHERE embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $2
        """
        
        results = await self.db.fetch(query, embedding, limit)
        return results
```

**Checklist:**
- [ ] Create SimilaritySearch class
- [ ] Implement indexing
- [ ] Implement similarity search
- [ ] Add distance threshold
- [ ] Write tests: `tests/test_similarity_search.py`

**Time:** 4 hours

---

#### Task 3.4: Backfill Embeddings
**File:** `scripts/backfill_embeddings.py`

```python
async def backfill_embeddings():
    """Generate embeddings for existing discoveries"""
    
    # Get all discoveries without embeddings
    discoveries = await db.fetch("""
        SELECT * FROM discoveries 
        WHERE embedding IS NULL 
        AND quality_score > 0.7
        ORDER BY created_at DESC
    """)
    
    # Process in batches
    for batch in chunks(discoveries, 100):
        texts = [format_for_embedding(d) for d in batch]
        embeddings = await embedding_service.batch_generate(texts)
        
        # Update database
        await db.update_embeddings(batch, embeddings)
        
        print(f"Processed {len(batch)} discoveries")
```

**Checklist:**
- [ ] Create backfill script
- [ ] Run on existing data
- [ ] Monitor API costs
- [ ] Log progress
- [ ] Verify embeddings stored

**Time:** 2 hours

---

#### Task 3.5: Add "Find Similar" to UI
**File:** `src/web/components/discoveries_tab.py`

```python
# Add button to each discovery
if st.button("🔍 Find Similar", key=f"similar_{discovery.id}"):
    similar = await similarity_search.find_similar(discovery.id, 10)
    
    st.markdown("### Similar Discoveries")
    for sim in similar:
        st.markdown(f"**[{sim.title}]({sim.url})** - {sim.similarity:.2%} match")
```

**Checklist:**
- [ ] Add "Find Similar" button
- [ ] Display similar discoveries
- [ ] Show similarity score
- [ ] Add loading state
- [ ] Test with real data

**Time:** 3 hours

---

### Week 2 Deliverables
- ✅ pgvector set up and working
- ✅ Embeddings generated for content
- ✅ Similarity search functional
- ✅ "Find Similar" in UI
- ✅ Tests passing

**Total Time:** ~14 hours  
**By End of Week:** Users can find similar content with one click

---

## 📅 Week 3: Smart Expansion (Oct 28-Nov 3)

### Goal
Auto-discover more content when user saves something

### Tasks

#### Task 4.1: Create SmartExpansion Class
**File:** `src/services/smart_expansion.py`

```python
class SmartExpansion:
    """Automatically expand on interesting discoveries"""
    
    async def expand_discovery(self, discovery_id: int):
        """When user saves, find and fetch more like it"""
        
        # 1. Find similar in database
        similar = await similarity_search.find_similar(discovery_id, 20)
        
        # 2. Analyze patterns
        patterns = await self.analyze_patterns(similar)
        
        # 3. Ask LLM for search queries
        queries = await self.generate_search_queries(discovery, patterns)
        
        # 4. Execute searches
        for query in queries:
            await self.execute_discovery_search(query)
```

**Checklist:**
- [ ] Create SmartExpansion class
- [ ] Implement pattern analysis
- [ ] Add LLM query generation
- [ ] Add search execution
- [ ] Write tests

**Time:** 6 hours

---

#### Task 4.2: Hook into Save Action
**File:** `src/web/components/discoveries_tab.py`

```python
# When user clicks save
if st.button("💾 Save", key=f"save_{discovery.id}"):
    await db.mark_saved(discovery.id)
    
    # Trigger smart expansion
    await smart_expansion.expand_discovery(discovery.id)
    
    st.success("Saved! Finding more like this...")
```

**Checklist:**
- [ ] Add expansion trigger on save
- [ ] Show progress notification
- [ ] Run in background
- [ ] Log expansion results

**Time:** 2 hours

---

#### Task 4.3: Test Expansion Quality
**Manual testing:**
- [ ] Save 5 different discoveries
- [ ] Check what gets auto-discovered
- [ ] Measure relevance of expanded content
- [ ] Tune parameters

**Time:** 2 hours

---

### Week 3 Deliverables
- ✅ Smart expansion working
- ✅ Auto-discovery on save
- ✅ Quality validated

**Total Time:** ~10 hours

---

## 📅 Week 4: LLM Research Agent (Nov 4-10)

### Goal
LLM autonomously researches and discovers content

### Tasks

#### Task 5.1: Create DiscoveryAgent Class
**File:** `src/agents/discovery_agent.py`

```python
class DiscoveryAgent:
    """LLM-powered autonomous discovery agent"""
    
    async def research_session(self, topic: str = None):
        """Run autonomous research session"""
        
        # Get context
        top_discoveries = await self.get_recent_top_discoveries()
        
        # Ask LLM for research plan
        plan = await self.generate_research_plan(topic, top_discoveries)
        
        # Execute research
        for direction in plan['directions']:
            await self.research_direction(direction)
```

**Time:** 8 hours

---

#### Task 5.2: Add Feedback Loop
**File:** `src/core/learning/feedback_loop.py`

```python
class FeedbackLoop:
    """Learn from user behavior"""
    
    async def learn_from_action(self, discovery_id: int, action: str):
        """When user saves/dismisses, adjust preferences"""
        
        if action == 'save':
            # Boost similar concepts
            await self.boost_concepts(concepts, 1.2)
        elif action == 'dismiss':
            # Reduce similar concepts
            await self.reduce_concepts(concepts, 0.8)
```

**Time:** 4 hours

---

### Week 4 Deliverables
- ✅ Discovery agent working
- ✅ Feedback loop implemented
- ✅ System learns from actions

**Total Time:** ~12 hours

---

## 🎯 Success Metrics

### Week 1
- [ ] Can extract concepts from 100+ discoveries
- [ ] Concepts visible in UI
- [ ] Extraction costs < $5

### Week 2
- [ ] Can search 1000+ discoveries by similarity
- [ ] Average similarity score > 0.7 for top results
- [ ] Search time < 1 second

### Week 3
- [ ] Auto-expansion finds 5-10 relevant items per save
- [ ] User saves expanded items 30%+ of time
- [ ] Expansion quality score > 0.7

### Week 4
- [ ] Research agent generates 10+ valuable discoveries per session
- [ ] User engagement with agent discoveries > 50%
- [ ] System preference accuracy > 70%

---

## 📊 Progress Tracking

### Completed
- ✅ Project cleanup (69% reduction)
- ✅ Documentation complete
- ✅ Core features verified working

### In Progress
- 🔄 Threads collector fix
- 🔄 Implementation plan created

### Next Up
- ⏳ Week 1: Concept extraction
- ⏳ Week 2: Similarity search
- ⏳ Week 3: Smart expansion
- ⏳ Week 4: Discovery agent

---

## 🔧 Development Workflow

### Daily Checklist
- [ ] Pull latest code
- [ ] Run tests: `pytest tests/ -v`
- [ ] Work on current task
- [ ] Write tests for new code
- [ ] Run tests again
- [ ] Commit with clear message
- [ ] Update progress in this file

### Weekly Review
- [ ] Review week's deliverables
- [ ] Test all new features end-to-end
- [ ] Update documentation
- [ ] Plan next week
- [ ] Demo to stakeholders

---

## 📝 Notes & Learnings

### Cost Estimates
- **OpenAI Embeddings:** $0.0001 per 1K tokens
  - 1000 discoveries × 500 tokens avg = 500K tokens = $0.05
- **LLM Concept Extraction:** $0.002 per 1K tokens (GPT-4)
  - 100 discoveries × 1K tokens = 100K tokens = $0.20
- **Monthly estimate:** < $10 for 1000 discoveries

### Performance Notes
- pgvector can handle 1M+ vectors efficiently
- Batch embedding generation is 10x faster
- Cache embeddings to avoid regeneration

---

**Last Updated:** October 14, 2024  
**Current Phase:** Fix Threads → Week 1 Concept Extraction  
**Status:** Ready to implement 🚀
