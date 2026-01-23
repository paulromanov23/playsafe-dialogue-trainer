# Neccesary imports
import streamlit as st
import re

from app import DialogueTrainer
from config import Config
from rag_index import RagIndex
from scenario_preprocessing import load_scenarios
from prompt import Prompt


# ---------- llm output formatting ----------

def format_llm_output(text: str) -> str:
    """Improve spacing + convert SECTION markers to headers."""
    text = text.replace("\n", "\n\n")
    text = re.sub(
        r"\[SECTION (\d+): ([^\]]+)\]",
        r"### Section \1 — \2",
        text
    )
    return text

# ---------- renderers ----------
def render_assistant(text: str):
    with st.chat_message("assistant", avatar="🤖"):
        st.markdown(format_llm_output(text), unsafe_allow_html=True)


def render_user(text: str):
    with st.chat_message("user", avatar="😀"):
        st.markdown(text)


# ---------- app init ----------

st.set_page_config(page_title="PlaySAFE Trainer", layout="centered")
st.title("🤖 PlaySAFE – Safeguarding Dialogue Trainer")

if "initialized" not in st.session_state:
    cfg = Config()
    rag = RagIndex(cfg)
    rag.build_or_load()
    scenarios = load_scenarios(cfg.scenarios_dir)

    trainer = DialogueTrainer(cfg, rag, scenarios)

    st.session_state.cfg = cfg
    st.session_state.trainer = trainer
    st.session_state.stage = 0
    st.session_state.messages = []
    st.session_state.initialized = True


trainer = st.session_state.trainer


# ---------- start scenario ----------

if st.session_state.stage == 0:
    trainer.current_scenario = None
    trainer.run = None  # prevent terminal loop logic
    scenario = trainer.current_scenario = __import__("random").choice(trainer.scenarios)

    msg1_prompt = trainer._build_user_prompt(stage=1, scenario=scenario)
    msg1 = trainer.rag.llm_chat = trainer.cfg  # noop guard
    msg1 = __import__("rag_utils").ollama_chat(
        model=trainer.cfg.chat_model,
        system=Prompt,
        user=msg1_prompt
    )

    st.session_state.scenario = scenario
    st.session_state.messages = [("assistant", msg1)]
    st.session_state.stage = 1


# ---------- render chat ----------

for role, msg in st.session_state.messages:
    if role == "assistant":
        render_assistant(msg)
    else:
        render_user(msg)


# ---------- stage inputs ----------

if st.session_state.stage in [1, 2]:
    user_input = st.chat_input("Your response…")

    if user_input:
        render_user(user_input)
        st.session_state.messages.append(("user", user_input))

        scenario = st.session_state.scenario

        if st.session_state.stage == 1:
            prompt = trainer._build_user_prompt(
                stage=2,
                scenario=scenario,
                user_answer=user_input
            )
        else:
            prompt = trainer._build_user_prompt(
                stage=3,
                scenario=scenario,
                user_answer=user_input
            )

        response = __import__("rag_utils").ollama_chat(
            model=trainer.cfg.chat_model,
            system=Prompt,
            user=prompt
        )

        render_assistant(response)
        st.session_state.messages.append(("assistant", response))
        st.session_state.stage += 1


# ---------- end + next scenario ----------

if st.session_state.stage == 3:
    st.divider()
    if st.button("▶️ Start next scenario"):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
