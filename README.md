# 🎓 Examinator AI

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-37814A?style=for-the-badge&logo=celery&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)

An advanced EdTech platform equipped with a **Hybrid Grading Core (HGC)**. The system evaluates students' open-ended and mathematical answers using a combination of deterministic mathematical engines, semantic vector search, and Large Language Models (LLMs).

## 🚀 Key Features

*   **Hybrid Grading Core (HGC):** A multi-layer evaluation system:
    1.  **Mathematical Accuracy:** Uses `SymPy` to parse and compare LaTeX formulas.
    2.  **Semantic Search:** Uses `pgvector` and `sentence-transformers` for embedding similarity.
    3.  **Thesis Matcher:** Validates the presence of key required points.
    4.  **Semantic Arbitrage (LLM):** Uses local LLMs (via LM Studio) for final classification.
*   **Automated Content Generation:** Teachers upload DOCX/TXT lectures. The system uses RAG to chunk the text and automatically generates test questions with reference answers and key theses.
*   **Real-time Exam Interfaces:** Offers both a traditional academic view and a modern "Chat Mode" for sequential testing with optimistic UI updates.
*   **Teacher & Admin Dashboard:** Real-time analytics, grade distributions, concept mastery heatmaps, and a manual review queue for low-confidence AI grades.
*   **Appeals System:** Human-in-the-loop mechanism allowing students to challenge AI grades.

## 🛠 Tech Stack

*   **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0 (Async), PostgreSQL + pgvector, Alembic.
*   **Background Workers:** Celery, Redis (Broker/Backend).
*   **AI/ML:** HuggingFace `sentence-transformers` (multilingual-e5-small), OpenAI API protocol (via LM Studio).
*   **Frontend:** React 18, TypeScript, Zustand (State), Tailwind CSS, TanStack Query (Data fetching), KaTeX (Math rendering).
*   **Storage:** S3-compatible object storage (MinIO).

## ⚙️ Quick Start

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/da007/examinator-ai.git
    cd examinator-ai
    ```
2.  **Configure Environment:**
    Copy `.env.example` to `.env` in the `backend/` folder and fill in the required keys (Postgres, Redis, S3, LM Studio URL).
3.  **Run Backend (Docker):**
    ```bash
    cd backend
    docker-compose up -d --build
    ```
4.  **Run Frontend:**
    ```bash
    cd frontend
    npm install
    npm run dev
    ```

## 🧠 Architecture Highlights

*   **Multi-tenancy:** Data isolation via `org_id` for institutions.
*   **Optimistic Locking:** Exam auto-saves use versioning to prevent race conditions.
*   **Resilient Processing:** Celery tasks with dead-letter queues and retry logic for LLM generation failures.

---
*Created by [da007](https://github.com/da007)*
