import re

from persbot.core.config import PersbotConfig
from persbot.core.platform.astr_message_event import AstrMessageEvent

from . import HandlerFilter


# 正则表达式过滤器不会受到 wake_prefix 的制约。
class RegexFilter(HandlerFilter):
    """正则表达式过滤器"""

    def __init__(self, regex: str) -> None:
        self.regex_str = regex
        self.regex = re.compile(regex)

    def filter(self, event: AstrMessageEvent, cfg: PersbotConfig) -> bool:
        return bool(self.regex.search(event.get_message_str().strip()))
