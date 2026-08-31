# AI-Powered Personalized Learning Path Recommender

This project is a Streamlit-based learning recommendation platform for learners who want a personalized roadmap toward a target role, such as Machine Learning Engineer. It blends profile extraction, structured skill-gap analysis, prerequisite validation, semantic retrieval, recommendation scoring, feasibility checks, adaptive learning, and assessments into one polished demo application.

## Features

- Natural-language learner profile generation
- Deterministic skill-gap and target-role analysis
- Prerequisite-aware learning graph
- Structured resource retrieval and hybrid ranking
- Time feasibility and roadmap generation
- AI-style explanations using structured facts
- Progress tracking and assessments
- Adaptive remediation after weak assessment results
- MongoDB-backed profiles, roadmaps, completion state, assessment results, feedback, and chat history
- Feedback-driven roadmap adjustments for difficulty, hands-on projects, and study time

## Architecture

- Streamlit UI for the learner experience
- Pydantic models for validation
- MongoDB for persistence
- NetworkX for prerequisite graphs
- Chroma style local retrieval fallback via deterministic embeddings
- Plotly for dashboards and progress visualization
- OpenAI integration only when an API key is configured and mock mode is off

## Tech Stack

- Python 3.11+
- Streamlit
- MongoDB
- Pydantic
- ChromaDB
- NetworkX
- Plotly
- python-dotenv
- pytest

## Installation

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment Setup

Create a copy of the example environment file and update values as needed:

```bash
copy .env.example .env
```

Key variables:

```env
LLM_API_KEY=
GROK_API_KEY=
OPENAI_API_KEY=
LLM_BASE_URL=
OPENAI_BASE_URL=
LLM_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
MOCK_MODE=true
MONGODB_URI=mongodb://localhost:27017/
MONGODB_DATABASE=learning_recommender
CHROMA_PATH=./storage/chroma
EMAIL_MODE=console
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USERNAME=
SMTP_PASSWORD=
SMTP_SENDER=
```

To use Grok or another OpenAI-compatible provider, set:

```env
LLM_API_KEY=your_grok_key
LLM_BASE_URL=https://api.x.ai/v1
LLM_MODEL=grok-2-latest
MOCK_MODE=false
```

The app accepts either `LLM_API_KEY`, `GROK_API_KEY`, or `OPENAI_API_KEY`, and it will use `LLM_BASE_URL` or `OPENAI_BASE_URL` when provided.

## Account Recovery

New accounts require an email address. The **Forgot password** tab creates a one-time reset code that expires after 15 minutes.

For free Gmail delivery, enable two-step verification on the sender account, create a Gmail App Password, then set:

```env
EMAIL_MODE=smtp
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USERNAME=your-gmail-address@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_SENDER=your-gmail-address@gmail.com
```

`EMAIL_MODE=console` is intended only for local development: it displays the reset code in the app and must not be used in production. Gmail supports `smtp.gmail.com` on port 465 for SSL or 587 for TLS. [Google Gmail SMTP documentation](https://developers.google.com/workspace/gmail/imap/imap-smtp)

## Running the App

```bash
streamlit run app.py
```

## Mock Mode

The project is designed to run fully in mock mode without any external API credentials. Set:

```env
MOCK_MODE=true
```

This enables deterministic resource retrieval, explanation fallback, and assessment flows.

## Database Setup

Start a local MongoDB server, or use a MongoDB Atlas connection string. Set `MONGODB_URI` and `MONGODB_DATABASE` in `.env`; collections and indexes are created automatically on first app start.

For a local Windows installation, MongoDB must be running before launching the app:

```powershell
Get-Service MongoDB
```

MongoDB Compass is optional: it is a graphical viewer for the data, not the database server.

## Testing

```bash
pytest -q
```

## Example Workflow

1. Enter a natural-language profile such as: "I know basic Python and statistics..."
2. Review the generated profile and target skills.
3. Inspect the skill-gap analysis.
4. Review the ranked recommendations and roadmap.
5. Mark resources completed.
6. Take an assessment.
7. Recalculate gaps and apply adaptive remediation.
8. Use the roadmap feedback controls to request easier, shorter, or more hands-on recommendations.

## Future Improvements

- Add more roles and domains beyond ML Engineer
- Integrate a real vector database and model vendor
- Add collaborative filtering for learner communities
- Expand project and assessment datasets
- Add user authentication and multi-learner support

## Project Structure

```text
.
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── config/
├── data/
├── database/
├── models/
├── services/
├── assessment/
├── dashboard/
├── utils/
├── tests/
├── storage/
└── .gitignore
```
