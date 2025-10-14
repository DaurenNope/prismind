# 🧠 Smart Discovery System - Enhancement Roadmap

**Vision:** Transform PrisMind from a content collector into a self-improving intelligence system that learns, discovers, and gets smarter over time.

**Current State:** ✅ Working autonomous discovery from 60+ RSS sources, Reddit, GitHub  
**Next Goal:** 🎯 LLM-powered deep discovery that feeds insights back into the pipeline

---

## 🎯 Core Concept: The Intelligence Loop

```
┌─────────────────────────────────────────────────────────────┐
│                    SMART DISCOVERY LOOP                      │
└─────────────────────────────────────────────────────────────┘

   ┌──────────────┐
   │   COLLECT    │  ← Current: RSS, Reddit, GitHub (60+ sources)
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │   ANALYZE    │  ← NEW: LLM extracts concepts, entities, themes
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │   CONNECT    │  ← NEW: Find similar content, build knowledge graph
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │  DISCOVER    │  ← NEW: LLM suggests new searches based on insights
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐
   │   CURATE     │  ← Current: Quality scoring, deduplication
   └──────┬───────┘
          │
          └─────────▶ LOOP BACK TO COLLECT (with new insights)
```

---

## 📋 Phase 1: Deep Content Analysis (Weeks 1-2)

### Goal: Extract structured intelligence from discovered content

### 1.1 Concept Extraction
**What:** Use LLM to extract key concepts, entities, and themes from each discovery

**Implementation:**
```python
# src/core/analysis/concept_extractor.py

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
        
        prompt = f'''
        Analyze this content and extract:
        
        1. Main concepts (3-5 key topics)
        2. Named entities (companies, people, technologies)
        3. Central themes (what's the story about?)
        4. Sentiment (positive/negative/neutral + why)
        5. Connections (what other topics does this relate to?)
        6. Time sensitivity (news, evergreen, trending)
        
        Content: {content[:2000]}
        
        Return as structured JSON.
        '''
        
        # Use existing AI service (Gemini/GPT-4)
        concepts = await self.ai_service.analyze(prompt)
        
        return ConceptGraph(
            concepts=concepts['main_concepts'],
            entities=concepts['entities'],
            themes=concepts['themes'],
            sentiment=concepts['sentiment'],
            connections=concepts['connections'],
            time_sensitivity=concepts['time_sensitivity']
        )
```

**Database Schema:**
```sql
-- New table for concept extraction
CREATE TABLE content_concepts (
    id BIGSERIAL PRIMARY KEY,
    discovery_id BIGINT REFERENCES discoveries(id),
    concepts JSONB,           -- ["AI", "regulation", "EU"]
    entities JSONB,           -- ["OpenAI", "Sam Altman"]
    themes JSONB,             -- ["AI regulation", "tech policy"]
    sentiment JSONB,          -- {"score": 0.7, "reasoning": "..."}
    connections JSONB,        -- ["crypto", "privacy", "censorship"]
    time_sensitivity TEXT,    -- "news", "evergreen", "trending"
    extracted_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_concepts_gin ON content_concepts USING GIN (concepts);
CREATE INDEX idx_entities_gin ON content_concepts USING GIN (entities);
```

**Integration Point:**
- Add to `autonomous_discovery.py` after quality scoring
- Extract concepts for discoveries with score > 0.7
- Store in new `content_concepts` table

### 1.2 Knowledge Graph Building
**What:** Connect related discoveries based on shared concepts

```python
# src/core/learning/knowledge_graph.py

class KnowledgeGraph:
    """Build and query knowledge graph of discoveries"""
    
    async def add_discovery(self, discovery_id: int, concepts: ConceptGraph):
        """Add discovery to knowledge graph"""
        
        # Find related discoveries
        related = await self.find_related(concepts)
        
        # Create connections
        for rel in related:
            await self.db.execute('''
                INSERT INTO discovery_connections (
                    discovery_a, discovery_b, 
                    shared_concepts, connection_strength
                ) VALUES ($1, $2, $3, $4)
            ''', discovery_id, rel.id, rel.shared_concepts, rel.strength)
    
    async def find_related(self, concepts: ConceptGraph) -> List[Discovery]:
        """Find discoveries with similar concepts"""
        
        # Use PostgreSQL similarity or vector search
        query = '''
            SELECT d.*, 
                   array_length(array_intersect(c.concepts, $1), 1) as overlap
            FROM discoveries d
            JOIN content_concepts c ON c.discovery_id = d.id
            WHERE c.concepts && $1  -- Array overlap operator
            ORDER BY overlap DESC
            LIMIT 20
        '''
        
        return await self.db.fetch(query, concepts.concepts)
```

