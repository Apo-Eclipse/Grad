# app.py
# ──────────────────────────────────────────────────────────────
# 1) Windows/grpc.aio event-loop fix (must be first)
# ──────────────────────────────────────────────────────────────
import sys
import asyncio

if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:
    asyncio.get_running_loop()
except RuntimeError:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

# ──────────────────────────────────────────────────────────────
# 2) Imports (after loop fix)
# ──────────────────────────────────────────────────────────────
import re
import streamlit as st
from graphs.behaviour_analyst_sub_graph import behaviour_analyst_super_agent


# ──────────────────────────────────────────────────────────────
# 3) Page setup
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="Behaviour Analyst Chatbot", page_icon="🤖", layout="wide")
st.title("🤖 Behaviour Analyst Chatbot")
st.markdown("Ask me about your spending behavior and patterns!")


# ──────────────────────────────────────────────────────────────
# 4) Session state
# ──────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "user_id" not in st.session_state:
    st.session_state.user_id = "1"


# ──────────────────────────────────────────────────────────────
# 5) Sidebar
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Settings")
    st.session_state.user_id = st.text_input("User ID", value=st.session_state.user_id)
    debug_mode = st.checkbox("Debug Mode", value=False)

    st.markdown("---")
    st.markdown("### Suggested Questions")
    st.markdown(
        """
- I want analysis for Sep 2025
"""
    )

    if st.button("Clear Chat History"):
        st.session_state.messages = []
        st.rerun()


# ──────────────────────────────────────────────────────────────
# 6) Render previous messages
# ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ──────────────────────────────────────────────────────────────
# 7) Multi-line bubble streamer (each "===>" starts new bubble)
# ──────────────────────────────────────────────────────────────
class GroupedBubbleStreamer:
    """
    Every '===>' starts a new bubble.
    All following lines belong to that bubble until the next '===>'.
    """

    _ARROWS = re.compile(r"===>\s*(.*?)\s*(?:<===|$)", re.IGNORECASE)

    def __init__(self):
        self._orig_stdout = sys.stdout
        self._buf = ""
        self.current_agent = None
        self.current_lines = []

    @classmethod
    def _extract_agent(cls, line: str) -> str:
        m = cls._ARROWS.search(line)
        if not m:
            return None
        name = m.group(1).strip()
        if name.lower().endswith("invoked"):
            name = name[: -len("invoked")].strip()
        return name or "Agent"

    def _emit_current_bubble(self):
        if self.current_agent and self.current_lines:
            content = "\n".join(self.current_lines).strip()
            if content:
                with st.chat_message("assistant"):
                    st.markdown(f"### 🤖 {self.current_agent}\n\n{content}")
        # reset buffer
        self.current_lines = []

    def write(self, text: str):
        if not text:
            return
        self._orig_stdout.write(text)
        self._buf += text

        if "\n" in self._buf:
            lines = self._buf.split("\n")
            for raw in lines[:-1]:
                line = raw.strip()
                if not line:
                    continue

                agent = self._extract_agent(line)
                if agent:  # new section
                    self._emit_current_bubble()
                    self.current_agent = agent
                    continue

                # add line to current bubble
                self.current_lines.append(line)

            self._buf = lines[-1]

    def flush(self):
        pass

    def __enter__(self):
        self._old = sys.stdout
        sys.stdout = self
        return self

    def __exit__(self, exc_type, exc, tb):
        sys.stdout = self._old
        if self._buf.strip():
            self.current_lines.append(self._buf.strip())
        self._emit_current_bubble()
        self._buf = ""


# ──────────────────────────────────────────────────────────────
# 8) Main chat flow
# ──────────────────────────────────────────────────────────────
if prompt := st.chat_input("Ask about your spending behavior..."):
    # user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # assistant work
    with st.chat_message("assistant"):
        answer_box = st.empty()
        status = st.status("🔄 Running…", expanded=True)
        with status:
            st.write("Streaming live agent steps…")

        try:
            if debug_mode:
                st.info(f"🐛 Debug: invoking with user_id={st.session_state.user_id}")

            with GroupedBubbleStreamer():
                result = behaviour_analyst_super_agent.invoke(
                    {
                        "request": prompt,
                        "data_acquired": [],
                        "analysis": "no analysis done yet",
                        "message": "no message yet",
                        "sender": "user",
                        "user": st.session_state.user_id,
                    },
                    {"recursion_limit": 500},
                )

            status.update(label="✅ Completed", state="complete", expanded=False)

            # Final = Analysis only
            result = result or {}
            analysis = result.get("analysis") or ""
            data_acquired = result.get("data_acquired") or []

            if not analysis:
                response = (
                    "⚠️ I couldn't generate an analysis.\n\n"
                    "- Try rephrasing your question\n"
                    "- Check data source connection\n"
                    "- Verify your User ID"
                )
            else:
                parts = [f"### 📊 Final Analysis\n{analysis}"]
                if data_acquired:
                    insights = []
                    for i, item in enumerate(data_acquired, 1):
                        if item:
                            insights.append(f"**Insight {i}:** {item}")
                    if insights:
                        parts.append("### 💡 Data Insights\n" + "\n\n".join(insights))
                response = "\n\n".join(parts)

            answer_box.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

            if debug_mode:
                with st.expander("🐛 Debug: Raw Agent Result"):
                    st.json(result)

        except Exception as e:
            msg = (
                f"❌ **Error occurred:**\n\n```\n{e}\n```\n\n"
                "💡 Try:\n"
                "- A different query\n"
                "- Checking data connection\n"
                "- Verifying your User ID"
            )
            answer_box.error(msg)
            st.session_state.messages.append({"role": "assistant", "content": msg})

            with st.expander("🔍 Technical Details"):
                import traceback
                st.code(traceback.format_exc())


# ──────────────────────────────────────────────────────────────
# 9) Footer
# ──────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("*Powered by Multi-Agent System*")