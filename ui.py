"""
Shared UI components — Behind The RAG
"""

import streamlit as st
from state import (
    go_next_offline, go_next_online, go_back, jump_to_online, jump_to_offline,
    progress_pct, current_step_num, total_steps
)


def _inject_mobile_css():
    st.markdown("""
<style>
/* ── Prevent horizontal page overflow ── */
.main .block-container {
  max-width: 100vw;
  overflow-x: hidden;
}

/* ── Stack Streamlit columns on mobile ── */
@media (max-width: 768px) {
  [data-testid="stHorizontalBlock"] {
    flex-direction: column !important;
    gap: 0 !important;
  }
  [data-testid="stHorizontalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"],
  [data-testid="stHorizontalBlock"] > div[data-testid="column"] {
    width: 100% !important;
    flex: unset !important;
    min-width: 0 !important;
  }
}

/* ── PM Decision Matrix — desktop table ── */
.pm-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11px;
  font-family: sans-serif;
  border: 1px solid rgba(255,255,255,0.25);
  border-radius: 8px;
  overflow: hidden;
  margin-bottom: 16px;
}
.pm-table th {
  background: #1a2636;
  color: #fff;
  font-weight: 700;
  padding: 9px 11px;
  text-align: left;
  border-right: 1px solid rgba(255,255,255,0.25);
}
.pm-table th:last-child { border-right: none; }
.pm-table td {
  padding: 9px 11px;
  vertical-align: top;
  border-bottom: 1px solid rgba(255,255,255,0.12);
  border-right: 1px solid rgba(255,255,255,0.25);
  line-height: 1.55;
  color: #ffffff;
  font-size: 11px;
}
.pm-table tr:last-child td { border-bottom: none; }
.pm-table td:last-child { border-right: none; }

/* ── PM Decision Matrix — mobile card view ── */
@media (max-width: 768px) {
  .pm-table thead { display: none; }
  .pm-table, .pm-table tbody, .pm-table tr, .pm-table td {
    display: block;
    width: 100%;
    box-sizing: border-box;
  }
  .pm-table tr {
    margin-bottom: 14px;
    border: 1px solid rgba(0,0,0,0.15);
    border-radius: 8px;
    overflow: hidden;
  }
  .pm-table td {
    border-right: none;
    border-bottom: 1px solid rgba(0,0,0,0.08);
    padding: 8px 12px;
    font-size: 12px;
  }
  .pm-table td:last-child { border-bottom: none; }
  .pm-table td::before {
    content: attr(data-label);
    display: block;
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #888;
    margin-bottom: 4px;
  }
  .pm-table td:first-child {
    background: #1a2636 !important;
    padding: 10px 12px;
  }
  .pm-table td:first-child::before { color: #7a9aba; }
  .pm-table td:first-child,
  .pm-table td:first-child strong { color: #fff !important; }
}
</style>
""", unsafe_allow_html=True)


def render_topbar():
    _inject_mobile_css()
    pipeline = st.session_state.get("active_pipeline", "offline")
    label = "📦 Offline pipeline" if pipeline == "offline" else "🔍 Online pipeline"
    pct = progress_pct()
    step_n = current_step_num()
    step_t = total_steps()
    color = "#0F6E56" if pipeline == "offline" else "#185FA5"

    st.markdown(f"""
<div style="display:flex;align-items:center;justify-content:space-between;
padding:8px 0 12px;border-bottom:0.5px solid var(--color-border-tertiary);
margin-bottom:20px">
  <div style="font-size:14px;font-weight:500;color:var(--color-text-primary)">
    🔍 Behind The RAG
  </div>
  <div style="font-size:11px;color:var(--color-text-tertiary)">
    {label} · Step {step_n} of {step_t - 1}
  </div>
</div>
<div style="height:3px;background:var(--color-border-tertiary);
border-radius:2px;margin-bottom:24px">
  <div style="height:3px;width:{pct*100:.0f}%;background:{color};
  border-radius:2px;transition:width 0.3s"></div>
</div>
""", unsafe_allow_html=True)


def render_step_header(icon: str, title: str, subtitle: str = ""):
    st.markdown(f"""
<div style="margin-bottom:16px">
  <div style="font-size:20px;font-weight:500;color:var(--color-text-primary)">
    {icon} {title}
  </div>
  {"<div style='font-size:12px;color:var(--color-text-tertiary);margin-top:4px'>" + subtitle + "</div>" if subtitle else ""}
</div>
""", unsafe_allow_html=True)


def render_thinking_card(text: str, pipeline: str = "online"):
    color = "#0F6E56" if pipeline == "offline" else "#185FA5"
    st.markdown(f"""
<div style="background:var(--color-background-secondary);
border-left:3px solid {color};border-radius:0 8px 8px 0;
padding:12px 16px;margin-bottom:16px;font-size:13px;
color:var(--color-text-secondary);line-height:1.6;font-style:italic">
{text}
</div>
""", unsafe_allow_html=True)


