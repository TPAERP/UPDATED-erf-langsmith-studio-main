from schemas import *

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

    return "\n".join([
        f"## Risk {i}: {r['title']}",
        f"**Categories:** {categories_str}",
        "",
        "**Narrative**",
        r["narrative"].strip(),
        reasoning_section,
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