**New Database Tables:**
```sql
CREATE TABLE discovery_connections (
    id BIGSERIAL PRIMARY KEY,
    discovery_a BIGINT REFERENCES discoveries(id),
    discovery_b BIGINT REFERENCES discoveries(id),
    shared_concepts JSONB,
    connection_strength FLOAT,  -- 0.0 to 1.0
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conn_a ON discovery_connections(discovery_a);
CREATE INDEX idx_conn_b ON discovery_connections(discovery_b);
```

---

## 📋 Phase 2: Similarity Search & Expansion (Weeks 3-4)

### Goal: "Find more like this" - autonomous content expansion

### 2.1 Embedding-Based Similarity
**What:** Generate embeddings for all content, enable vector search

**Implementation:**
```python
# src/core/indexing/similarity_search.py

class SimilaritySearch:
    """Semantic similarity search using embeddings"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()  # Use existing
        self.vector_db = VectorDB()  # pgvector or FAISS
    
    async def index_discovery(self, discovery: Discovery):
        """Generate and store embedding"""
        
        # Combine title + content + concepts
        text = f"{discovery.title}\n{discovery.content}\n"
        text += " ".join(discovery.concepts)
        
        # Generate embedding (OpenAI ada-002 or local model)
        embedding = await self.embedding_service.embed(text)
        
        # Store in vector DB
        await self.vector_db.insert(discovery.id, embedding)
    
    async def find_similar(self, discovery_id: int, limit: int = 10) -> List[Discovery]:
        """Find similar discoveries"""
        
        # Get embedding
        embedding = await self.vector_db.get_embedding(discovery_id)
        
        # Vector similarity search
        similar_ids = await self.vector_db.search(embedding, limit)
        
        # Fetch discoveries
        return await self.db.fetch_discoveries(similar_ids)
```

**Database (pgvector extension):**
```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Add embedding column to discoveries
ALTER TABLE discoveries 
ADD COLUMN embedding vector(1536);  -- OpenAI ada-002 dimension

-- Create index for fast similarity search
CREATE INDEX idx_discoveries_embedding 
ON discoveries USING ivfflat (embedding vector_cosine_ops);

-- Similarity search query
-- SELECT id, title, 1 - (embedding <=> $1) as similarity
-- FROM discoveries
-- ORDER BY embedding <=> $1  -- Cosine distance
-- LIMIT 10;
```

### 2.2 Autonomous Content Expansion
**What:** When user saves a discovery, automatically find and fetch more like it

```python
# src/services/smart_expansion.py

class SmartExpansion:
    """Automatically expand on interesting discoveries"""
    
    async def expand_discovery(self, discovery_id: int):
        """
        When user saves/likes a discovery:
        1. Find similar content in database
        2. Extract common themes
        3. Generate search queries
        4. Execute searches
        5. Add new discoveries
        """
        
        # Get the discovery
        discovery = await self.db.get_discovery(discovery_id)
        
        # Extract concepts if not already done
        concepts = await self.concept_extractor.extract(discovery)
        
        # Find similar in database
        similar = await self.similarity_search.find_similar(discovery_id, 20)
        
        # Analyze patterns across similar content
        patterns = await self.analyze_patterns(similar)
        
        # Ask LLM to suggest search queries
        search_queries = await self.generate_search_queries(
            discovery, concepts, patterns
        )
        
        # Execute searches
        for query in search_queries:
            await self.execute_discovery_search(query)
    
    async def generate_search_queries(
        self, 
        discovery: Discovery,
        concepts: ConceptGraph,
        patterns: List[Pattern]
    ) -> List[str]:
        """Use LLM to generate search queries"""
        
        prompt = f'''
        Given this interesting content:
        
        Title: {discovery.title}
        Concepts: {concepts.concepts}
        Themes: {concepts.themes}
        
        And these patterns from similar content:
        {patterns}
        
        Generate 5 search queries to find MORE content like this.
        Make queries specific but not too narrow.
        Focus on:
        - Emerging trends related to these concepts
        - Alternative perspectives
        - Deeper technical details
        - Recent developments
        - Expert discussions
        
        Return as JSON array of strings.
        '''
        
        return await self.ai_service.query(prompt)
```

