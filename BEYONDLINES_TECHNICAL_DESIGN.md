# 🛠️ BEYONDLINES - Technical Design & Architecture

> *Builder's Guide: How the AI Engine Works*

---

## **System Architecture Overview**

### **Microservices Architecture**
```
┌─────────────────────────────────────────────────────────────┐
│                    BEYONDLINES PLATFORM                │
├─────────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────┐  │
│  │  Web App    │    │   API       │    │ Workers   │  │
│  │ (Svelte)  │◄──►│  (FastAPI)  │◄──►│ (RQ)     │  │
│  └─────────────┘    └─────────────┘    └──────────┘  │
│         │                   │                   │      │
│         ▼                   ▼                   ▼      │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────┐  │
│  │ Supabase    │    │   Redis     │    │ Playwright│  │
│  │ (Database)   │    │   (Queue)   │    │ (Browser) │  │
│  └─────────────┘    └─────────────┘    └──────────┘  │
│                                                         │
└─────────────────────────────────────────────────────────────┘
```

### **Technology Stack**

#### **Frontend**
- **Svelte**: Current web dashboard (15+ tabs, 20K+ lines)
- **Future**: React/Next.js mobile-responsive portal
- **Mobile App**: React Native (iOS/Android)

#### **Backend**
- **FastAPI**: RESTful API with async support
- **Python 3.11+**: Core business logic
- **Redis**: Job queue & caching
- **Docker**: Containerized deployment

#### **AI/ML Stack**
- **Primary**: Google Gemini 2.5 Flash-Lite (1,000 RPD free tier)
- **Fallback**: Mistral Large Latest (rotation with 4 keys)
- **Local**: Ollama (last resort, self-hosted)
- **Smart Routing**: Automatic provider switching + cost optimization

#### **Database**
- **Primary**: Supabase (PostgreSQL + real-time)
- **Cache**: SQLite for local development
- **Analytics**: Time-series data for performance tracking

---

## **Core AI Components**

### **1. Voice Authenticity Engine** 🎨

```python
class VoiceAuthenticityEngine:
    """Core AI system for maintaining consistent persona voice"""

    def __init__(self, persona_key: str):
        self.persona = self._load_persona_config(persona_key)
        self.voice_patterns = self._load_voice_patterns(persona_key)
        self.opinions = self._load_opinions(persona_key)
        self.examples = self._load_voice_examples(persona_key)

    def generate_content(self, source_content: str, platform: str) -> str:
        """Generate platform-specific content in authentic voice"""

        # Extract core idea, don't translate
        core_idea = self._extract_essence(source_content)

        # Apply persona voice patterns
        voice_application = {
            'vocabulary': self.voice_patterns['preferred_words'],
            'slang': self.voice_patterns['casual_slang'],
            'language_mixing': self.persona['allow_mixed_language'],
            'quirks': self.voice_patterns['personality_quirks']
        }

        # Platform-specific optimization
        platform_rules = self._get_platform_rules(platform)

        # Generate with AI provider routing
        content = self._call_ai_with_routing(
            prompt=self._build_rewrite_prompt(core_idea, voice_application),
            platform_rules=platform_rules,
            fallback_providers=['gemini', 'mistral', 'ollama']
        )

        # Validate voice consistency
        confidence = self._validate_voice_consistency(content)

        return {
            'content': content,
            'confidence': confidence,
            'platform': platform,
            'persona': self.persona['display_name']
        }
```

### **2. Multi-AI Provider Router** 🤖

```python
class AIProviderRouter:
    """Intelligent routing between AI providers with cost optimization"""

    def __init__(self):
        self.providers = {
            'gemini': {
                'keys': self._load_gemini_keys(),
                'model': 'gemini-2.5-flash-lite',
                'rpm_limit': 15,  # Requests per minute
                'rpd_limit': 1000,  # Requests per day (free tier)
                'cost_per_1k_tokens': 0,
                'current_key_index': 0
            },
            'mistral': {
                'keys': self._load_mistral_keys(),
                'model': 'mistral-large-latest',
                'rpm_limit': 80,
                'rpd_limit': 10000,
                'cost_per_1k_tokens': 0.003,
                'current_key_index': 0
            },
            'ollama': {
                'model': 'llama3.1:8b',
                'cost_per_1k_tokens': 0,
                'latency': 'high',
                'use_last': True
            }
        }

        self.usage_tracker = {}
        self.circuit_breaker = CircuitBreaker()

    def call_ai(self, prompt: str, priority: str = 'normal') -> str:
        """Route call to optimal provider"""

        # Priority: Gemini (free) → Mistral (paid) → Ollama (local)
        providers_in_order = ['gemini', 'mistral', 'ollama']

        for provider_name in providers_in_order:
            if self._can_use_provider(provider_name, priority):
                try:
                    result = self._call_provider(provider_name, prompt)
                    self._track_usage(provider_name, result)
                    return result
                except Exception as e:
                    logger.warning(f"Provider {provider_name} failed: {e}")
                    self._handle_provider_failure(provider_name)
                    continue

        raise AIProviderExhaustedException("All AI providers failed")
```

