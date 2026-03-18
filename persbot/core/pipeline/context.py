from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from persbot.core.config import PersbotConfig

from .context_utils import call_event_hook, call_handler

if TYPE_CHECKING:
    from persbot.core.star import PluginManager


@dataclass
class PipelineContext:
    """上下文对象，包含管道执行所需的上下文信息"""

    persbot_config: PersbotConfig  # Persbot 配置对象
    plugin_manager: PluginManager  # 插件管理器对象
    persbot_config_id: str
    call_handler = call_handler
    call_event_hook = call_event_hook
