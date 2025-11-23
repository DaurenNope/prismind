"""
A/B Testing Framework for Dynamic Rewriter
Allows testing different prompt strategies, personality variations, and content approaches
"""

import json
import logging
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

class TestStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"

class TestType(Enum):
    PROMPT_STRATEGY = "prompt_strategy"
    PERSONALITY_VARIATION = "personality_variation"
    PLATFORM_OPTIMIZATION = "platform_optimization"
    ENGAGEMENT_HOOKS = "engagement_hooks"
    TEMPERATURE_TESTING = "temperature_testing"

class VariantType(Enum):
    CONTROL = "control"
    TREATMENT = "treatment"

@dataclass
class TestVariant:
    """A single variant in an A/B test"""
    id: str
    name: str
    type: VariantType
    description: str
    config: Dict[str, Any]
    traffic_allocation: float  # Percentage of traffic (0.0-1.0)

@dataclass
class TestMetrics:
    """Metrics for a test variant"""
    variant_id: str
    total_requests: int = 0
    successful_generations: int = 0
    avg_quality_score: float = 0.0
    avg_voice_consistency: float = 0.0
    avg_personality_consistency: float = 0.0
    avg_engagement_score: float = 0.0
    total_engagement: int = 0  # Likes, shares, comments (if tracked)

    def update_metrics(self, quality_score: float, voice_consistency: float,
                      personality_consistency: float, engagement_score: float = 0.0):
        """Update running averages with new data point"""
        self.total_requests += 1
        if quality_score > 0:  # Successful generation
            self.successful_generations += 1

            # Update running averages
            n = self.successful_generations
            self.avg_quality_score = ((self.avg_quality_score * (n-1)) + quality_score) / n
            self.avg_voice_consistency = ((self.avg_voice_consistency * (n-1)) + voice_consistency) / n
            self.avg_personality_consistency = ((self.avg_personality_consistency * (n-1)) + personality_consistency) / n
            self.avg_engagement_score = ((self.avg_engagement_score * (n-1)) + engagement_score) / n

@dataclass
class ABTest:
    """An A/B test configuration"""
    id: str
    name: str
    description: str
    type: TestType
    status: TestStatus
    persona_id: str
    platform: Optional[str]  # None for all platforms
    variants: List[TestVariant]
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    min_sample_size: int = 100  # Minimum samples per variant before determining winner
    confidence_threshold: float = 0.95  # Statistical confidence threshold

    def get_variant_by_id(self, variant_id: str) -> Optional[TestVariant]:
        """Get variant by ID"""
        for variant in self.variants:
            if variant.id == variant_id:
                return variant
        return None