### **3. Content Discovery & Analysis** 🔍

```python
class ContentDiscoveryEngine:
    """Multi-source content discovery with AI-powered analysis"""

    def __init__(self):
        self.sources = {
            'social': {
                'twitter': TwitterCollector(),
                'reddit': RedditCollector(),
                'threads': ThreadsCollector()
            },
            'rss': {
                'sources': self._load_rss_sources(),  # 60+ curated feeds
                'categories': ['crypto', 'hacking', 'ai', 'startup', 'conspiracy']
            },
            'trending': {
                'github': GitHubTrendingCollector(),
                'news': NewsAPICollector()
            }
        }

    def discover_content(self, user_preferences: dict) -> List[AnalyzedContent]:
        """Discover and analyze relevant content"""

        discovered = []

        # Collect from all sources
        for source_type, sources in self.sources.items():
            for source_name, collector in sources.items():
                raw_content = collector.collect(user_preferences)

                # Analyze each piece of content
                for content in raw_content:
                    analyzed = self._analyze_content(content, user_preferences)
                    if analyzed['value_score'] >= 6.0:  # Quality threshold
                        discovered.append(analyzed)

        # Deduplicate and rank
        unique_content = self._deduplicate(discovered)
        ranked_content = self._rank_by_relevance(unique_content, user_preferences)

        return ranked_content[:50]  # Top 50 pieces

    def _analyze_content(self, content: dict, preferences: dict) -> dict:
        """AI-powered content analysis"""

        analysis_prompt = f"""
        Analyze this content for persona-based rewriting:

        CONTENT: {content['text']}
        SOURCE: {content['platform']} - {content['author']}

        USER PREFERENCES: {preferences}

        Provide:
        1. value_score (0-10): How valuable for social media
        2. rewrite_score (0-10): How suitable for persona rewriting
        3. best_persona: Which persona fits best
        4. key_concepts: 3-5 main concepts
        5. content_type: news, tutorial, opinion, etc.
        6. urgency: same-day, 24-72h, this-week, evergreen
        """

        result = self.ai_router.call_ai(analysis_prompt, priority='high')
        return self._parse_analysis(result, content)
```

### **4. Reply Guy Engine** 💬

```python
class ReplyGuyEngine:
    """Autonomous, contextual reply generation"""

    def __init__(self):
        self.conversation_tracker = ConversationTracker()
        self.relationship_manager = RelationshipManager()
        self.voice_engine = VoiceAuthenticityEngine()

    def monitor_and_reply(self, platforms: List[str]):
        """Monitor conversations and generate replies"""

        while True:
            # Get relevant conversations
            conversations = self._get_relevant_conversations(platforms)

            for conv in conversations:
                if self._should_reply(conv):
                    reply = self._generate_contextual_reply(conv)

                    # Quality check
                    if self._quality_score(reply) >= 0.8:
                        self._send_reply(conv, reply)
                        self._update_relationship(conv['author'], reply)

            time.sleep(60)  # Check every minute

    def _generate_contextual_reply(self, conversation: dict) -> str:
        """Generate authentic, contextual reply"""

        context = {
            'thread_history': conversation['replies'],
            'author_influence': conversation['author_stats'],
            'topic_sentiment': conversation['sentiment'],
            'existing_relationship': self.relationship_manager.get_relationship(conversation['author'])
        }

        reply_prompt = f"""
        You are {self.persona['display_name']}. Reply to this conversation:

        THREAD: {conversation['text']}
        CONTEXT: {context}

        YOUR VOICE: {self.persona['voice_guidelines']}

        Guidelines:
        - Add value, don't just agree
        - Reference previous context if relevant
        - Be authentic to your voice
        - Under 280 characters for Twitter
        - Build relationship subtly
        - Don't be promotional
        """

        return self.voice_engine.generate_content(
            source_content=conversation['text'],
            platform=conversation['platform'],
            custom_prompt=reply_prompt
        )
```

---

## **Database Schema Design**

### **Core Tables**

