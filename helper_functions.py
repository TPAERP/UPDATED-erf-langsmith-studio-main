from schemas import *
import re

def last_human_content(messages: List[BaseMessage]) -> str:
    """
    Returns the content of the last HumanMessage in the list.
    If none found, returns an empty string.
    """
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            return cast(str, m.content)
    return ""

def format_risk_md(r: RiskDraft, i: int) -> str:
    """
    Formats a single risk draft as markdown, including audit trail and reasoning trace.
    """
    categories = r["category"] if isinstance(r["category"], list) else [r["category"]]
    categories_str = ", ".join(categories)
    
    # Format Audit Trail as a narrative blockquote
    audit_section = ""
    if r.get("audit_log"):
        audit_text = " ".join(r["audit_log"])
        audit_section += f"\n> **Governance History:**\n> {audit_text}\n"
    
    # Format Reasoning Trace
    reasoning_section = ""
    if r.get("reasoning_trace"):
        reasoning_section += f"\n**Analyst Reasoning:**\n{r['reasoning_trace']}\n"

    sources_section = _format_sources_section(r.get("sources") or [])

    return "\n".join([
        f"## Risk {i}: {r['title']}",
        f"**Categories:** {categories_str}",
        "",
        "**Narrative**",
        r["narrative"].strip(),
        reasoning_section,
        sources_section,
        audit_section,
        "",
        "---",
        ""
    ])

def format_all_risks_md(risks: List[RiskDraft]) -> str:
    """
    Formats all risk drafts as markdown.
    """
    md = ["# Risk Register\n"]
    for i, r in enumerate(risks, start=1):
        md.append(format_risk_md(r, i))
    return "\n".join(md)


def _format_sources_section(sources: List[str]) -> str:
    if not sources:
        return ""
    lines = ["**Sources**"]
    for i, entry in enumerate(sources, start=1):
        if isinstance(entry, str) and _is_indexed_source(entry):
            lines.append(entry.strip())
        else:
            lines.append(f"{i}. {entry}")
    return "\n".join(lines)


def _is_indexed_source(entry: str) -> bool:
    if not entry:
        return False
    prefix = entry.lstrip().split(" ", 1)[0].rstrip(".")
    return prefix.isdigit()

def dedupe_risks(risks: List[RiskDraft]) -> List[RiskDraft]:
    """
    Remove exact duplicate risks based on a canonicalized fingerprint.
    Keeps the first occurrence and drops subsequent duplicates.
    """
    def _as_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v) for v in value]
        return [str(value)]

    def _fingerprint(risk: RiskDraft) -> tuple:
        title = str(risk.get("title", "")).strip().lower()

        category_raw = risk.get("category")
        categories = [c.strip().lower() for c in _as_list(category_raw) if str(c).strip()]
        categories_sorted = tuple(sorted(categories))

        narrative = str(risk.get("narrative", "")).strip()
        portfolio_relevance = str(risk.get("portfolio_relevance", "")).strip()
        portfolio_relevance_rationale = str(
            risk.get("portfolio_relevance_rationale", "")
        ).strip()

        sources_raw = risk.get("sources") or []
        sources = [str(s).strip() for s in _as_list(sources_raw) if str(s).strip()]
        sources_sorted = tuple(sorted(sources))

        reasoning_trace = str(risk.get("reasoning_trace", "")).strip()

        audit_log_raw = risk.get("audit_log") or []
        audit_log = tuple(_as_list(audit_log_raw))

        return (
            title,
            categories_sorted,
            narrative,
            portfolio_relevance,
            portfolio_relevance_rationale,
            sources_sorted,
            reasoning_trace,
            audit_log,
        )

    deduped: List[RiskDraft] = []
    seen = set()
    for risk in risks or []:
        key = _fingerprint(risk)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(risk)
    return deduped

def normalize_citations_and_sources(risk: RiskDraft) -> RiskDraft:
    """
    Reindex sources contiguously and rewrite bracket citations to match.
    This prevents mismatches like [3] referencing a source listed as 1.
    """
    sources = risk.get("sources") or []
    if not sources:
        return risk

    entries = []
    for pos, entry in enumerate(sources, start=1):
        old_index = pos
        text = entry
        if isinstance(entry, str):
            stripped = entry.strip()
            match = re.match(r"^(\\d+)\\.\\s*(.+)$", stripped)
            if match:
                old_index = int(match.group(1))
                text = match.group(2).strip()
            else:
                text = stripped
        entries.append({"old_index": old_index, "text": str(text).strip()})

    if not entries:
        return risk

    old_to_new = {e["old_index"]: idx for idx, e in enumerate(entries, start=1)}

    def _rewrite(text: str) -> str:
        if not text:
            return text
        def repl(match: re.Match[str]) -> str:
            idx = int(match.group(1))
            new_idx = old_to_new.get(idx)
            return f"[{new_idx}]" if new_idx is not None else match.group(0)
        return re.sub(r"\\[(\\d+)\\]", repl, text)

    narrative = _rewrite(risk.get("narrative", ""))
    reasoning = _rewrite(risk.get("reasoning_trace", ""))

    new_sources = [f"{i}. {e['text']}" for i, e in enumerate(entries, start=1) if e["text"]]

    return {
        **risk,
        "narrative": narrative,
        "reasoning_trace": reasoning,
        "sources": new_sources,
    }

def format_signposts_md(signposts: List[Signpost]) -> str:
    lines = ["**Signposts (3)**"]
    for sp in signposts:
        lines.append(f"- {sp['description']} — **{sp['status']}**")
    return "\n".join(lines)

def format_conversation(messages: List[Any]) -> str:
    """
    Formats the conversation history from messages into a string.
    """
    conversation = "Conversation history:\n\n"
    for message in messages:
        if isinstance(message, HumanMessage):
            conversation += f"User: {message.content}\n"
        elif isinstance(message, AIMessage):
            conversation += f"Assistant: {message.content}\n"
    return conversation


def format_taxonomy_reports_md(reports: List[TaxonomyWebReport]) -> str:
    """
    Formats per-taxonomy web briefs as markdown, including an explicit source list.
    """
    if not reports:
        return ""

    chunks: List[str] = ["# Horizon Scan — Web Briefs by Taxonomy\n"]

    def _sort_key(r: TaxonomyWebReport) -> str:
        return (r.get("taxonomy") or "").lower()

    for r in sorted(reports, key=_sort_key):
        brief = (r.get("brief_md") or "").strip()
        if brief:
            chunks.append(brief)
        else:
            taxonomy = (r.get("taxonomy") or "").strip() or "Unknown taxonomy"
            chunks.append(f"## {taxonomy}\n\n- No brief generated.")

        sources = r.get("sources") or []
        if sources:
            lines = ["", "**Sources**"]
            for i, s in enumerate(sources[:20], start=1):
                published = f" ({s['published']})" if s.get("published") else ""
                title = s.get("title") or s.get("url") or "Untitled"
                url = s.get("url") or ""
                reliability = s.get("reliability")
                reliability_text = f" — Reliability: {reliability}" if reliability else ""
                lines.append(f"{i}. {title}{published} — {url}{reliability_text}")
            chunks.append("\n".join(lines))

        chunks.append("\n---\n")

    return "\n".join(chunks).strip()
