# Standart imports
import os
import random # For scenario selection
from typing import List, Dict, Tuple, Optional

# Import help modules
from prompt import Prompt  # System prompt for the trainer
from config import Config # Configuration dataclass
from rag_utils import ollama_chat # Ollama API wrappers
from rag_index import RagIndex  # RAG index class
from scenario_preprocessing import load_scenarios, strip_section4_examples  # Scenario loading function

# Main class: RAG dialogue trainer
class DialogueTrainer:
    """
    Implements the 3-message training loop.
    - Message 1: scenario part A + ask confidentiality boundaries only
    - Message 2: feedback on confidentiality + scenario part B+C + ask response + follow-up Q
    - Message 3: feedback on neutrality/emotions + predicted reaction + end
    """

    def __init__(self, cfg: Config, rag: RagIndex, scenarios: List[Dict]):
        self.cfg = cfg
        self.rag = rag
        self.scenarios = scenarios
        self.current_scenario: Optional[Dict] = None
        self.state = 1 # Tracks which message the user is on

    def _build_user_prompt(self, stage: int, scenario: Dict, user_answer: str = "") -> str:
        """
        Builds a user prompt wrapper for the LLM.

        """

        # Retrieve knowledge based on stage + scenario (simple heuristic)
        # Retrieval queries are predefined, as the user input isn't related to the retrieval information.
        if stage == 1:
            retrieval_query = "confidentiality boundaries explain confidentiality safeguarding officer"
        elif stage == 2:
            retrieval_query = "neutrality impartial trauma-sensitive listening follow-up question safeguarding"
        else:
            retrieval_query = "feedback neutrality emotional reaction de-escalation psychologically safe communication"

        retrieved = self.rag.retrieve(retrieval_query, self.cfg.top_k)

        context_block_lines = []
        for score, chunk, meta in retrieved:
            context_block_lines.append(
                f"[source={meta.get('source_file')} chunk={meta.get('chunk_index')} score={score:.3f}]\n{chunk}"
            )
        context_block = "\n\n---\n\n".join(context_block_lines)

        if self.cfg.show_retrieved_chunks:
            print("\n[DEBUG] Retrieved knowledge chunks:")
            for score, _, meta in retrieved:
                print(f"  - {meta.get('source_file')} chunk={meta.get('chunk_index')} score={score:.3f}")
            print()

        # Stage-specific wrapper
        if stage == 1:
            return (
                f"YOU ARE GENERATING: MESSAGE 1\n"
                f"RULES:\n"
                f"- Use ONLY the scenario text provided below.\n"
                f"- Do NOT invent names, ages, events, or extra details.\n"
                f"- Do NOT provide an example confidentiality explanation.\n"
                f"- You MUST follow the output format exactly.\n\n"
                f"- You MUST not explain person's emotions.\n\n"
                f"OUTPUT FORMAT:\n"
                f"[SECTION 1: SCENARIO – PART 1]\n"
                f"(Repeat the Part 1 text exactly as provided.)\n"
                f"[SECTION 2: TASK FOR OFFICER – CONFIDENTIALITY ONLY]\n"
                f"(Instruct the officer to explain confidentiality boundaries ONLY. Then STOP.)\n\n"
                f"=== Scenario (Part 1 / Intro) ===\n{scenario['part_a']}\n"
            )

        if stage == 2:
            return (
                f"YOU ARE GENERATING: MESSAGE 2\n"
                f"RULES:\n"
                f"- Use ONLY the scenario text provided below for Parts 2 and 3.\n"
                f"- Do NOT invent names, ages, events, or extra details.\n"
                f"- Do NOT repeat the officer’s confidentiality message verbatim.\n"
                f"- Do NOT write the officer’s main response.\n"
                f"- Do NOT include any sample/ideal answer.\n"
                f"- Do NOT use quotation marks anywhere in your output.\n"
                f"- When giving a feedback for confidentiality, always be critical but constructive.\n"
                f"- In SECTION 4, output ONLY ONE line starting with 'Officer task:' and then STOP.\n"
                f"- You MUST follow the output format exactly.\n\n"
                f"OUTPUT FORMAT:\n"
                f"[SECTION 1: FEEDBACK ON CONFIDENTIALITY]\n"
                f"(Give reflective feedback on the officer’s confidentiality explanation.)\n"
                f"[SECTION 2: SCENARIO – PART 2]\n"
                f"(Repeat Part 2 exactly as provided. Do not change the details.)\n"
                f"[SECTION 3: SCENARIO – PART 3 (HULPVRAAG)]\n"
                f"(Repeat Part 3 exactly as provided.)\n"
                f"[SECTION 4: INSTRUCTION FOR OFFICER (DO NOT ANSWER)]\n"
                f"Output ONLY this single line and nothing else:\n"
                f"Officer task: Respond neutrally and supportively to the person and end with ONE open follow-up question.\n"
                # f"STOP IMMEDIATELY AFTER THAT LINE.\n\n"
                f"=== Retrieved Guidance Context ===\n{context_block}\n\n"
                f"=== Officer Confidentiality Message (to evaluate) ===\n{user_answer}\n\n"
                f"=== Scenario (Part 2 / Facts) ===\n{scenario['part_b']}\n\n"
                f"=== Scenario (Part 3 / Request) ===\n{scenario['part_c']}\n"
            )

        # stage 3
        twist = scenario.get("part_d", "").strip()
        twist_block = f"\n\n=== Scenario Twist (Optional) ===\n{twist}\n" if twist else ""

        return (
            f"YOU ARE GENERATING: MESSAGE 3\n"
            f"RULES:\n"
            f"- Provide feedback ONLY. Do NOT continue the conversation.\n"
            f"- Do NOT write a new officer message.\n"
            f"- You MUST follow the output format exactly.\n\n"
            f"OUTPUT FORMAT:\n"
            f"[SECTION 1: REFLECTIVE FEEDBACK]\n"
            f"[SECTION 2: END]\n\n"
            f"=== Retrieved Guidance Context ===\n{context_block}\n\n"
            f"=== Officer Main Response (to evaluate) ===\n{user_answer}\n"
            f"{twist_block}"
)
    # Start a new scenario
    def start_scenario(self) -> str:
        self.current_scenario = random.choice(self.scenarios)
        self.stage = 1
        self.history = []
        # Build initial prompt
        prompt = self._build_user_prompt(stage=1, scenario=self.current_scenario)
        response = ollama_chat(
            model=self.cfg.chat_model,
            system=Prompt,
            user=prompt
        )
        return response
    
    def next_turn(self, user_input: str) -> str:
        # Advance the stage and build the stage-specific prompt

        if self.stage == 1:
            prompt = self._build_user_prompt(
                stage=2,
                scenario=self.current_scenario,
                user_answer=user_input
            )
            self.stage = 2

        elif self.stage == 2:
            prompt = self._build_user_prompt(
                stage=3,
                scenario=self.current_scenario,
                user_answer=user_input
            )
            self.stage = 3

        else:
            return "[Dialogue finished. Start a new scenario.]"

        response = ollama_chat(
            model=self.cfg.chat_model,
            system=Prompt,
            user=prompt
        )
        return response
    # Main run loop
    def run(self) -> None:
        # Pick a scenario
        self.current_scenario = random.choice(self.scenarios)
        scenario = self.current_scenario

        print(f"\n[Trainer] Selected scenario: {scenario['id']}\n")

        # -------- Message 1 --------
        print("=== MESSAGE 1 ===")
        msg1_user_prompt = self._build_user_prompt(stage=1, scenario=scenario)
        msg1 = ollama_chat(
            model=self.cfg.chat_model,
            system=Prompt,
            user=msg1_user_prompt
        )
        # Returns LLM output
        print(msg1)

        officer_1 = input("\n[Your response to Message 1]:\n> ").strip()
        # Returns user input
        print(f"[Your response to Message 1]:\n{officer_1}")

        # -------- Message 2 --------
        print("\n=== MESSAGE 2 ===")
        msg2_user_prompt = self._build_user_prompt(stage=2, scenario=scenario, user_answer=officer_1)
        msg2 = ollama_chat(
            model=self.cfg.chat_model,
            system=Prompt,
            user=msg2_user_prompt
        )
        msg2 = strip_section4_examples(msg2)
        print(msg2)

        officer_2 = input("\n[Your response to Message 2]:\n> ").strip()
        print(f"[Your response to Message 2]:\n{officer_2}")

        # -------- Message 3 --------
        print("\n=== MESSAGE 3 ===")
        msg3_user_prompt = self._build_user_prompt(stage=3, scenario=scenario, user_answer=officer_2)
        msg3 = ollama_chat(
            model=self.cfg.chat_model,
            system=Prompt,
            user=msg3_user_prompt
        )
        print(msg3)

        print("\n[Trainer] Dialogue ended.\n")


# Main execution
def main():
    cfg = Config()

    # 1) Check folders exist
    if not os.path.isdir(cfg.knowledge_dir):
        raise FileNotFoundError(f"Missing folder: {cfg.knowledge_dir}")
    if not os.path.isdir(cfg.scenarios_dir):
        raise FileNotFoundError(f"Missing folder: {cfg.scenarios_dir}")

    # 2) Build/Load RAG index
    print("Building/loading knowledge index...")
    rag = RagIndex(cfg)
    rag.build_or_load()
    print(f"Knowledge chunks indexed: {len(rag.chunks)}")

    # 3) Load scenarios
    print("Loading scenarios...")
    scenarios = load_scenarios(cfg.scenarios_dir)
    print(f"Scenarios loaded: {len(scenarios)}")

    # 4) Run trainer
    trainer = DialogueTrainer(cfg, rag, scenarios)
    # Loop for multiple scenarios
    while True:
        trainer.run()
        again = input("Run another scenario? (y/n): ").strip().lower()
        if again != "y":
            break

# Main execution
if __name__ == "__main__":
    main()