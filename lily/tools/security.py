"""Security tools — let Lily scan text, the clipboard, and the repo for leaked secrets."""

from .. import security
from ..config import ROOT
from . import tool


def _format(findings) -> str:
    return "\n".join(f"• [{f.kind}] line {f.line}: {f.masked}" for f in findings)


@tool(description="Scan a block of text for likely secrets/credentials (masked in the report).")
def scan_text(text: str) -> str:
    findings = security.detect_secrets(text)
    return _format(findings) if findings else "No secrets detected."


@tool(description="Scan the clipboard contents for likely secrets before you paste them.")
def scan_clipboard() -> str:
    try:
        text = security.read_clipboard()
    except security.ClipboardUnavailable as exc:
        return f"[error] {exc}"
    findings = security.detect_secrets(text)
    return _format(findings) if findings else "Clipboard looks clean — no secrets detected."


@tool(description="Scan the project repository for accidentally-committed secrets.")
def scan_repo() -> str:
    results = security.scan_repo(ROOT)
    if not results:
        return "No secrets detected in the repo. ✅"
    return "\n".join(f"• {path}:{f.line} [{f.kind}] {f.masked}" for path, f in results)
