"""Predictive assistance tools."""

from .. import predict
from . import tool


@tool(description="Suggest likely next steps from local timeline/activity patterns.")
def predict_next(limit: int = 5) -> str:
    return predict.format_suggestions(limit)