---

## 📋 Phase 3: LLM-Guided Discovery (Weeks 5-6)

### Goal: LLM acts as a research assistant, guiding discovery

### 3.1 Autonomous Research Agent
**What:** Give LLM access to current best content and let it guide discovery

```python
# src/agents/discovery_agent.py

class DiscoveryAgent:
    """LLM-powered autonomous discovery agent"""
    
    async def research_session(self, topic: str = None):
        """
        Run an autonomous research session:
        1. Review recent high-quality discoveries
        2. Identify knowledge gaps
        3. Suggest research directions
        4. Execute searches
        5. Analyze results
        6. Repeat
        """
        
        # Get context: recent top discoveries
        top_discoveries = await self.db.fetch('''
            SELECT * FROM discoveries
            WHERE quality_score > 0.8
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        
        # Get concept distribution
        concept_distribution = await self.analyze_concepts(top_discoveries)
        
        # Ask LLM for research plan
        research_plan = await self.generate_research_plan(
            topic, top_discoveries, concept_distribution
        )
        
        # Execute research plan
        for direction in research_plan['directions']:
            discoveries = await self.research_direction(direction)
            await self.analyze_and_store(discoveries)
            
            # Feed results back to LLM for next iteration
            feedback = await self.evaluate_results(direction, discoveries)
            
            if feedback['promising']:
                # Go deeper
                await self.deep_dive(direction, discoveries)
    
    async def generate_research_plan(
        self,
        topic: str,
        context: List[Discovery],
        concepts: Dict
    ) -> Dict:
        """LLM generates research plan"""
        
        prompt = f'''
        You are a research AI helping discover valuable content.
        
        Current focus: {topic or "general intelligence gathering"}
        
        Recent high-quality discoveries:
        {self.format_discoveries(context[:10])}
        
        Concept distribution:
        {concepts}
        
        Based on this context:
        1. What knowledge gaps do you see?
        2. What emerging trends should we investigate?
        3. What related topics might be valuable?
        4. What specific searches would be most productive?
        
        Generate a research plan with:
        - 5 specific research directions
        - Search queries for each direction
        - Expected value/priority for each
        
        Return as structured JSON.
        '''
        
        return await self.llm.query(prompt)
```

### 3.2 Feedback Loop
**What:** Learn from user actions (save/dismiss) to improve discovery

```python
# src/core/learning/feedback_loop.py

class FeedbackLoop:
    """Learn from user behavior to improve discovery"""
    
    async def learn_from_action(self, discovery_id: int, action: str):
        """
        When user saves/dismisses:
        1. Update preference model
        2. Adjust source weights
        3. Refine concept preferences
        4. Adjust search strategies
        """
        
        discovery = await self.db.get_discovery(discovery_id)
        concepts = await self.db.get_concepts(discovery_id)
        
        if action == 'save':
            # Boost similar content
            await self.boost_concepts(concepts.concepts, weight=1.2)
            await self.boost_source(discovery.source, weight=1.1)
            
            # Trigger expansion
            await self.smart_expansion.expand_discovery(discovery_id)
            
        elif action == 'dismiss':
            # Reduce similar content
            await self.reduce_concepts(concepts.concepts, weight=0.8)
            
        # Update LLM context
        await self.update_agent_preferences()
    
    async def update_agent_preferences(self):
        """Update discovery agent with learned preferences"""
        
        preferences = await self.db.fetch('''
            SELECT 
                unnest(c.concepts) as concept,
                AVG(CASE WHEN d.dismissed THEN 0 ELSE 1 END) as score,
                COUNT(*) as frequency
            FROM discoveries d
            JOIN content_concepts c ON c.discovery_id = d.id
            GROUP BY concept
            ORDER BY score DESC, frequency DESC
            LIMIT 50
        ''')
        
        # Give to LLM for next research session
        self.agent.set_preferences(preferences)
```

---

## 📋 Phase 4: Multi-Source Discovery (Weeks 7-8)

### Goal: Expand beyond RSS to dynamic web discovery

### 4.1 Intelligent Web Crawling
**What:** Follow links from high-quality discoveries, discover new sources

