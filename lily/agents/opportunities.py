"""The opportunities agent — surface CFPs, CTFs, and the like from RSS/Atom feeds.

Reads only the feeds *you* list in ``rss_feeds`` (default none) — no scraping, no
discovery, no tracking. Feeds are fetched over HTTPS with a hard timeout and cached
briefly; parsing uses the stdlib :mod:`xml.etree` (no feedparser) via the pure
:func:`_parse_feed`, which handles both RSS ``<item>`` and Atom ``<entry>``. New items
are announced on the bus as ``opportunities.found``.
"""

import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from .. import bus
from ..config import RSS_FEEDS
from ..log import get_logger
from . import Agent, register

log = get_logger("opportunities")

_TIMEOUT = 10
_CACHE_TTL = 1800  # seconds
_cache: dict[str, tuple[float, list]] = {}


@dataclass
class Item:
    title: str
    link: str
    summary: str
    source: str = ""


def _local(tag: str) -> str:
    """Strip an XML namespace, returning the local tag name."""
    return tag.rsplit("}", 1)[-1].lower()


def _child_text(elem, *names: str) -> str:
    """First non-empty text (or href) among child elements matching any local ``names``."""
    wanted = set(names)
    for child in elem:
        if _local(child.tag) in wanted:
            text = (child.text or "").strip()
            if text:
                return text
            href = child.attrib.get("href", "").strip()
            if href:
                return href
    return ""


def _parse_feed(xml_text: str, source: str = "") -> list[Item]:
    """Parse RSS or Atom ``xml_text`` into Items. Pure — no network. Empty on parse error."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        log.warning("feed parse error (%s): %s", source, exc)
        return []
    items: list[Item] = []
    for elem in root.iter():
        if _local(elem.tag) in {"item", "entry"}:
            title = _child_text(elem, "title")
            link = _child_text(elem, "link")
            summary = _child_text(elem, "description", "summary", "content")
            if title:
                items.append(Item(title=title, link=link, summary=summary[:300], source=source))
    return items


def fetch_feed(url: str) -> list[Item]:
    """Fetch + parse one feed, with a short TTL cache. Network errors yield []."""
    now = time.time()
    cached = _cache.get(url)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Lily/1.0 (personal feed reader)"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:  # network, DNS, TLS, HTTP error — degrade quietly
        log.warning("feed fetch failed (%s): %s", url, exc)
        return _cache.get(url, (0, []))[1]
    items = _parse_feed(raw, source=url)
    _cache[url] = (now, items)
    return items


def opportunities(limit: int = 10) -> list[Item]:
    """Aggregate items across all configured feeds (newest-first as feeds provide)."""
    found: list[Item] = []
    for url in RSS_FEEDS:
        found.extend(fetch_feed(url))
    return found[:limit]


def _handle(query: str, messages: list) -> str:
    if not RSS_FEEDS:
        return "No feeds configured. Add URLs to rss_feeds (e.g. a CFP or CTFtime feed) to enable this."
    items = opportunities()
    bus.publish("opportunities.found", {"count": len(items)})
    if not items:
        return "Nothing new in your feeds right now."
    lines = ["Here's what's out there:"]
    lines += [f"  • {it.title}" + (f"\n    {it.link}" if it.link else "") for it in items]
    return "\n".join(lines)


register(
    Agent(
        name="opportunities",
        description="Surfaces CFPs, CTFs, and other opportunities from your RSS/Atom feeds.",
        handler=_handle,
        triggers=("opportun", "cfp", "ctftime", "call for paper", "any ctfs"),
    )
)
