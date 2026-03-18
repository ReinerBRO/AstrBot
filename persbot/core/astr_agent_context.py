from pydantic import Field
from pydantic.dataclasses import dataclass

from persbot.core.agent.run_context import ContextWrapper
from persbot.core.platform.astr_message_event import AstrMessageEvent
from persbot.core.star.context import Context


@dataclass
class AstrAgentContext:
    __pydantic_config__ = {"arbitrary_types_allowed": True}

    context: Context
    """The star context instance"""
    event: AstrMessageEvent
    """The message event associated with the agent context."""
    extra: dict[str, str] = Field(default_factory=dict)
    """Customized extra data."""


AgentContextWrapper = ContextWrapper[AstrAgentContext]
