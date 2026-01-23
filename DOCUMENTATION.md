# PlaySAFE – RAG-based Dialogue Trainer for Safeguarding Officers

PlaySAFE is a dialogue-based training system designed to help safeguarding officers (vertrouwenscontactpersonen) in Dutch sports clubs practice neutral, emotionally aware, and procedurally correct conversations in sensitive situations.

Unlike conventional RAG systems focused on fact retrieval or summarisation, PlaySAFE uses Retrieval-Augmented Generation to support reflective practice, scenario-based learning, and feedback on conversational skills.

## Project Overview

The system simulates structured training dialogues in which the user (a safeguarding officer) responds to fictional but realistic scenarios involving issues related to inter-personal violence.

### Each training interaction follows a three-stage pedagogical flow:

1) Message 1 – Scenario introduction
The model presents the first part of a scenario and instructs the officer to explain confidentiality boundaries only.

2) Message 2 – Scenario development
The model provides reflective feedback on how confidentiality was explained, introduces additional scenario details, and asks the officer to respond supportively and neutrally.

3) Message 3 – Reflection and feedback
The model evaluates the officer’s response in terms of neutrality, emotional attunement, and likely impact on the person involved.

The flow is enforced through prompt design and UI logic, not hardcoded dialogue trees, allowing flexibility for follow-up questions and reflection.

## Data Sources

The system uses two main data types:

1) Scenario files

Fictional safeguarding scenarios, adapted for the sports club context.
Each scenario is split into structured parts (intro, facts, request, optional twist) to support controlled progression.

2) Help / guidance documents

Short, theory-based documents covering topics such as:

- neutrality and impartiality

- confidentiality boundaries

- trauma-informed communication

- conversational boundaries

These documents are indexed and retrieved dynamically to support feedback generation.

All data is fictional or generalised to avoid sensitive personal information.

## Architecture

## Installation

Create a virtual environment (recommended), then install dependencies:

{pip install -r requirements.txt}

Make sure Ollama is installed and running locally with a compatible chat model.

## Running the Application
1) Unzip the data folder
2) In the command prompt activate the virtual environment and navigate to the directory where gui.py is stored.
3) Start the Streamlit interface:

{streamlit run gui.py}

4) The app opens in your browser

5) Quit anytime with Ctrl + C in the terminal

## Design Considerations

- Scenarios are not generated on the fly to ensure consistency and pedagogical control.

- RAG is used only for conversational guidance, not for scenario content.

- The model is instructed never to take the role of the safeguarding officer.

- All feedback is reflective, not prescriptive

## Scientific report produced as the result of this project:
[PLAYSAFE_GROUP_7_260123_202456.pdf](https://github.com/user-attachments/files/24828045/PLAYSAFE_GROUP_7_260123_202456.pdf)

