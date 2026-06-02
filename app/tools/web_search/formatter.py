"""Format selected web search items into compact generator context."""

from __future__ import annotations

from tools.web_search.models import ContextStrength, WebSearchItem

_UNCERTAINTY_NOTE = (
    "Use this context only if relevant. If selected context is weak or insufficient, "
    "say the available recent context is limited."
)

_EXAM_PREP_ONLY_NOTE = (
    "These sources are exam-prep/supporting sources, not official authority. "
    "Use them only for summary/explanation. Do not present official dates, results, "
    "eligibility, or notification details as confirmed unless official/reputed sources "
    "are present."
)


_WEAK_CONTEXT_SAFE_NOTE = (
    "Reliable recent web sources were limited. Answer carefully and note uncertainty "
    "about recent events. Do not present official dates, results, eligibility, or "
    "notifications as confirmed."
)


class WebContextFormatter:
    """Build [Web Context] section for the generator."""

    @staticmethod
    def format(
        items: list[WebSearchItem],
        *,
        source_pack_name: str,
        attempt_label: str,
        freshness_label: str,
        reason: str,
        search_query: str,
        max_chars: int,
        weak_context: bool = False,
        context_strength: ContextStrength = "authoritative",
    ) -> str:
        if not items and not weak_context:
            return ""

        lines: list[str] = ["[Web Context]"]
        if context_strength in {"authoritative", "mixed", "supporting_only"}:
            lines.append(f"Source strength: {context_strength}")
        if source_pack_name:
            lines.append(f"Source policy: {source_pack_name} / {attempt_label}")
        if freshness_label:
            lines.append(f"Freshness: {freshness_label}")
        if reason and reason not in {"none", ""}:
            lines.append(f"Reason: {reason}")
        if search_query.strip():
            lines.append(f"Search query: {search_query.strip()}")
        if weak_context:
            lines.append("Context quality: limited")
        lines.append("")

        for idx, item in enumerate(items, start=1):
            content = item.snippet.strip()
            if len(content) > 400:
                content = content[:400].rstrip() + "..."
            if len(content) < 20:
                continue
            block_lines = [
                f"{idx}. Title: {item.title.strip() or 'Untitled'}",
                f"   Source: {item.source.strip() or 'unknown'}",
            ]
            if item.published_at:
                block_lines.append(f"   Date: {item.published_at.strip()}")
            block_lines.extend(
                [
                    f"   Content: {content}",
                    f"   URL: {item.url.strip()}",
                ]
            )
            lines.append("\n".join(block_lines))
            lines.append("")

        lines.append("Instruction:")
        if context_strength == "supporting_only":
            lines.append(_EXAM_PREP_ONLY_NOTE)
        else:
            lines.append(_UNCERTAINTY_NOTE)

        context_text = "\n".join(lines).strip()
        if len(context_text) > max_chars:
            context_text = context_text[:max_chars].rstrip()
        return context_text

    @staticmethod
    def format_weak_safe_note(*, max_chars: int) -> str:
        """Safe generator note when web evidence is weak — no rejected snippets."""
        lines = [
            "[Web Context]",
            "Context quality: limited",
            "",
            "Instruction:",
            _WEAK_CONTEXT_SAFE_NOTE,
        ]
        context_text = "\n".join(lines).strip()
        if len(context_text) > max_chars:
            context_text = context_text[:max_chars].rstrip()
        return context_text


def format_web_context(
    items: list[WebSearchItem],
    *,
    max_chars: int,
) -> str:
    """Legacy wrapper — prefer WebContextFormatter.format."""
    return WebContextFormatter.format(
        items,
        source_pack_name="",
        attempt_label="authoritative",
        freshness_label="",
        reason="freshness_required",
        search_query="",
        max_chars=max_chars,
    )


def format_selected_web_context(
    items: list[WebSearchItem],
    *,
    reason: str,
    search_query: str,
    max_chars: int,
    source_pack_name: str = "",
    attempt_label: str = "authoritative",
    freshness_label: str = "",
    weak_context: bool = False,
    context_strength: ContextStrength = "authoritative",
) -> str:
    """Backward-compatible wrapper around WebContextFormatter."""
    return WebContextFormatter.format(
        items,
        source_pack_name=source_pack_name,
        attempt_label=attempt_label,
        freshness_label=freshness_label,
        reason=reason,
        search_query=search_query,
        max_chars=max_chars,
        weak_context=weak_context,
        context_strength=context_strength,
    )
