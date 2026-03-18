"""Persbot 备份与恢复模块

提供数据导出和导入功能，支持用户在服务器迁移时一键备份和恢复所有数据。
"""

# 从 constants 模块导入共享常量
from .constants import (
    BACKUP_MANIFEST_VERSION,
    KB_METADATA_MODELS,
    MAIN_DB_MODELS,
    get_backup_directories,
)

# 导入导出器和导入器
from .exporter import PersbotExporter
from .importer import PersbotImporter, ImportPreCheckResult

__all__ = [
    "PersbotExporter",
    "PersbotImporter",
    "ImportPreCheckResult",
    "MAIN_DB_MODELS",
    "KB_METADATA_MODELS",
    "get_backup_directories",
    "BACKUP_MANIFEST_VERSION",
]
