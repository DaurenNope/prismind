"""
Batch Processing Capabilities for Persona Optimization
Allows processing multiple content pieces in parallel for optimization and learning
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

@dataclass
class BatchJob:
    """A batch processing job"""
    id: str
    name: str
    persona_data: Dict[str, Any]
    content_batch: List[Dict[str, Any]]
    platform: str
    created_at: datetime
    status: str  # 'pending', 'running', 'completed', 'failed'
    results: List[Dict[str, Any]] = None
    error: Optional[str] = None
    processing_stats: Dict[str, Any] = None

@dataclass
class BatchResults:
    """Results from batch processing"""
    job_id: str
    total_processed: int
    successful: int
    failed: int
    average_quality: float
    average_ml_confidence: float
    optimization_opportunities: List[str]
    best_performing_content: Dict[str, Any]
    processing_time: float
    insights: Dict[str, Any]

class BatchProcessor:
    """Batch processing system for persona optimization"""

    def __init__(self, rewriter_instance):
        self.rewriter = rewriter_instance
        self.active_jobs: Dict[str, BatchJob] = {}
        self.max_concurrent = 5  # Max parallel content generation
        self.batch_size = 10  # Max content per batch

    async def create_batch_job(self, name: str, persona_data: Dict[str, Any],
                             content_batch: List[Dict[str, Any]],
                             platform: str) -> str:
        """Create a new batch processing job"""

        job_id = f"batch_{int(time.time())}_{len(self.active_jobs)}"

        # Limit batch size for performance
        if len(content_batch) > self.batch_size:
            content_batch = content_batch[:self.batch_size]
            logger.warning(f"Batch size limited to {self.batch_size} items")

        job = BatchJob(
            id=job_id,
            name=name,
            persona_data=persona_data,
            content_batch=content_batch,
            platform=platform,
            created_at=datetime.now(),
            status='pending',
            results=[],
            processing_stats={
                'total_items': len(content_batch),
                'start_time': None,
                'end_time': None,
                'avg_processing_time': 0
            }
        )

        self.active_jobs[job_id] = job
        logger.info(f"Created batch job: {job_id} with {len(content_batch)} items")

        return job_id

    async def process_batch_job(self, job_id: str) -> BatchResults:
        """Process a batch job and return results"""

        job = self.active_jobs.get(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")

        job.status = 'running'
        job.processing_stats['start_time'] = datetime.now()

        try:
            logger.info(f"Starting batch processing for job: {job_id}")

            # Process content in parallel batches
            semaphore = asyncio.Semaphore(self.max_concurrent)
            tasks = []

            for i, content_item in enumerate(job.content_batch):
                task = self._process_content_item(semaphore, job.persona_data, content_item,
                                                  job.platform, i)
                tasks.append(task)

            # Wait for all tasks to complete
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            successful_results = []
            failed_count = 0

            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Content processing failed: {result}")
                    failed_count += 1
                else:
                    successful_results.append(result)

            job.results = successful_results
            job.status = 'completed'
            job.processing_stats['end_time'] = datetime.now()
            job.processing_stats['successful'] = len(successful_results)
            job.processing_stats['failed'] = failed_count

            # Generate batch insights
            batch_results = self._generate_batch_results(job_id, successful_results, failed_count)

            logger.info(f"Batch job {job_id} completed: {len(successful_results)} successful, {failed_count} failed")
            return batch_results

        except Exception as e:
            job.status = 'failed'
            job.error = str(e)
            job.processing_stats['end_time'] = datetime.now()
            logger.error(f"Batch job {job_id} failed: {e}")
            raise

    async def _process_content_item(self, semaphore: asyncio.Semaphore, persona_data: Dict,
                                   content_item: Dict, platform: str, index: int) -> Dict[str, Any]:
        """Process a single content item with semaphore control"""

        async with semaphore:
            start_time = time.time()

            try:
                # Generate content
                result = await self.rewriter.generate_content(
                    persona_data=persona_data,
                    content=content_item,
                    platform=platform
                )

                processing_time = time.time() - start_time

                if result.get('success'):
                    return {
                        'index': index,
                        'success': True,
                        'content': result.get('content'),
                        'quality_score': result.get('quality_score', 0),
                        'advanced_quality_score': result.get('advanced_quality_score', 0),
                        'ml_confidence': result.get('ml_confidence_score', 0),
                        'engagement_prediction': result.get('advanced_engagement_prediction'),
                        'ml_insights': result.get('ml_insights', []),
                        'optimizations': result.get('optimization_opportunities', []),
                        'processing_time': processing_time,
                        'content_data': content_item
                    }
                else:
                    return {
                        'index': index,
                        'success': False,
                        'error': result.get('error', 'Unknown error'),
                        'processing_time': processing_time,
                        'content_data': content_item
                    }

            except Exception as e:
                processing_time = time.time() - start_time
                return {
                    'index': index,
                    'success': False,
                    'error': str(e),
                    'processing_time': processing_time,
                    'content_data': content_item
                }

    def _generate_batch_results(self, job_id: str, successful_results: List[Dict],
                              failed_count: int) -> BatchResults:
        """Generate comprehensive batch processing results"""

        if not successful_results:
            return BatchResults(
                job_id=job_id,
                total_processed=len(successful_results) + failed_count,
                successful=0,
                failed=failed_count,
                average_quality=0.0,
                average_ml_confidence=0.0,
                optimization_opportunities=[],
                best_performing_content={},
                processing_time=0.0,
                insights={'error': 'No successful results'}
            )

        # Calculate averages
        total_quality = sum(r.get('quality_score', 0) for r in successful_results)
        total_advanced_quality = sum(r.get('advanced_quality_score', 0) for r in successful_results)
        total_ml_confidence = sum(r.get('ml_confidence', 0) for r in successful_results)
        total_processing_time = sum(r.get('processing_time', 0) for r in successful_results)

        successful_count = len(successful_results)

        # Find best performing content
        best_content = max(successful_results,
                         key=lambda x: x.get('advanced_quality_score', x.get('quality_score', 0)))

        # Collect optimization opportunities
        all_optimizations = []
        for result in successful_results:
            optimizations = result.get('optimizations', [])
            all_optimizations.extend([opt.get('dimension', 'unknown') for opt in optimizations])

        # Count optimization frequency
        optimization_counts = {}
        for opt in all_optimizations:
            optimization_counts[opt] = optimization_counts.get(opt, 0) + 1

        # Get top optimization opportunities
        top_optimizations = sorted(optimization_counts.items(),
                                 key=lambda x: x[1], reverse=True)[:5]

        # Generate insights
        insights = self._generate_batch_insights(successful_results, failed_count)

        job = self.active_jobs[job_id]
        processing_time = 0
        if job.processing_stats.get('start_time') and job.processing_stats.get('end_time'):
            processing_time = (job.processing_stats['end_time'] - job.processing_stats['start_time']).total_seconds()

        return BatchResults(
            job_id=job_id,
            total_processed=successful_count + failed_count,
            successful=successful_count,
            failed=failed_count,
            average_quality=total_quality / successful_count,
            average_ml_confidence=total_ml_confidence / successful_count,
            optimization_opportunities=[f"{opt} ({count}x)" for opt, count in top_optimizations],
            best_performing_content=best_content,
            processing_time=processing_time,
            insights=insights
        )

    def _generate_batch_insights(self, successful_results: List[Dict],
                               failed_count: int) -> Dict[str, Any]:
        """Generate insights from batch processing results"""

        insights = {
            'quality_distribution': {'high': 0, 'medium': 0, 'low': 0},
            'ml_confidence_distribution': {'high': 0, 'medium': 0, 'low': 0},
            'common_insights': {},
            'performance_metrics': {},
            'recommendations': []
        }

        for result in successful_results:
            # Quality distribution
            quality = result.get('advanced_quality_score', result.get('quality_score', 0))
            if quality >= 0.7:
                insights['quality_distribution']['high'] += 1
            elif quality >= 0.5:
                insights['quality_distribution']['medium'] += 1
            else:
                insights['quality_distribution']['low'] += 1

            # ML confidence distribution
            ml_conf = result.get('ml_confidence', 0)
            if ml_conf >= 0.7:
                insights['ml_confidence_distribution']['high'] += 1
            elif ml_conf >= 0.5:
                insights['ml_confidence_distribution']['medium'] += 1
            else:
                insights['ml_confidence_distribution']['low'] += 1

            # Collect ML insights
            ml_insights = result.get('ml_insights', [])
            for insight in ml_insights:
                insight_type = insight.get('type', 'unknown')
                insights['common_insights'][insight_type] = insights['common_insights'].get(insight_type, 0) + 1

        # Performance metrics
        if successful_results:
            processing_times = [r.get('processing_time', 0) for r in successful_results]
            insights['performance_metrics'] = {
                'avg_processing_time': sum(processing_times) / len(processing_times),
                'min_processing_time': min(processing_times),
                'max_processing_time': max(processing_times),
                'success_rate': len(successful_results) / (len(successful_results) + failed_count)
            }

        # Generate recommendations
        high_quality_count = insights['quality_distribution']['high']
        total_count = len(successful_results)

        if high_quality_count / total_count < 0.5:
            insights['recommendations'].append("Consider refining persona examples for better voice consistency")

        if insights['ml_confidence_distribution']['low'] / total_count > 0.3:
            insights['recommendations'].append("ML confidence is low - provide more diverse persona examples")

        if insights['performance_metrics'].get('avg_processing_time', 0) > 10:
            insights['recommendations'].append("Processing time is high - consider reducing batch size")

        return insights

    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a batch job"""
        job = self.active_jobs.get(job_id)
        if not job:
            return None

        return {
            'job_id': job.id,
            'name': job.name,
            'status': job.status,
            'created_at': job.created_at.isoformat(),
            'total_items': job.processing_stats.get('total_items', 0),
            'successful': job.processing_stats.get('successful', 0),
            'failed': job.processing_stats.get('failed', 0),
            'error': job.error,
            'processing_stats': job.processing_stats
        }

    def get_job_results(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed results of a completed batch job"""
        job = self.active_jobs.get(job_id)
        if not job or job.status != 'completed':
            return None

        return {
            'job_id': job.id,
            'name': job.name,
            'results': job.results,
            'processing_stats': job.processing_stats,
            'completed_at': job.processing_stats.get('end_time')
        }

    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old completed jobs"""
        current_time = datetime.now()
        jobs_to_remove = []

        for job_id, job in self.active_jobs.items():
            age_hours = (current_time - job.created_at).total_seconds() / 3600
            if age_hours > max_age_hours and job.status in ['completed', 'failed']:
                jobs_to_remove.append(job_id)

        for job_id in jobs_to_remove:
            del self.active_jobs[job_id]
            logger.info(f"Cleaned up old batch job: {job_id}")

        return len(jobs_to_remove)

    def get_system_stats(self) -> Dict[str, Any]:
        """Get batch processing system statistics"""
        total_jobs = len(self.active_jobs)
        pending_jobs = sum(1 for job in self.active_jobs.values() if job.status == 'pending')
        running_jobs = sum(1 for job in self.active_jobs.values() if job.status == 'running')
        completed_jobs = sum(1 for job in self.active_jobs.values() if job.status == 'completed')
        failed_jobs = sum(1 for job in self.active_jobs.values() if job.status == 'failed')

        return {
            'total_jobs': total_jobs,
            'pending_jobs': pending_jobs,
            'running_jobs': running_jobs,
            'completed_jobs': completed_jobs,
            'failed_jobs': failed_jobs,
            'max_concurrent': self.max_concurrent,
            'batch_size_limit': self.batch_size
        }