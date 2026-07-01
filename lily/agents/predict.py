"""Predictive assistance agent."""

from .. import predict
from . import Agent, register


def _handle(query: str, messages: list) -> str:
    return predict.format_suggestions()


register(
    Agent(
        name="predict",
        description="Anticipates likely next steps from local usage patterns.",
        handler=_handle,
        triggers=("what next", "predict", "next step", "anticipate"),
    )
)