```python
# src/core/discovery/intelligent_crawler.py

class IntelligentCrawler:
    """Smart web crawler that discovers new sources"""
    
    async def crawl_from_discovery(self, discovery: Discovery):
        """
        Extract links from high-quality discoveries:
        1. Parse all links
        2. Filter by relevance
        3. Fetch and analyze
        4. Add valuable ones to sources
        """
        
        links = await self.extract_links(discovery.content)
        
        for link in links:
            # Skip known sources
            if await self.is_known_source(link):
                continue
            
            # Fetch and analyze
            content = await self.fetch(link)
            
            # Quick quality check
            quality = await self.quick_quality_check(content)
            
            if quality > 0.7:
                # Add to temporary discovery queue
                await self.add_to_discovery_queue(link, quality)
        
    async def discover_new_sources(self):
        """Find new blogs/sites that consistently produce quality content"""
        
        # Analyze discovery queue
        queue = await self.db.fetch('''
            SELECT domain, COUNT(*) as discoveries, AVG(quality) as avg_quality
            FROM discovery_queue
            GROUP BY domain
            HAVING COUNT(*) >= 3 AND AVG(quality) > 0.75
        ''')
        
        # Add high-quality domains as new sources
        for item in queue:
            await self.add_new_source(item['domain'], item['avg_quality'])
```

### 4.2 Social Signal Discovery
**What:** Monitor Twitter/Reddit for emerging topics

```python
# src/core/discovery/social_signals.py

class SocialSignalDiscovery:
    """Discover emerging topics from social signals"""
    
    async def monitor_social_signals(self):
        """
        Track what's trending:
        1. Monitor Twitter for concept keywords
        2. Track Reddit upvote patterns
        3. Watch GitHub star velocity
        4. Identify emerging narratives
        """
        
        # Get current concept preferences
        concepts = await self.get_top_concepts()
        
        # Monitor Twitter for these concepts
        for concept in concepts[:10]:
            tweets = await self.twitter_api.search(
                concept, 
                min_engagement=100
            )
            
            # Analyze for emerging sub-topics
            emerging = await self.analyze_emerging_topics(tweets)
            
            # Trigger discovery for promising topics
            for topic in emerging:
                await self.discovery_agent.research_session(topic)
```

---

## 📋 Phase 5: Advanced Intelligence (Weeks 9-10)

### 5.1 Predictive Discovery
**What:** Predict what user will find valuable before they see it

```python
# src/core/learning/predictive_model.py

class PredictiveModel:
    """Predict content value before user sees it"""
    
    async def predict_value(self, discovery: Discovery) -> float:
        """
        Machine learning model:
        - Input: concepts, entities, source, time, context
        - Output: predicted user interest (0.0 to 1.0)
        
        Train on historical save/dismiss actions
        """
        
        features = await self.extract_features(discovery)
        prediction = await self.model.predict(features)
        
        return prediction['interest_score']
```

### 5.2 Narrative Tracking
**What:** Track how stories evolve over time

```python
# src/core/analysis/narrative_tracker.py

class NarrativeTracker:
    """Track evolving narratives and story arcs"""
    
    async def track_narrative(self, concept: str):
        """
        Follow how a story develops:
        - Initial emergence
        - Peak coverage
        - New developments
        - Resolution/outcome
        """
        
        timeline = await self.db.fetch('''
            SELECT d.*, c.concepts
            FROM discoveries d
            JOIN content_concepts c ON c.discovery_id = d.id
            WHERE $1 = ANY(c.concepts)
            ORDER BY d.created_at
        ''', concept)
        
        # Analyze narrative arc
        arc = await self.llm.analyze_narrative(timeline)
        
        return NarrativeArc(
            concept=concept,
            emergence_date=arc['emergence'],
            key_moments=arc['key_moments'],
            current_phase=arc['phase'],
            predictions=arc['predictions']
        )
```

### 5.3 Expertise Network
**What:** Track who are the experts on each topic

