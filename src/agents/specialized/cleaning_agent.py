"""
Cleaning Agent

Removes redundant files and directories to keep the workspace clean.
Includes safety checks and verification before deletion.
Enhanced with comprehensive cleanup capabilities including documentation,
log rotation, backup management, deprecated code detection, and more.
"""

import gzip
import json
import logging
import os
import re
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Optional
from langchain_core.messages import AIMessage
from src.agents.specialized.base_specialized import SpecializedAgent
import yaml

logger = logging.getLogger(__name__)


class CleaningAgent(SpecializedAgent):
    """
    The Cleaner: Removes redundant files and directories.
    Provides structured output with cleanup results and safety checks.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__(agent_id="cleaner", agent_name="The Cleaner", role="File Cleanup")
        self.config_path = config_path or "src/agents/config/cleaning_agent.yaml"
        self.config = self._load_config()
        self.workspace_root = Path(__file__).parent.parent.parent.parent
        self.cleanup_stats = {
            "files_removed": 0,
            "directories_removed": 0,
            "files_archived": 0,
            "bytes_freed": 0,
            "errors": []
        }
        self.cleanup_report = {
            "timestamp": None,
            "operations": [],
            "summary": {}
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return yaml.safe_load(f) or {}
            else:
                logger.warning(f"Config file not found: {self.config_path}, using defaults")
                return self._default_config()
        except Exception as e:
            logger.error(f"Failed to load config: {e}, using defaults")
            return self._default_config()
    
    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "cleanup_rules": {
                "remove_pycache": True,
                "remove_backups": True,
                "remove_old_files": True,
                "remove_obsolete_docs": True,
                "remove_test_artifacts": True,
                "remove_temp_files": True
            },
            "safety_checks": {
                "require_verification": True,
                "dry_run": False,
                "backup_before_delete": False
            }
        }
    
    async def _process_impl(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process cleanup task.
        """
        logger.info("🧹 Cleaner starting cleanup...")
        
        # Reset stats
        self.cleanup_stats = {
            "files_removed": 0,
            "directories_removed": 0,
            "files_archived": 0,
            "bytes_freed": 0,
            "errors": []
        }
        self.cleanup_report = {
            "timestamp": datetime.now().isoformat(),
            "operations": [],
            "summary": {}
        }
        
        # Check if verification is required
        if self.config.get("safety_checks", {}).get("require_verification", True):
            verification_result = state.get("artifacts", {}).get("verification_result", {})
            if verification_result.get("verdict") not in ["verified", "questionable"]:
                logger.warning("Verification not passed, skipping cleanup")
                return {
                    "messages": [AIMessage(content="Cleaner: Skipping cleanup - verification not passed")],
                    "artifacts": {
                        "cleanup_result": {
                            "status": "skipped",
                            "reason": "verification_not_passed",
                            "stats": self.cleanup_stats
                        }
                    },
                    "current_agent": "cleaner",
                    "task_status": "cleanup_skipped"
                }
        
        # Perform cleanup
        cleanup_result = await self._perform_cleanup()
        
        return {
            "messages": [AIMessage(content=f"Cleaner: Removed {self.cleanup_stats['files_removed']} files, {self.cleanup_stats['directories_removed']} directories")],
            "artifacts": {"cleanup_result": cleanup_result},
            "current_agent": "cleaner",
            "task_status": "cleanup_complete"
        }
    
    async def _perform_cleanup(self) -> Dict[str, Any]:
        """Perform the actual cleanup operations."""
        dry_run = self.config.get("safety_checks", {}).get("dry_run", False)
        rules = self.config.get("cleanup_rules", {})
        
        cleanup_details = {
            "dry_run": dry_run,
            "rules_applied": [],
            "items_removed": [],
            "stats": self.cleanup_stats.copy()
        }
        
        try:
            # Cleanup completed documentation
            docs_rules = rules.get("docs", {})
            if docs_rules.get("archive_completed", False):
                result = await self._cleanup_completed_docs(dry_run)
                cleanup_details["rules_applied"].append("cleanup_completed_docs")
                cleanup_details["items_removed"].extend(result.get("archived", []))
            
            # Log rotation
            logs_rules = rules.get("logs", {})
            if logs_rules.get("keep_days", 0) > 0:
                result = await self._rotate_logs(dry_run)
                cleanup_details["rules_applied"].append("rotate_logs")
                cleanup_details["items_removed"].extend(result.get("archived", []))
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            # Backup management
            backups_rules = rules.get("backups", {})
            if backups_rules.get("keep_count", 0) > 0 or backups_rules.get("archive_days", 0) > 0:
                result = await self._cleanup_backups(dry_run)
                cleanup_details["rules_applied"].append("cleanup_backups")
                cleanup_details["items_removed"].extend(result.get("archived", []))
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            # Deprecated code detection
            deprecated_rules = rules.get("deprecated_code", {})
            if deprecated_rules.get("detect", False):
                result = await self._identify_deprecated_code(dry_run)
                cleanup_details["rules_applied"].append("identify_deprecated_code")
                cleanup_details["deprecated_items"] = result.get("deprecated_items", [])
            
            # Script organization
            scripts_rules = rules.get("scripts", {})
            if scripts_rules.get("organize_archive", False):
                result = await self._organize_scripts(dry_run)
                cleanup_details["rules_applied"].append("organize_scripts")
                cleanup_details["items_removed"].extend(result.get("moved", []))
            
            # Remove __pycache__ directories (enhanced)
            if rules.get("remove_pycache", True):
                result = await self._remove_pycache_dirs(dry_run)
                cleanup_details["rules_applied"].append("remove_pycache")
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            # Remove backup files (legacy - now handled by _cleanup_backups)
            if rules.get("remove_backups", True) and not backups_rules:
                result = await self._remove_backup_files(dry_run)
                cleanup_details["rules_applied"].append("remove_backups")
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            # Remove old files
            if rules.get("remove_old_files", True):
                result = await self._remove_old_files(dry_run)
                cleanup_details["rules_applied"].append("remove_old_files")
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            # Remove obsolete docs (legacy - now handled by _cleanup_completed_docs)
            if rules.get("remove_obsolete_docs", True) and not docs_rules.get("archive_completed", False):
                result = await self._remove_obsolete_docs(dry_run)
                cleanup_details["rules_applied"].append("remove_obsolete_docs")
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            # Remove test artifacts
            if rules.get("remove_test_artifacts", True):
                result = await self._remove_test_artifacts(dry_run)
                cleanup_details["rules_applied"].append("remove_test_artifacts")
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            # Remove temp files (enhanced)
            if rules.get("remove_temp_files", True):
                result = await self._remove_temp_files(dry_run)
                cleanup_details["rules_applied"].append("remove_temp_files")
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            cleanup_details["stats"] = self.cleanup_stats.copy()
            cleanup_details["status"] = "success" if not dry_run else "dry_run"
            
            # Generate cleanup report
            if not dry_run:
                await self._generate_cleanup_report(cleanup_details)
            
            # Update metrics
            self.metrics["cleanup_count"] = self.metrics.get("cleanup_count", 0) + 1
            self.metrics["last_cleanup_time"] = time.time()
            self.record_metric("files_removed", self.cleanup_stats["files_removed"])
            self.record_metric("directories_removed", self.cleanup_stats["directories_removed"])
            self.record_metric("files_archived", self.cleanup_stats["files_archived"])
            self.record_metric("bytes_freed", self.cleanup_stats["bytes_freed"])
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}", exc_info=True)
            cleanup_details["status"] = "error"
            cleanup_details["error"] = str(e)
            self.cleanup_stats["errors"].append(str(e))
        
        return cleanup_details
    
    async def _remove_pycache_dirs(self, dry_run: bool) -> Dict[str, Any]:
        """Remove __pycache__ directories and other cache directories."""
        removed = []
        cache_patterns = ["__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"]
        
        for pattern in cache_patterns:
            for cache_dir in self.workspace_root.rglob(pattern):
                try:
                    if cache_dir.is_dir():
                        # Check exclusions
                        if self._should_exclude(cache_dir):
                            continue
                        
                        size = self._get_dir_size(cache_dir)
                        if not dry_run:
                            shutil.rmtree(cache_dir)
                            logger.info(f"Removed cache dir: {cache_dir}")
                        else:
                            logger.info(f"[DRY RUN] Would remove cache dir: {cache_dir}")
                        removed.append({
                            "path": str(cache_dir),
                            "type": "directory",
                            "size": size,
                            "pattern": pattern
                        })
                        if not dry_run:
                            self.cleanup_stats["directories_removed"] += 1
                            self.cleanup_stats["bytes_freed"] += size
                except Exception as e:
                    error_msg = f"Failed to remove {cache_dir}: {e}"
                    logger.error(error_msg)
                    self.cleanup_stats["errors"].append(error_msg)
        
        # Also clean node_modules/.cache in frontend
        frontend_cache = self.workspace_root / "frontend" / "node_modules" / ".cache"
        if frontend_cache.exists() and frontend_cache.is_dir():
            try:
                size = self._get_dir_size(frontend_cache)
                if not dry_run:
                    shutil.rmtree(frontend_cache)
                    logger.info(f"Removed frontend cache: {frontend_cache}")
                else:
                    logger.info(f"[DRY RUN] Would remove frontend cache: {frontend_cache}")
                removed.append({
                    "path": str(frontend_cache),
                    "type": "directory",
                    "size": size,
                    "pattern": "node_modules/.cache"
                })
                if not dry_run:
                    self.cleanup_stats["directories_removed"] += 1
                    self.cleanup_stats["bytes_freed"] += size
            except Exception as e:
                error_msg = f"Failed to remove {frontend_cache}: {e}"
                logger.error(error_msg)
                self.cleanup_stats["errors"].append(error_msg)
        
        return {"removed": removed}
    
    async def _remove_backup_files(self, dry_run: bool) -> Dict[str, Any]:
        """Remove backup files (.backup, .OLD, .bak, etc.)."""
        removed = []
        backup_patterns = ["*.backup", "*.OLD", "*.bak", "*.old", "*_backup_*"]
        
        for pattern in backup_patterns:
            for backup_file in self.workspace_root.rglob(pattern):
                try:
                    if backup_file.is_file():
                        size = backup_file.stat().st_size
                        if not dry_run:
                            backup_file.unlink()
                            logger.info(f"Removed backup: {backup_file}")
                        else:
                            logger.info(f"[DRY RUN] Would remove backup: {backup_file}")
                        removed.append({
                            "path": str(backup_file),
                            "type": "file",
                            "size": size
                        })
                        if not dry_run:
                            self.cleanup_stats["files_removed"] += 1
                            self.cleanup_stats["bytes_freed"] += size
                except Exception as e:
                    error_msg = f"Failed to remove {backup_file}: {e}"
                    logger.error(error_msg)
                    self.cleanup_stats["errors"].append(error_msg)
        
        return {"removed": removed}
    
    async def _remove_old_files(self, dry_run: bool, days_old: int = 90) -> Dict[str, Any]:
        """Remove files older than specified days in temp/log directories."""
        removed = []
        current_time = time.time()
        cutoff_time = current_time - (days_old * 24 * 60 * 60)
        
        temp_dirs = ["logs", "var", "tmp", ".tmp"]
        for temp_dir_name in temp_dirs:
            temp_dir = self.workspace_root / temp_dir_name
            if temp_dir.exists() and temp_dir.is_dir():
                for file_path in temp_dir.rglob("*"):
                    try:
                        if file_path.is_file():
                            file_mtime = file_path.stat().st_mtime
                            if file_mtime < cutoff_time:
                                size = file_path.stat().st_size
                                if not dry_run:
                                    file_path.unlink()
                                    logger.info(f"Removed old file: {file_path}")
                                else:
                                    logger.info(f"[DRY RUN] Would remove old file: {file_path}")
                                removed.append({
                                    "path": str(file_path),
                                    "type": "file",
                                    "size": size,
                                    "age_days": (current_time - file_mtime) / (24 * 60 * 60)
                                })
                                if not dry_run:
                                    self.cleanup_stats["files_removed"] += 1
                                    self.cleanup_stats["bytes_freed"] += size
                    except Exception as e:
                        error_msg = f"Failed to remove {file_path}: {e}"
                        logger.error(error_msg)
                        self.cleanup_stats["errors"].append(error_msg)
        
        return {"removed": removed}
    
    async def _remove_obsolete_docs(self, dry_run: bool) -> Dict[str, Any]:
        """Remove obsolete documentation files."""
        removed = []
        obsolete_patterns = ["*.OLD.md", "*_deprecated.md", "*_old.md"]
        docs_dir = self.workspace_root / "docs"
        
        if docs_dir.exists():
            for pattern in obsolete_patterns:
                for doc_file in docs_dir.rglob(pattern):
                    try:
                        if doc_file.is_file():
                            size = doc_file.stat().st_size
                            if not dry_run:
                                doc_file.unlink()
                                logger.info(f"Removed obsolete doc: {doc_file}")
                            else:
                                logger.info(f"[DRY RUN] Would remove obsolete doc: {doc_file}")
                            removed.append({
                                "path": str(doc_file),
                                "type": "file",
                                "size": size
                            })
                            if not dry_run:
                                self.cleanup_stats["files_removed"] += 1
                                self.cleanup_stats["bytes_freed"] += size
                    except Exception as e:
                        error_msg = f"Failed to remove {doc_file}: {e}"
                        logger.error(error_msg)
                        self.cleanup_stats["errors"].append(error_msg)
        
        return {"removed": removed}
    
    async def _remove_test_artifacts(self, dry_run: bool) -> Dict[str, Any]:
        """Remove test artifacts (.pyc, .pytest_cache, etc.)."""
        removed = []
        test_artifact_patterns = ["*.pyc", ".pytest_cache", ".coverage", "htmlcov"]
        
        for pattern in test_artifact_patterns:
            if pattern.startswith("."):
                # Directory pattern
                for artifact_dir in self.workspace_root.rglob(pattern):
                    try:
                        if artifact_dir.is_dir():
                            size = self._get_dir_size(artifact_dir)
                            if not dry_run:
                                shutil.rmtree(artifact_dir)
                                logger.info(f"Removed test artifact dir: {artifact_dir}")
                            else:
                                logger.info(f"[DRY RUN] Would remove test artifact dir: {artifact_dir}")
                            removed.append({
                                "path": str(artifact_dir),
                                "type": "directory",
                                "size": size
                            })
                            if not dry_run:
                                self.cleanup_stats["directories_removed"] += 1
                                self.cleanup_stats["bytes_freed"] += size
                    except Exception as e:
                        error_msg = f"Failed to remove {artifact_dir}: {e}"
                        logger.error(error_msg)
                        self.cleanup_stats["errors"].append(error_msg)
            else:
                # File pattern
                for artifact_file in self.workspace_root.rglob(pattern):
                    try:
                        if artifact_file.is_file():
                            size = artifact_file.stat().st_size
                            if not dry_run:
                                artifact_file.unlink()
                                logger.info(f"Removed test artifact: {artifact_file}")
                            else:
                                logger.info(f"[DRY RUN] Would remove test artifact: {artifact_file}")
                            removed.append({
                                "path": str(artifact_file),
                                "type": "file",
                                "size": size
                            })
                            if not dry_run:
                                self.cleanup_stats["files_removed"] += 1
                                self.cleanup_stats["bytes_freed"] += size
                    except Exception as e:
                        error_msg = f"Failed to remove {artifact_file}: {e}"
                        logger.error(error_msg)
                        self.cleanup_stats["errors"].append(error_msg)
        
        return {"removed": removed}
    
    async def _remove_temp_files(self, dry_run: bool) -> Dict[str, Any]:
        """Remove temporary files (.tmp, .temp, etc.) and clean test_results/ and var/."""
        removed = []
        temp_patterns = ["*.tmp", "*.temp", "*.swp", "*.swo", "*~"]
        
        for pattern in temp_patterns:
            for temp_file in self.workspace_root.rglob(pattern):
                try:
                    if temp_file.is_file() and not self._should_exclude(temp_file):
                        size = temp_file.stat().st_size
                        if not dry_run:
                            temp_file.unlink()
                            logger.info(f"Removed temp file: {temp_file}")
                        else:
                            logger.info(f"[DRY RUN] Would remove temp file: {temp_file}")
                        removed.append({
                            "path": str(temp_file),
                            "type": "file",
                            "size": size
                        })
                        if not dry_run:
                            self.cleanup_stats["files_removed"] += 1
                            self.cleanup_stats["bytes_freed"] += size
                except Exception as e:
                    error_msg = f"Failed to remove {temp_file}: {e}"
                    logger.error(error_msg)
                    self.cleanup_stats["errors"].append(error_msg)
        
        # Clean test_results/ older than 7 days
        test_results_dir = self.workspace_root / "test_results"
        if test_results_dir.exists() and test_results_dir.is_dir():
            current_time = time.time()
            cutoff_time = current_time - (7 * 24 * 60 * 60)  # 7 days
            for file_path in test_results_dir.rglob("*"):
                try:
                    if file_path.is_file():
                        file_mtime = file_path.stat().st_mtime
                        if file_mtime < cutoff_time:
                            size = file_path.stat().st_size
                            if not dry_run:
                                file_path.unlink()
                                logger.info(f"Removed old test result: {file_path}")
                            else:
                                logger.info(f"[DRY RUN] Would remove old test result: {file_path}")
                            removed.append({
                                "path": str(file_path),
                                "type": "file",
                                "size": size,
                                "age_days": (current_time - file_mtime) / (24 * 60 * 60)
                            })
                            if not dry_run:
                                self.cleanup_stats["files_removed"] += 1
                                self.cleanup_stats["bytes_freed"] += size
                except Exception as e:
                    error_msg = f"Failed to remove {file_path}: {e}"
                    logger.error(error_msg)
                    self.cleanup_stats["errors"].append(error_msg)
        
        # Clean var/ directory if exists
        var_dir = self.workspace_root / "var"
        if var_dir.exists() and var_dir.is_dir():
            for file_path in var_dir.rglob("*"):
                try:
                    if file_path.is_file() and not self._should_exclude(file_path):
                        size = file_path.stat().st_size
                        if not dry_run:
                            file_path.unlink()
                            logger.info(f"Removed var file: {file_path}")
                        else:
                            logger.info(f"[DRY RUN] Would remove var file: {file_path}")
                        removed.append({
                            "path": str(file_path),
                            "type": "file",
                            "size": size
                        })
                        if not dry_run:
                            self.cleanup_stats["files_removed"] += 1
                            self.cleanup_stats["bytes_freed"] += size
                except Exception as e:
                    error_msg = f"Failed to remove {file_path}: {e}"
                    logger.error(error_msg)
                    self.cleanup_stats["errors"].append(error_msg)
        
        return {"removed": removed}
    
    def _get_dir_size(self, directory: Path) -> int:
        """Calculate total size of directory in bytes."""
        total_size = 0
        try:
            for file_path in directory.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception as e:
            logger.warning(f"Could not calculate size for {directory}: {e}")
        return total_size
    
    def _should_exclude(self, path: Path) -> bool:
        """Check if a path should be excluded from cleanup."""
        exclusions = self.config.get("exclusions", {})
        exclude_dirs = exclusions.get("exclude_directories", [])
        exclude_patterns = exclusions.get("exclude_patterns", [])
        
        # Check directory exclusions
        for exclude_dir in exclude_dirs:
            if exclude_dir in str(path):
                return True
        
        # Check pattern exclusions
        if path.is_file():
            for pattern in exclude_patterns:
                if path.match(pattern):
                    return True
        
        return False
    
    async def _cleanup_completed_docs(self, dry_run: bool) -> Dict[str, Any]:
        """Archive completed status reports to docs/archive/completed/."""
        archived = []
        docs_dir = self.workspace_root / "docs"
        archive_dir = docs_dir / "archive" / "completed"
        
        if not docs_dir.exists():
            return {"archived": archived}
        
        # Patterns for completed docs
        completed_patterns = [
            "*_COMPLETE.md",
            "*_FINAL*.md",
            "AGENT_*_COMPLETE.md",
            "*_COMPLETE_SUMMARY.md",
            "*_FINAL_STATUS.md"
        ]
        
        # Create archive directory if needed
        if not dry_run:
            archive_dir.mkdir(parents=True, exist_ok=True)
        
        for pattern in completed_patterns:
            for doc_file in docs_dir.glob(pattern):
                try:
                    if doc_file.is_file() and not self._should_exclude(doc_file):
                        size = doc_file.stat().st_size
                        archive_path = archive_dir / doc_file.name
                        
                        if not dry_run:
                            # Move file to archive
                            shutil.move(str(doc_file), str(archive_path))
                            logger.info(f"Archived completed doc: {doc_file} -> {archive_path}")
                        else:
                            logger.info(f"[DRY RUN] Would archive completed doc: {doc_file} -> {archive_path}")
                        
                        archived.append({
                            "path": str(doc_file),
                            "archive_path": str(archive_path),
                            "type": "file",
                            "size": size
                        })
                        if not dry_run:
                            self.cleanup_stats["files_archived"] += 1
                except Exception as e:
                    error_msg = f"Failed to archive {doc_file}: {e}"
                    logger.error(error_msg)
                    self.cleanup_stats["errors"].append(error_msg)
        
        return {"archived": archived}
    
    async def _rotate_logs(self, dry_run: bool) -> Dict[str, Any]:
        """Rotate logs: keep last 7 days, archive older, delete older than 30 days."""
        archived = []
        removed = []
        logs_dir = self.workspace_root / "logs"
        archive_dir = logs_dir / "archive"
        
        if not logs_dir.exists():
            return {"archived": archived, "removed": removed}
        
        logs_rules = self.config.get("cleanup_rules", {}).get("logs", {})
        keep_days = logs_rules.get("keep_days", 7)
        archive_days = logs_rules.get("archive_days", 30)
        archive_location = logs_rules.get("archive_location", "logs/archive/")
        
        current_time = time.time()
        keep_cutoff = current_time - (keep_days * 24 * 60 * 60)
        delete_cutoff = current_time - (archive_days * 24 * 60 * 60)
        
        if not dry_run:
            archive_dir.mkdir(parents=True, exist_ok=True)
        
        for log_file in logs_dir.glob("*.log"):
            try:
                if not log_file.is_file():
                    continue
                
                file_mtime = log_file.stat().st_mtime
                size = log_file.stat().st_size
                age_days = (current_time - file_mtime) / (24 * 60 * 60)
                
                if file_mtime < delete_cutoff:
                    # Delete logs older than archive_days
                    if not dry_run:
                        log_file.unlink()
                        logger.info(f"Deleted old log (>{archive_days} days): {log_file}")
                    else:
                        logger.info(f"[DRY RUN] Would delete old log: {log_file}")
                    removed.append({
                        "path": str(log_file),
                        "type": "file",
                        "size": size,
                        "age_days": age_days
                    })
                    if not dry_run:
                        self.cleanup_stats["files_removed"] += 1
                        self.cleanup_stats["bytes_freed"] += size
                elif file_mtime < keep_cutoff:
                    # Archive logs between keep_days and archive_days
                    archive_path = archive_dir / log_file.name
                    if not dry_run:
                        # Compress and move
                        with open(log_file, 'rb') as f_in:
                            with gzip.open(f"{archive_path}.gz", 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        log_file.unlink()
                        logger.info(f"Archived log: {log_file} -> {archive_path}.gz")
                    else:
                        logger.info(f"[DRY RUN] Would archive log: {log_file} -> {archive_path}.gz")
                    archived.append({
                        "path": str(log_file),
                        "archive_path": str(archive_path) + ".gz",
                        "type": "file",
                        "size": size,
                        "age_days": age_days
                    })
                    if not dry_run:
                        self.cleanup_stats["files_archived"] += 1
            except Exception as e:
                error_msg = f"Failed to rotate log {log_file}: {e}"
                logger.error(error_msg)
                self.cleanup_stats["errors"].append(error_msg)
        
        return {"archived": archived, "removed": removed}
    
    async def _cleanup_backups(self, dry_run: bool) -> Dict[str, Any]:
        """Manage backups: keep last N, archive older, delete older than 90 days."""
        archived = []
        removed = []
        backups_dir = self.workspace_root / "backups"
        archive_dir = backups_dir / "archive"
        
        if not backups_dir.exists():
            return {"archived": archived, "removed": removed}
        
        backups_rules = self.config.get("cleanup_rules", {}).get("backups", {})
        keep_count = backups_rules.get("keep_count", 3)
        archive_days = backups_rules.get("archive_days", 90)
        archive_location = backups_rules.get("archive_location", "backups/archive/")
        
        current_time = time.time()
        delete_cutoff = current_time - (archive_days * 24 * 60 * 60)
        json_delete_cutoff = current_time - (30 * 24 * 60 * 60)  # 30 days for JSON backups
        
        if not dry_run:
            archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Get all database backups
        db_backups = sorted(
            [f for f in backups_dir.glob("*.db") if f.is_file()],
            key=lambda f: f.stat().st_mtime,
            reverse=True
        )
        
        # Keep last N database backups, archive/delete the rest
        for i, backup_file in enumerate(db_backups):
            try:
                file_mtime = backup_file.stat().st_mtime
                size = backup_file.stat().st_size
                age_days = (current_time - file_mtime) / (24 * 60 * 60)
                
                if file_mtime < delete_cutoff:
                    # Delete backups older than archive_days
                    if not dry_run:
                        backup_file.unlink()
                        logger.info(f"Deleted old backup (>{archive_days} days): {backup_file}")
                    else:
                        logger.info(f"[DRY RUN] Would delete old backup: {backup_file}")
                    removed.append({
                        "path": str(backup_file),
                        "type": "file",
                        "size": size,
                        "age_days": age_days
                    })
                    if not dry_run:
                        self.cleanup_stats["files_removed"] += 1
                        self.cleanup_stats["bytes_freed"] += size
                elif i >= keep_count:
                    # Archive backups beyond keep_count
                    archive_path = archive_dir / backup_file.name
                    if not dry_run:
                        shutil.move(str(backup_file), str(archive_path))
                        logger.info(f"Archived backup: {backup_file} -> {archive_path}")
                    else:
                        logger.info(f"[DRY RUN] Would archive backup: {backup_file} -> {archive_path}")
                    archived.append({
                        "path": str(backup_file),
                        "archive_path": str(archive_path),
                        "type": "file",
                        "size": size,
                        "age_days": age_days
                    })
                    if not dry_run:
                        self.cleanup_stats["files_archived"] += 1
            except Exception as e:
                error_msg = f"Failed to process backup {backup_file}: {e}"
                logger.error(error_msg)
                self.cleanup_stats["errors"].append(error_msg)
        
        # Clean up JSON backup files older than 30 days
        for json_backup in backups_dir.rglob("*.json*"):
            try:
                if json_backup.is_file() and not self._should_exclude(json_backup):
                    file_mtime = json_backup.stat().st_mtime
                    if file_mtime < json_delete_cutoff:
                        size = json_backup.stat().st_size
                        if not dry_run:
                            json_backup.unlink()
                            logger.info(f"Deleted old JSON backup: {json_backup}")
                        else:
                            logger.info(f"[DRY RUN] Would delete old JSON backup: {json_backup}")
                        removed.append({
                            "path": str(json_backup),
                            "type": "file",
                            "size": size,
                            "age_days": (current_time - file_mtime) / (24 * 60 * 60)
                        })
                        if not dry_run:
                            self.cleanup_stats["files_removed"] += 1
                            self.cleanup_stats["bytes_freed"] += size
            except Exception as e:
                error_msg = f"Failed to remove JSON backup {json_backup}: {e}"
                logger.error(error_msg)
                self.cleanup_stats["errors"].append(error_msg)
        
        return {"archived": archived, "removed": removed}
    
    async def _identify_deprecated_code(self, dry_run: bool) -> Dict[str, Any]:
        """Identify deprecated code marked with @deprecated or DEPRECATED comments."""
        deprecated_items = []
        deprecated_rules = self.config.get("cleanup_rules", {}).get("deprecated_code", {})
        should_remove = deprecated_rules.get("remove", False)
        
        # Search for deprecated code patterns
        code_patterns = [
            (r"@deprecated", "decorator"),
            (r"#\s*DEPRECATED", "comment"),
            (r"#\s*deprecated", "comment"),
            (r"TODO.*deprecated", "comment"),
            (r"FIXME.*deprecated", "comment")
        ]
        
        # Search in Python files
        for py_file in self.workspace_root.rglob("*.py"):
            try:
                if self._should_exclude(py_file):
                    continue
                
                content = py_file.read_text(encoding='utf-8', errors='ignore')
                lines = content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    for pattern, pattern_type in code_patterns:
                        if re.search(pattern, line, re.IGNORECASE):
                            deprecated_items.append({
                                "file": str(py_file),
                                "line": line_num,
                                "pattern": pattern,
                                "type": pattern_type,
                                "content": line.strip()
                            })
                            break
            except Exception as e:
                logger.warning(f"Could not read {py_file}: {e}")
        
        # Generate report
        if deprecated_items:
            report_path = self.workspace_root / "docs" / "cleanup_reports" / f"deprecated_code_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            if not dry_run:
                report_path.parent.mkdir(parents=True, exist_ok=True)
                with open(report_path, 'w') as f:
                    json.dump({
                        "timestamp": datetime.now().isoformat(),
                        "deprecated_items": deprecated_items,
                        "total_count": len(deprecated_items)
                    }, f, indent=2)
                logger.info(f"Generated deprecated code report: {report_path}")
            else:
                logger.info(f"[DRY RUN] Would generate deprecated code report: {report_path}")
        
        # Optionally remove if safe (with verification)
        if should_remove and not dry_run:
            logger.warning("Auto-removal of deprecated code is enabled but not implemented for safety")
            logger.warning("Please review deprecated code report and remove manually")
        
        return {"deprecated_items": deprecated_items, "report_path": str(report_path) if deprecated_items else None}
    
    async def _organize_scripts(self, dry_run: bool) -> Dict[str, Any]:
        """Organize scripts: move obsolete to archive, organize test scripts."""
        moved = []
        scripts_dir = self.workspace_root / "scripts"
        archive_dir = scripts_dir / "archive"
        old_tests_dir = archive_dir / "old_tests"
        
        if not scripts_dir.exists():
            return {"moved": moved}
        
        scripts_rules = self.config.get("cleanup_rules", {}).get("scripts", {})
        organize_archive = scripts_rules.get("organize_archive", True)
        
        if not dry_run:
            archive_dir.mkdir(parents=True, exist_ok=True)
            old_tests_dir.mkdir(parents=True, exist_ok=True)
        
        # Move old test scripts to archive/old_tests/
        if organize_archive:
            test_patterns = ["test_*.py", "*_test.py", "*test*.py"]
            for pattern in test_patterns:
                for test_script in scripts_dir.glob(pattern):
                    try:
                        if test_script.is_file() and not self._should_exclude(test_script):
                            # Check if it's truly obsolete (e.g., old naming convention)
                            # For now, we'll move scripts with "old" in name or in archive/
                            if "old" in test_script.name.lower() or "archive" in str(test_script.parent):
                                target = old_tests_dir / test_script.name
                                if not dry_run:
                                    shutil.move(str(test_script), str(target))
                                    logger.info(f"Moved old test script: {test_script} -> {target}")
                                else:
                                    logger.info(f"[DRY RUN] Would move old test script: {test_script} -> {target}")
                                moved.append({
                                    "path": str(test_script),
                                    "target": str(target),
                                    "type": "file"
                                })
                    except Exception as e:
                        error_msg = f"Failed to move script {test_script}: {e}"
                        logger.error(error_msg)
                        self.cleanup_stats["errors"].append(error_msg)
        
        return {"moved": moved}
    
    async def _generate_cleanup_report(self, cleanup_details: Dict[str, Any]) -> None:
        """Generate cleanup report and save to docs/cleanup_reports/."""
        report_dir = self.workspace_root / "docs" / "cleanup_reports"
        report_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_path = report_dir / f"cleanup_report_{timestamp}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "files_removed": self.cleanup_stats["files_removed"],
                "directories_removed": self.cleanup_stats["directories_removed"],
                "files_archived": self.cleanup_stats["files_archived"],
                "bytes_freed": self.cleanup_stats["bytes_freed"],
                "errors_count": len(self.cleanup_stats["errors"])
            },
            "operations": cleanup_details.get("rules_applied", []),
            "details": cleanup_details,
            "errors": self.cleanup_stats["errors"]
        }
        
        try:
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            logger.info(f"Generated cleanup report: {report_path}")
            self.cleanup_report = report
        except Exception as e:
            logger.error(f"Failed to generate cleanup report: {e}")
    
    async def run_scheduled_cleanup(self, schedule_type: str = "weekly") -> Dict[str, Any]:
        """Run cleanup on schedule (weekly, monthly, pre-release)."""
        logger.info(f"Running scheduled cleanup: {schedule_type}")
        
        # Adjust rules based on schedule type
        original_rules = self.config.get("cleanup_rules", {}).copy()
        
        if schedule_type == "weekly":
            # Weekly: logs, cache, temp files
            self.config["cleanup_rules"] = {
                "logs": original_rules.get("logs", {}),
                "remove_pycache": True,
                "remove_temp_files": True,
                "remove_test_artifacts": True
            }
        elif schedule_type == "monthly":
            # Monthly: documentation archive
            self.config["cleanup_rules"] = {
                "docs": original_rules.get("docs", {}),
                "backups": original_rules.get("backups", {})
            }
        elif schedule_type == "pre-release":
            # Pre-release: full cleanup
            self.config["cleanup_rules"] = original_rules
        
        # Run cleanup
        state = {
            "artifacts": {
                "verification_result": {"verdict": "verified"}
            }
        }
        
        result = await self._process_impl(state)
        
        # Restore original rules
        self.config["cleanup_rules"] = original_rules
        
        return result
    
    async def health_check(self) -> Dict[str, Any]:
        """Enhanced health check for Cleaning Agent"""
        base_health = await super().health_check()
        
        # Add agent-specific health
        agent_health = {
            **base_health,
            "config_loaded": self.config is not None,
            "workspace_root": str(self.workspace_root),
            "last_cleanup": self.metrics.get("last_cleanup_time"),
            "cleanup_count": self.metrics.get("cleanup_count", 0),
            "total_files_removed": self.metrics.get("files_removed", 0),
            "total_directories_removed": self.metrics.get("directories_removed", 0),
        }
        
        return agent_health

