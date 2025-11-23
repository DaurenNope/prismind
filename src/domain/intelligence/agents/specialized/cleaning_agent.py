"""
Cleaning Agent

Removes redundant files and directories to keep the workspace clean.
Includes safety checks and verification before deletion.
"""

import json
import logging
import os
import shutil
import time
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
            "bytes_freed": 0,
            "errors": []
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
            "bytes_freed": 0,
            "errors": []
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
            # Remove __pycache__ directories
            if rules.get("remove_pycache", True):
                result = await self._remove_pycache_dirs(dry_run)
                cleanup_details["rules_applied"].append("remove_pycache")
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            # Remove backup files
            if rules.get("remove_backups", True):
                result = await self._remove_backup_files(dry_run)
                cleanup_details["rules_applied"].append("remove_backups")
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            # Remove old files
            if rules.get("remove_old_files", True):
                result = await self._remove_old_files(dry_run)
                cleanup_details["rules_applied"].append("remove_old_files")
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            # Remove obsolete docs
            if rules.get("remove_obsolete_docs", True):
                result = await self._remove_obsolete_docs(dry_run)
                cleanup_details["rules_applied"].append("remove_obsolete_docs")
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            # Remove test artifacts
            if rules.get("remove_test_artifacts", True):
                result = await self._remove_test_artifacts(dry_run)
                cleanup_details["rules_applied"].append("remove_test_artifacts")
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            # Remove temp files
            if rules.get("remove_temp_files", True):
                result = await self._remove_temp_files(dry_run)
                cleanup_details["rules_applied"].append("remove_temp_files")
                cleanup_details["items_removed"].extend(result.get("removed", []))
            
            cleanup_details["stats"] = self.cleanup_stats.copy()
            cleanup_details["status"] = "success" if not dry_run else "dry_run"
            
            # Update metrics
            self.metrics["cleanup_count"] = self.metrics.get("cleanup_count", 0) + 1
            self.metrics["last_cleanup_time"] = time.time()
            self.record_metric("files_removed", self.cleanup_stats["files_removed"])
            self.record_metric("directories_removed", self.cleanup_stats["directories_removed"])
            self.record_metric("bytes_freed", self.cleanup_stats["bytes_freed"])
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}", exc_info=True)
            cleanup_details["status"] = "error"
            cleanup_details["error"] = str(e)
            self.cleanup_stats["errors"].append(str(e))
        
        return cleanup_details
    
    async def _remove_pycache_dirs(self, dry_run: bool) -> Dict[str, Any]:
        """Remove __pycache__ directories."""
        removed = []
        for pycache_dir in self.workspace_root.rglob("__pycache__"):
            try:
                if pycache_dir.is_dir():
                    size = self._get_dir_size(pycache_dir)
                    if not dry_run:
                        shutil.rmtree(pycache_dir)
                        logger.info(f"Removed __pycache__: {pycache_dir}")
                    else:
                        logger.info(f"[DRY RUN] Would remove __pycache__: {pycache_dir}")
                    removed.append({
                        "path": str(pycache_dir),
                        "type": "directory",
                        "size": size
                    })
                    if not dry_run:
                        self.cleanup_stats["directories_removed"] += 1
                        self.cleanup_stats["bytes_freed"] += size
            except Exception as e:
                error_msg = f"Failed to remove {pycache_dir}: {e}"
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
        """Remove temporary files (.tmp, .temp, etc.)."""
        removed = []
        temp_patterns = ["*.tmp", "*.temp", "*.swp", "*.swo", "*~"]
        
        for pattern in temp_patterns:
            for temp_file in self.workspace_root.rglob(pattern):
                try:
                    if temp_file.is_file():
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

