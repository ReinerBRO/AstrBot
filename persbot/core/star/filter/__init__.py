import abc

from persbot.core.config import PersbotConfig
from persbot.core.platform.astr_message_event import AstrMessageEvent
from persbot.core.platform.message_type import MessageType


class HandlerFilter(abc.ABC):
    @abc.abstractmethod
    def filter(self, event: AstrMessageEvent, cfg: PersbotConfig) -> bool:
        """是否应当被过滤"""
        raise NotImplementedError


__all__ = ["PersbotConfig", "AstrMessageEvent", "HandlerFilter", "MessageType"]