```python
# src/core/learning/expertise_network.py

class ExpertiseNetwork:
    """Build network of experts and authorities"""
    
    async def identify_experts(self, concept: str):
        """
        Find key voices on a topic:
        - Most cited authors
        - Highest quality content producers
        - Early adopters of concepts
        """
        
        experts = await self.db.fetch('''
            SELECT 
                c.entities->>'author' as author,
                COUNT(*) as content_count,
                AVG(d.quality_score) as avg_quality,
                MIN(d.created_at) as first_mention
            FROM discoveries d
            JOIN content_concepts c ON c.discovery_id = d.id
            WHERE $1 = ANY(c.concepts)
            GROUP BY author
            HAVING COUNT(*) >= 3
            ORDER BY avg_quality DESC
        ''', concept)
        
        # Prioritize content from these experts
        await self.boost_authors(experts)
```

---

## 🎯 Implementation Priority

### Must Have (Phase 1-2): Core Intelligence
1. ✅ **Concept Extraction** - Extract structured concepts from content
2. ✅ **Similarity Search** - Find related content
3. ✅ **Smart Expansion** - Auto-discover more like saved items

### Should Have (Phase 3): Guided Discovery
4. **Discovery Agent** - LLM researches autonomously
5. **Feedback Loop** - Learn from user actions

### Nice to Have (Phase 4-5): Advanced Features
6. **Intelligent Crawling** - Discover new sources
7. **Social Signals** - Monitor trends
8. **Predictive Model** - Predict value
9. **Narrative Tracking** - Follow story arcs
10. **Expertise Network** - Track thought leaders

---

## 📊 Success Metrics

### Quality Metrics
- **Discovery Relevance:** % of discoveries user saves (target: >20%)
- **Expansion Success:** % of expanded discoveries that are saved (target: >30%)
- **Concept Coverage:** Number of unique concepts discovered per week
- **Source Diversity:** Number of unique sources contributing quality content

### Intelligence Metrics
- **Connection Density:** Avg connections per discovery (target: >5)
- **Prediction Accuracy:** How well model predicts user interest (target: >70%)
- **Research Depth:** Levels of discovery depth achieved (target: 3+ levels)
- **Narrative Completeness:** % of emerging stories fully tracked

### System Metrics
- **Processing Speed:** Concepts extracted per minute
- **Storage Efficiency:** Disk usage vs. value delivered
- **API Costs:** LLM API costs per valuable discovery
- **User Engagement:** Time spent in discovery vs. curation

---

## 🚀 Quick Wins (Next 2 Weeks)

### Week 1: Concept Extraction
- [ ] Create `ConceptExtractor` class
- [ ] Add `content_concepts` table to Supabase
- [ ] Integrate into `autonomous_discovery.py`
- [ ] Extract concepts for all new discoveries (score > 0.7)
- [ ] Build simple UI to view concepts

### Week 2: Similarity Search  
- [ ] Set up pgvector extension in Supabase
- [ ] Create `SimilaritySearch` class
- [ ] Generate embeddings for existing discoveries
- [ ] Add "Find similar" button to web UI
- [ ] Test similarity search quality

---

## 💡 Key Insights

### The Self-Improving Loop
The system gets smarter over time because:
1. **Better understanding** - Concepts extracted from each discovery
2. **Better connections** - Knowledge graph grows
3. **Better predictions** - More data to learn from
4. **Better sources** - Discovers new high-quality sources
5. **Better queries** - LLM learns what works

### The Compound Effect
Each improvement multiplies:
- Better concepts → Better connections → Better expansion
- Better predictions → Better curation → Better feedback
- Better sources → Better content → Better learning

### The Intelligence Flywheel
- More discoveries → More concepts learned
- More concepts → Better search queries
- Better queries → More relevant discoveries
- More relevant discoveries → Higher user engagement
- Higher engagement → More feedback
- More feedback → Better predictions
- **LOOP BACK TO START**

---

## 🎓 Learning Resources

### Embeddings & Vector Search
- OpenAI Embeddings API
- pgvector extension for PostgreSQL
- FAISS for local vector search
- Semantic search best practices

### LLM Integration
- Structured output from LLMs (JSON mode)
- Prompt engineering for extraction
- Context window management
- Cost optimization strategies

### Knowledge Graphs
- Graph database basics (Neo4j, NetworkX)
- Entity relationship modeling
- Graph traversal algorithms
- Community detection

---

**Status:** Ready to implement 🚀  
**First Step:** Concept extraction (Week 1)  
**Expected Impact:** 2-3x increase in discovery relevance

---

*"The goal is not just to find content, but to understand it, connect it, and use those connections to discover even more valuable content."*
