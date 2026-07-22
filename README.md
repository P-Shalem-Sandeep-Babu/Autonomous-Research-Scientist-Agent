# Autonomous Research Scientist Agent (ARSA)

**Autonomous Research Scientist Agent (ARSA)** is a production-grade, multi-agent AI research assistant platform designed to automate significant portions of the scientific research lifecycle. It coordinates specialized autonomous agents under a central orchestrator engine to transform a simple research topic into a complete research workflow, including code execution, evaluation, manuscript writing, and peer review.

---

## 🌟 Core Research Workflow

```text
Topic Analysis
      ↓
Literature Review (arXiv & Local RAG Uploads)
      ↓
Research Gap Discovery
      ↓
Hypothesis Generation
      ↓
Multi-Perspective Agent Debate (Expert Swarms)
      ↓
Dataset Discovery (Hugging Face Search Queries)
      ↓
Experiment Roadmap Planning
      ↓
Code Generation (Self-Debugging PyTorch Compiler Loop)
      ↓
Sandbox Subprocess Execution (Safe Shell Console execution)
      ↓
Statistical Metrics Evaluation & Baselines Comparison
      ↓
Scientific Manuscript Writing (WYSIWYG LaTeX Dual Panel Editor)
      ↓
Peer Review Simulator (Skeptical, Methodological, Editor Consensus)
      ↓
Automated Correction Revision Loop
      ↓
Cross-Project Global Memory & Knowledge Graph Compilation
```

---

## 🚀 Key Features

*   **Expert Swarm Debates:** Models 4 distinct research personas (Moderator, Neuroscientist, Hardware Optimizer, Statistician) debating clinical margins, GFLOP bounds, and data splits to select the winning hypothesis.
*   **Safe Subprocess Sandbox:** Runs training scripts dynamically under a restricted folder structure, blocking dangerous commands (`rm`, `del`, `mv`, etc.), and features an interactive file explorer and diagnostic terminal in the UI.
*   **Interactive LaTeX PDF Compilation:** Renders paper drafts dynamically using Python `reportlab` inside a split-screen workspace next to an interactive LaTeX editor.
*   **Panel Peer Review Board:** Simulates Skeptical, Methodological, and Editor-in-Chief personas to critique drafts and automatically trigger manuscript revision cycles if the score falls below a threshold.
*   **Chain-of-Thought (CoT) Visualizer:** Records step-by-step agent decisions in the database and streams them in real-time over WebSockets to a tree timeline widget.
*   **Agent-Reach Search Integration:** Integrates the `agent-reach` capability layer to fetch live, zero-API-fee evidence and discussions from GitHub, Reddit, YouTube, and RSS feeds.
*   **Hugging Face Hub Publisher:** Uploads model cards, configs, and training logs directly to simulated repository URLs.

---

## 📂 System Architecture

The project is structured into two main sub-projects:

### 1. Backend (`/backend`)
*   **FastAPI & Uvicorn:** Exposes RESTful endpoints for projects, code updates, reference paper PDF uploads, LaTeX compilation, and Hugging Face publisher.
*   **SQLAlchemy & SQLite:** Persists project stages, literature metadata, hypotheses, debate logs, generated files, and reasoning chains.
*   **WebSockets:** Streams active research manager logs and CoT reasoning steps in real-time.
*   **Specialized Agents (`app/agents/`):** Houses literature, gap, hypothesis, debate, dataset, planner, codegen, execution, evaluation, writer, reviewer, memory, and graph agents.

### 2. Frontend (`/frontend`)
*   **Next.js (App Router) & TypeScript:** Implements the research workspace dashboard and layouts.
*   **Vanilla CSS & Lucide Icons:** Curated sleek dark mode styles, custom timeline components, and widgets.
*   **Interactive Knowledge Graph:** Renders node-edge relationship connections mapping papers, gaps, hypotheses, plans, and files.

---

## ⚙️ Quick Start Setup

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows:
   .\venv\Scripts\activate
   # On macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install npm packages:
   ```bash
   npm install
   ```
3. Launch the Next.js development server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🧪 Running Automated Tests

To verify backend routing, sandbox commands, vector store memory lookups, and revision loops, execute `pytest` with the pythonpath environment set:

```bash
# In the /backend directory
$env:PYTHONPATH="."; .\venv\Scripts\pytest
```
All 12 test cases should pass successfully.