#### **posts** (Primary Content Store)
```sql
CREATE TABLE posts (
    post_id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    author TEXT NOT NULL,
    author_handle TEXT,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,

    -- Analysis Fields (AI-generated)
    ai_summary TEXT,
    value_score NUMERIC CHECK (value_score >= 0 AND value_score <= 10),
    quality_score NUMERIC CHECK (quality_score >= 0 AND quality_score <= 10),
    rewrite_score NUMERIC CHECK (rewrite_score >= 0 AND rewrite_score <= 10),
    best_persona_key TEXT,
    key_concepts TEXT[],
    content_type TEXT,
    urgency TEXT CHECK (urgency IN ('same-day', '24-72h', 'this-week', 'evergreen')),

    -- Metadata
    analyzed_at TIMESTAMPTZ,
    analysis_model TEXT,
    embedding TEXT,  -- Vector for semantic search
    embedding_model TEXT
);
```

#### **personas** (AI Personalities)
```sql
CREATE TABLE personas (
    persona_key TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    description TEXT,
    language TEXT,
    voice_patterns JSONB,
    opinions JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### **generated_content** (AI Output)
```sql
CREATE TABLE generated_content (
    id BIGSERIAL PRIMARY KEY,
    persona_key TEXT REFERENCES personas(persona_key),
    original_post_id TEXT REFERENCES posts(post_id),
    platform TEXT NOT NULL,
    content TEXT NOT NULL,
    voice_confidence NUMERIC CHECK (voice_confidence >= 0 AND voice_confidence <= 1),
    ai_provider_used TEXT,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    posted_at TIMESTAMPTZ,
    engagement_metrics JSONB
);
```

---

## **Performance & Scalability**

### **Caching Strategy**
```python
class CacheManager:
    """Multi-layer caching for performance"""

    def __init__(self):
        self.memory_cache = {}  # Fastest: in-memory
        self.redis_cache = redis.Redis()  # Medium: distributed
        self.supabase_cache = Supabase()  # Slowest: persistent

    def get(self, key: str, ttl: int = 3600):
        # L1: Memory cache
        if key in self.memory_cache:
            return self.memory_cache[key]

        # L2: Redis cache
        result = self.redis_cache.get(key)
        if result:
            self.memory_cache[key] = result  # Warm L1
            return result

        # L3: Database cache
        result = self.supabase.get_cached(key)
        if result:
            self.redis_cache.setex(key, ttl, result)  # Warm L2
            self.memory_cache[key] = result  # Warm L1
            return result

        return None
```

### **Rate Limiting**
```python
class RateLimiter:
    """Intelligent rate limiting across platforms and AI providers"""

    def __init__(self):
        self.limits = {
            'twitter': {'requests_per_minute': 300, 'requests_per_day': 1500},
            'reddit': {'requests_per_minute': 60, 'requests_per_day': 1000},
            'threads': {'requests_per_minute': 200, 'requests_per_day': 2400},
            'gemini': {'requests_per_minute': 15, 'requests_per_day': 1000},
            'mistral': {'requests_per_minute': 80, 'requests_per_day': 10000}
        }

    def can_make_request(self, service: str) -> tuple[bool, int]:
        """Check if request can be made and wait time if not"""

        key = f"rate_limit:{service}"
        current_count = self.redis.get(key) or 0
        reset_time = self.redis.ttl(key)

        if current_count < self.limits[service]['requests_per_minute']:
            self.redis.incr(key)
            if reset_time == -1:  # Key doesn't exist
                self.redis.expire(key, 60)  # 1 minute window
            return True, 0

        return False, reset_time