class ABTestingEngine:
    """Main A/B testing engine for the Dynamic Rewriter"""

    def __init__(self, storage_path: str = "data/ab_tests"):
        self.storage_path = storage_path
        self.active_tests: Dict[str, ABTest] = {}
        self.test_metrics: Dict[str, Dict[str, TestMetrics]] = {}
        self.load_tests()

    def create_test(self, name: str, description: str, test_type: TestType,
                   persona_id: str, platform: Optional[str] = None,
                   min_sample_size: int = 100, confidence_threshold: float = 0.95) -> str:
        """Create a new A/B test"""
        test_id = str(uuid.uuid4())

        test = ABTest(
            id=test_id,
            name=name,
            description=description,
            type=test_type,
            status=TestStatus.DRAFT,
            persona_id=persona_id,
            platform=platform,
            variants=[],
            created_at=datetime.now(),
            min_sample_size=min_sample_size,
            confidence_threshold=confidence_threshold
        )

        self.active_tests[test_id] = test
        self.test_metrics[test_id] = {}
        self.save_tests()

        logger.info(f"Created A/B test: {name} (ID: {test_id})")
        return test_id

    def add_variant(self, test_id: str, name: str, description: str,
                   config: Dict[str, Any], variant_type: VariantType = VariantType.TREATMENT,
                   traffic_allocation: float = 0.5) -> bool:
        """Add a variant to an existing test"""
        test = self.active_tests.get(test_id)
        if not test or test.status != TestStatus.DRAFT:
            return False

        variant_id = str(uuid.uuid4())
        variant = TestVariant(
            id=variant_id,
            name=name,
            type=variant_type,
            description=description,
            config=config,
            traffic_allocation=traffic_allocation
        )

        test.variants.append(variant)
        self.test_metrics[test_id][variant_id] = TestMetrics(variant_id=variant_id)
        self.save_tests()

        logger.info(f"Added variant {name} to test {test_id}")
        return True

    def start_test(self, test_id: str) -> bool:
        """Start an A/B test"""
        test = self.active_tests.get(test_id)
        if not test or test.status != TestStatus.DRAFT:
            return False

        if len(test.variants) < 2:
            logger.error(f"Test {test_id} needs at least 2 variants to start")
            return False

        # Validate traffic allocation sums to 1.0
        total_allocation = sum(v.traffic_allocation for v in test.variants)
        if abs(total_allocation - 1.0) > 0.01:
            logger.error(f"Traffic allocation must sum to 1.0, got {total_allocation}")
            return False

        test.status = TestStatus.ACTIVE
        test.started_at = datetime.now()
        self.save_tests()

        logger.info(f"Started A/B test: {test.name}")
        return True

    def get_variant_for_request(self, test_id: str, user_id: Optional[str] = None) -> Optional[TestVariant]:
        """Get the appropriate variant for a request based on traffic allocation"""
        test = self.active_tests.get(test_id)
        if not test or test.status != TestStatus.ACTIVE:
            return None

        # Use consistent user assignment if user_id provided
        if user_id:
            import hashlib
            hash_value = int(hashlib.md5(f"{test_id}:{user_id}".encode()).hexdigest()[:8], 16)
            position = hash_value % 1000 / 1000.0  # Normalize to 0-1
        else:
            import random
            position = random.random()

        # Find variant based on cumulative traffic allocation
        cumulative = 0.0
        for variant in test.variants:
            cumulative += variant.traffic_allocation
            if position <= cumulative:
                return variant

        # Fallback to first variant
        return test.variants[0]

    def record_conversion(self, test_id: str, variant_id: str, quality_score: float,
                         voice_consistency: float, personality_consistency: float,
                         engagement_score: float = 0.0):
        """Record a conversion/event for A/B test analysis"""
        if test_id not in self.test_metrics or variant_id not in self.test_metrics[test_id]:
            logger.warning(f"Invalid test_id or variant_id: {test_id}, {variant_id}")
            return

        metrics = self.test_metrics[test_id][variant_id]
        metrics.update_metrics(quality_score, voice_consistency, personality_consistency, engagement_score)

        # Auto-save every 10 conversions
        if metrics.total_requests % 10 == 0:
            self.save_tests()

    def get_test_results(self, test_id: str) -> Dict[str, Any]:
        """Get comprehensive results for an A/B test"""
        test = self.active_tests.get(test_id)
        if not test:
            return {}

        results = {
            'test': asdict(test),
            'variants': [],
            'winner': None,
            'confidence': 0.0,
            'recommendation': 'insufficient_data'
        }

        for variant in test.variants:
            metrics = self.test_metrics[test_id].get(variant.id)
            if metrics:
                variant_data = {
                    'variant': asdict(variant),
                    'metrics': asdict(metrics),
                    'conversion_rate': metrics.successful_generations / max(metrics.total_requests, 1),
                    'avg_quality': metrics.avg_quality_score
                }
                results['variants'].append(variant_data)

        # Determine winner if sufficient data
        if self.has_sufficient_data(test_id):
            winner = self.determine_winner(test_id)
            results['winner'] = winner
            results['confidence'] = self.calculate_confidence(test_id)
            results['recommendation'] = 'declare_winner' if results['confidence'] >= test.confidence_threshold else 'continue_test'

        return results

    def has_sufficient_data(self, test_id: str) -> bool:
        """Check if test has sufficient data to determine winner"""
        test = self.active_tests.get(test_id)
        if not test:
            return False

        for variant in test.variants:
            metrics = self.test_metrics[test_id].get(variant.id)
            if not metrics or metrics.total_requests < test.min_sample_size:
                return False

        return True

    def determine_winner(self, test_id: str) -> Optional[str]:
        """Determine winning variant based on quality scores"""
        test = self.active_tests.get(test_id)
        if not test:
            return None

        best_variant_id = None
        best_score = 0.0

        for variant in test.variants:
            metrics = self.test_metrics[test_id].get(variant.id)
            if metrics and metrics.successful_generations > 0:
                # Use weighted score prioritizing quality over engagement
                score = (metrics.avg_quality_score * 0.5 +
                         metrics.avg_voice_consistency * 0.3 +
                         metrics.avg_personality_consistency * 0.2)

                if score > best_score:
                    best_score = score
                    best_variant_id = variant.id

        return best_variant_id

    def calculate_confidence(self, test_id: str) -> float:
        """Calculate statistical confidence in the winner"""
        # Simplified confidence calculation
        # In production, you'd use proper statistical tests like chi-square or t-test
        test = self.active_tests.get(test_id)
        if not test:
            return 0.0

        winner_id = self.determine_winner(test_id)
        if not winner_id:
            return 0.0

        winner_metrics = self.test_metrics[test_id].get(winner_id)
        if not winner_metrics:
            return 0.0

        # Simple confidence based on sample size and performance difference
        sample_size_bonus = min(winner_metrics.total_requests / test.min_sample_size, 1.0)

        # Find second best variant
        second_best_score = 0.0
        for variant in test.variants:
            if variant.id != winner_id:
                metrics = self.test_metrics[test_id].get(variant.id)
                if metrics:
                    score = (metrics.avg_quality_score * 0.5 +
                            metrics.avg_voice_consistency * 0.3 +
                            metrics.avg_personality_consistency * 0.2)
                    second_best_score = max(second_best_score, score)

        winner_score = (winner_metrics.avg_quality_score * 0.5 +
                       winner_metrics.avg_voice_consistency * 0.3 +
                       winner_metrics.avg_personality_consistency * 0.2)

        performance_diff = max(0, (winner_score - second_best_score) / max(second_best_score, 0.1))

        return min(0.99, sample_size_bonus * 0.5 + performance_diff * 0.5)

    def complete_test(self, test_id: str, winning_variant_id: Optional[str] = None) -> bool:
        """Complete a test and optionally declare a winner"""
        test = self.active_tests.get(test_id)
        if not test or test.status != TestStatus.ACTIVE:
            return False

        test.status = TestStatus.COMPLETED
        test.ended_at = datetime.now()

        if winning_variant_id:
            # Apply winning configuration to the persona
            self.apply_winning_config(test_id, winning_variant_id)

        self.save_tests()
        logger.info(f"Completed A/B test: {test.name}")
        return True

    def apply_winning_config(self, test_id: str, winning_variant_id: str):
        """Apply winning variant configuration to the persona"""
        test = self.active_tests.get(test_id)
        if not test:
            return

        winning_variant = test.get_variant_by_id(winning_variant_id)
        if not winning_variant:
            return

        # This would integrate with the persona management system
        # For now, just log the recommendation
        logger.info(f"Recommended applying config from variant {winning_variant.name} to persona {test.persona_id}")
        logger.info(f"Config: {winning_variant.config}")

    def get_active_tests(self) -> List[Dict[str, Any]]:
        """Get all active tests for frontend display"""
        active_tests = []
        for test_id, test in self.active_tests.items():
            if test.status in [TestStatus.ACTIVE, TestStatus.PAUSED]:
                results = self.get_test_results(test_id)
                active_tests.append(results)
        return active_tests

    def save_tests(self):
        """Save tests to disk"""
        import os
        os.makedirs(self.storage_path, exist_ok=True)

        data = {
            'tests': {test_id: asdict(test) for test_id, test in self.active_tests.items()},
            'metrics': {test_id: {v_id: asdict(metrics) for v_id, metrics in variants.items()}
                      for test_id, variants in self.test_metrics.items()}
        }

        filepath = os.path.join(self.storage_path, "ab_tests.json")
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def load_tests(self):
        """Load tests from disk"""
        import os
        filepath = os.path.join(self.storage_path, "ab_tests.json")

        if not os.path.exists(filepath):
            return

        try:
            with open(filepath, 'r') as f:
                data = json.load(f)

            # Load tests
            for test_id, test_data in data.get('tests', {}).items():
                test_data['created_at'] = datetime.fromisoformat(test_data['created_at'])
                if test_data.get('started_at'):
                    test_data['started_at'] = datetime.fromisoformat(test_data['started_at'])
                if test_data.get('ended_at'):
                    test_data['ended_at'] = datetime.fromisoformat(test_data['ended_at'])

                # Convert enums back
                test_data['type'] = TestType(test_data['type'])
                test_data['status'] = TestStatus(test_data['status'])

                # Convert variants
                variants = []
                for variant_data in test_data.get('variants', []):
                    variant_data['type'] = VariantType(variant_data['type'])
                    variants.append(TestVariant(**variant_data))
                test_data['variants'] = variants

                self.active_tests[test_id] = ABTest(**test_data)

            # Load metrics
            for test_id, variants_data in data.get('metrics', {}).items():
                self.test_metrics[test_id] = {}
                for variant_id, metrics_data in variants_data.items():
                    self.test_metrics[test_id][variant_id] = TestMetrics(**metrics_data)

            logger.info(f"Loaded {len(self.active_tests)} A/B tests from storage")

        except Exception as e:
            logger.error(f"Error loading A/B tests: {e}")