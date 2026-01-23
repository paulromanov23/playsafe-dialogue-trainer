import os
import glob
import json
import re
from typing import List, Dict


#Functions for loading and preprocessing scenario data
def load_scenarios(scenarios_dir: str) -> List[Dict]:
    scenario_folders = sorted([
        p for p in glob.glob(os.path.join(scenarios_dir, "scenario_*"))
        if os.path.isdir(p)
    ])
    scenarios = []
    for folder in scenario_folders:
        sid = os.path.basename(folder)

        def read_if_exists(name: str) -> str:
            fp = os.path.join(folder, name)
            return open(fp, "r", encoding="utf-8").read().strip() if os.path.exists(fp) else ""

        scenario = {
            "id": sid,
            "folder": folder,
            "meta": {},
            "part_a": read_if_exists("part_a_intro.txt"),
            "part_b": read_if_exists("part_b_facts.txt"),
            "part_c": read_if_exists("part_c_request.txt"),
            "part_d": read_if_exists("part_d_twist_optional.txt"),
        }

        meta_fp = os.path.join(folder, "meta.json")
        if os.path.exists(meta_fp):
            try:
                scenario["meta"] = json.load(open(meta_fp, "r", encoding="utf-8"))
            except Exception:
                scenario["meta"] = {}

        # Require at least A/B/C
        if scenario["part_a"] and scenario["part_b"] and scenario["part_c"]:
            scenarios.append(scenario)

    if not scenarios:
        raise FileNotFoundError(
            f"No valid scenarios found. Each scenario folder must contain "
            f"part_a_intro.txt, part_b_facts.txt, part_c_request.txt in {scenarios_dir}"
        )
    return scenarios

def strip_section4_examples(msg: str) -> str:
    """
    Some models try to be 'helpful' and include a sample answer in Section 4.
    This function removes any quoted sample text that appears after Section 4 starts.
    """
    marker = "[SECTION 4:"
    idx = msg.find(marker)
    if idx == -1:
        return msg

    before = msg[:idx]
    after = msg[idx:]

    # Remove anything in quotes in the 'after' part (common way models provide examples)
    after = re.sub(r'“.*?”', '', after, flags=re.DOTALL)
    after = re.sub(r'".*?"', '', after, flags=re.DOTALL)

    # Also remove lines that look like an example answer (start with common sentence stems)
    # (kept conservative; just strips obvious answer-like lines)
    bad_starts = (
        "I understand", "Thank you", "Thanks", "I’m sorry", "I'm sorry", "I can hear",
        "It sounds like", "What you’re describing", "What you're describing"
    )
    cleaned_lines = []
    for line in after.splitlines():
        if line.strip().startswith(bad_starts):
            continue
        cleaned_lines.append(line)
    after = "\n".join(cleaned_lines)

    return before + after