```

### **Circuit Breaker Pattern**
```python
class CircuitBreaker:
    """Prevent cascade failures with circuit breaker pattern"""

    def __init__(self, failure_threshold=5, timeout=60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN

    def call(self, func):
        """Execute function with circuit breaker protection"""

        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.timeout:
                self.state = 'HALF_OPEN'
            else:
                raise CircuitBreakerOpenException()

        try:
            result = func()
            if self.state == 'HALF_OPEN':
                self.state = 'CLOSED'
                self.failure_count = 0
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'

            raise e
```

---

## **Security & Privacy**

### **API Security**
```python
class SecurityManager:
    """Security layer for API endpoints"""

    def __init__(self):
        self.rate_limiter = RateLimiter()
        self.auth_manager = AuthManager()

    @middleware
    def secure_endpoint(self, request):
        # Rate limiting
        if not self.rate_limiter.can_make_request(request.client_ip):
            raise HTTPException(429, "Rate limit exceeded")

        # Authentication
        if not self.auth_manager.verify_token(request.headers.get('Authorization')):
            raise HTTPException(401, "Unauthorized")

        # Input validation
        validated_data = self.validate_input(request.json)

        # Output sanitization
        return self.sanitize_output(validated_data)
```

### **Data Encryption**
```python
class EncryptionManager:
    """Data encryption for sensitive information"""

    def __init__(self):
        self.encryption_key = os.getenv('ENCRYPTION_KEY')
        if not self.encryption_key:
            raise ValueError("Encryption key not configured")

    def encrypt_sensitive_data(self, data: str) -> str:
        """Encrypt sensitive data before storage"""

        cipher = AES.new(self.encryption_key, AES.MODE_GCM)
        ciphertext, auth_tag = cipher.encrypt_and_digest(data.encode())

        return base64.b64encode(
            cipher.nonce + auth_tag + ciphertext
        ).decode('utf-8')

    def decrypt_sensitive_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data for use"""

        data = base64.b64decode(encrypted_data)
        nonce, auth_tag, ciphertext = data[:16], data[16:32], data[32:]

        cipher = AES.new(self.encryption_key, AES.MODE_GCM, nonce=nonce)
        return cipher.decrypt_and_verify(ciphertext, auth_tag).decode('utf-8')
```

---

## **Monitoring & Observability**

### **Performance Metrics**
```python
class MetricsCollector:
    """Comprehensive metrics collection"""

    def __init__(self):
        self.prometheus_client = PrometheusClient()
        self.metrics = {
            'ai_requests_total': Counter('ai_requests_total'),
            'ai_request_duration': Histogram('ai_request_duration_seconds'),
            'content_generation_success': Counter('content_generation_success_total'),
            'platform_posts_total': Counter('platform_posts_total'),
            'active_users': Gauge('active_users_total'),
            'system_health': Gauge('system_health_score')
        }

    def track_ai_request(self, provider: str, duration: float, success: bool):
        """Track AI provider performance"""

        self.metrics['ai_requests_total'].labels(provider=provider).inc()
        self.metrics['ai_request_duration'].labels(provider=provider).observe(duration)

        if success:
            self.metrics['content_generation_success'].inc()
        else:
            # Alert on failure
            self.send_alert(f"AI provider {provider} failed after {duration}s")
```

### **Health Checks**
```python
class HealthCheckManager:
    """Comprehensive health monitoring"""

    async def check_system_health(self):
        """Check all system components"""

        health_status = {
            'database': await self._check_database(),
            'redis': await self._check_redis(),
            'ai_providers': await self._check_ai_providers(),
            'external_apis': await self._check_external_apis(),
            'overall': 'healthy'
        }

        # If any component is unhealthy, mark overall as degraded
        if any(status != 'healthy' for status in health_status.values()):
            health_status['overall'] = 'degraded'

        return health_status
```

---

## **Deployment Architecture**

### **Docker Compose Production**
```yaml
version: "3.9"
services:
  redis:
    image: redis:7-alpine
    deploy:
      replicas: 2
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]

  api:
    image: beyondlines/api:latest
    deploy:
      replicas: 3
    environment:
      - REDIS_URL=redis://redis:6379/0
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]

  workers:
    image: beyondlines/worker:latest
    deploy:
      replicas: 5  # Scale based on queue length
    environment:
      - REDIS_URL=redis://redis:6379/0
    command: ["--queue", "publisher", "--queue", "rewriter"]
```

### **Kubernetes Deployment**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: beyondlines-api
spec:
  replicas: 5
  selector:
    matchLabels:
      app: beyondlines-api
  template:
    metadata:
      labels:
        app: beyondlines-api
    spec:
      containers:
      - name: api
        image: beyondlines/api:latest
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
```

---

## **Development Workflow**

### **Local Development Setup**
```bash
# Start all services
docker-compose up -d

# Initialize database
python scripts/migrate_database.py

# Load sample data
python scripts/load_sample_data.py

# Start development server
python -m svelte run src/web/app.py
```

### **Testing Strategy**
```python
# Unit tests
pytest tests/unit/ -v --cov=src

# Integration tests
pytest tests/integration/ -v

# End-to-end tests
pytest tests/e2e/ -v --headless=false

# Performance tests
pytest tests/performance/ -v --benchmark-only
```

---

## **Future Technical Roadmap**

### **Phase 1: Foundation (Current)**
- ✅ Voice Authenticity Engine
- ✅ Multi-AI Provider Routing
- ✅ Content Discovery & Analysis
- ✅ Web Dashboard (Svelte)

### **Phase 2: Scaling (6 months)**
- 🔄 Microservices migration
- 🔄 Redis cluster setup
- 🔄 Database sharding
- 🔄 Mobile app architecture

### **Phase 3: Intelligence (12 months)**
- ⏳ Real-time streaming (Kafka)
- ⏳ Machine learning pipeline
- ⏳ Predictive analytics
- ⏳ Advanced recommendation engine

### **Phase 4: Autonomy (18 months)**
- ⏳ Autonomous decision engine
- ⏳ Self-healing systems
- ⏳ Advanced security layer
- ⏳ Global CDN deployment

---

## **This technical foundation enables BEYONDLINES to scale from personal tool to enterprise AI content platform while maintaining the voice authenticity and intelligence that makes it revolutionary.**