def render_what_we_built(text: str):
    pass  # removed — content covered by step header and thinking card


def render_enterprise_note(text: str):
    with st.expander("🏢 How enterprises do this"):
        st.markdown(f"<div style='font-size:12px;color:var(--color-text-secondary);line-height:1.7'>{text}</div>", unsafe_allow_html=True)


def render_risk_table(risks: list):
    with st.expander("⚠️ What can go wrong"):
        rows = "| Risk | Example | Fix |\n|---|---|---|\n"
        rows += "\n".join(
            f"| **{r['risk']}** | {r['example']} | {r['mitigation']} |"
            for r in risks
        )
        st.markdown(rows)


_PM_COLS_3 = ["PM Decision", "The question to ask", "In this app"]

def render_pm_matrix(title: str, rows: list):
    """Render a 3-column PM Decision Matrix — desktop table, mobile card view."""
    with st.expander(f"📋 PM Takeaways — {title}"):
        thead = "".join(f"<th>{c}</th>" for c in _PM_COLS_3)
        tbody = ""
        for i, row in enumerate(rows):
            bg = "var(--color-background-secondary)" if i % 2 == 0 else "var(--color-background-primary)"
            # row[0]=PM Decision, row[1]=Ask Yourself → "The question to ask", row[4]=Behind The RAG → "In this app"
            c0 = f'<td data-label="{_PM_COLS_3[0]}"><strong>{row[0]}</strong></td>'
            c1 = f'<td data-label="{_PM_COLS_3[1]}">{row[1]}</td>'
            c2 = f'<td data-label="{_PM_COLS_3[2]}">{row[4]}</td>'
            tbody += f'<tr style="background:{bg}">{c0}{c1}{c2}</tr>'
        st.markdown(
            f'<table class="pm-table"><thead><tr>{thead}</tr></thead>'
            f'<tbody>{tbody}</tbody></table>',
            unsafe_allow_html=True,
        )



def render_error_card(error: str):
    st.markdown(f"""
<div style="background:#FCEBEB;border:0.5px solid #F7C1C1;border-radius:8px;
padding:12px 14px;margin:12px 0;font-size:12px;color:#501313;line-height:1.6">
⚠️ <strong>This step hit a snag</strong> — {error}<br>
Showing a pre-computed example so you can continue.
</div>
""", unsafe_allow_html=True)


def render_fallback_badge():
    st.markdown("""
<div style="display:inline-block;background:#FAEEDA;border:0.5px solid #FAC775;
border-radius:4px;padding:2px 8px;font-size:10px;color:#633806;margin-bottom:8px">
⚠️ Pre-computed example — API unavailable
</div>
""", unsafe_allow_html=True)


def render_jump_to_online():
    """Persistent button to jump to online pipeline — shown during offline steps."""
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("Jump to Online Pipeline →", key="jump_online", use_container_width=False):
        jump_to_online()


def render_jump_to_offline():
    """Persistent button to jump to offline pipeline — shown during online steps."""
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    if st.button("← Back to Offline Pipeline", key="jump_offline", use_container_width=False):
        jump_to_offline()


def render_nav(
    back: bool = True,
    next_label: str = "Next →",
    next_disabled: bool = False,
    pipeline: str = "offline",
    show_jump: bool = True,
):
    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    if show_jump and pipeline == "offline":
        render_jump_to_online()
    if show_jump and pipeline == "online":
        render_jump_to_offline()

    cols = st.columns([1, 3, 1])
    with cols[0]:
        if back:
            if st.button("← Back", use_container_width=True):
                go_back()
    with cols[2]:
        clicked = st.button(
            next_label,
            type="primary",
            use_container_width=True,
            disabled=next_disabled,
        )
        if clicked:
            if pipeline == "offline":
                go_next_offline()
            else:
                go_next_online()


def render_gemini_key_prompt():
    st.markdown("---")
    st.markdown("### Add your Gemini API key to continue")
    st.markdown("""
This step needs a live Gemini API call. Get a free key in 2 minutes:

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Click **Get API key**
3. Paste it below — no credit card required
""")
    key = st.text_input("Gemini API key", type="password", placeholder="AIza...")
    if key:
        st.session_state.gemini_key = key
        st.session_state.llm_client = None
        st.success("Key saved — ready to continue.")
        st.rerun()


def render_cohere_key_prompt():
    st.markdown("""
<div style="background:#EBF4FD;border:0.5px solid #B5D4F4;border-radius:8px;
padding:12px 14px;margin:12px 0;font-size:12px;color:#0C447C;line-height:1.6">
🔑 <strong>Live re-ranking on custom queries requires a free Cohere API key.</strong><br>
Get one at <a href="https://cohere.com" target="_blank">cohere.com</a> — free tier, no credit card.
Add it in the sidebar under Settings.
</div>
""", unsafe_allow_html=True)
