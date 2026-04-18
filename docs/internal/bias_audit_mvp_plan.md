# Bias Audit Framework — Full MVP Plan
### An agentic audit framework for ML datasets combining statistical analysis with LLM-based interpretation

---

## Project Overview

### What this system does

Most bias detection tools treat bias as a statistical property of a dataset in isolation. This system treats bias as **contextual** — a pattern is only a problem if it impacts the specific task the model is being trained for. A class imbalance that is harmless for one task can be catastrophic for another.

The system takes two inputs:
1. A dataset (CSV or tabular file)
2. A plain-English description of the ML task (e.g. "predict whether a loan applicant will default")

It then:
- Runs a deterministic statistical audit on the dataset (Layer 1)
- Passes those results and the task description to an LLM-based agent pipeline (Layer 2)
- Generates a structured PDF/markdown report with ranked issues, visualizations, and mitigation code (Layer 3)

### Why it matters

Bias in ML datasets causes real harm — biased hiring models, biased loan approval systems, biased recidivism predictions. The problem is well-known. The tooling to audit for it in a task-aware, actionable way is not.

This system fills that gap by combining the audibility of statistical analysis with the reasoning power of LLMs to explain *what the bias means* and *how to fix it* — not just that it exists.

### Core design principles

- **Task-aware**: every finding is evaluated relative to the user's specific ML task
- **Severity-ranked**: issues are scored and ranked, not dumped as a flat list
- **Auditable**: Layer 1 is fully deterministic — the statistical foundation can always be independently verified
- **Transparent about limitations**: the system includes explicit "human review recommended" notices; the interpretation layer can be wrong
- **Reproducible**: every report includes the exact parameters and methods used

---

## Tech Stack

| Component | Technology |
|---|---|
| Backend API | Python + FastAPI |
| Statistical analysis | Pandas, SciPy, scikit-learn |
| Agent pipeline | LangGraph |
| LLM | OpenAI GPT-4o or Groq (Llama 3) |
| Frontend | Streamlit (MVP), Next.js (future) |
| Deployment | Hugging Face Spaces |
| Report generation | WeasyPrint or ReportLab |
| Visualizations | Matplotlib, Seaborn |

---

## System Architecture

```
User uploads CSV + writes task description
              │
              ▼
┌─────────────────────────────────────┐
│         Layer 1 — Statistical        │
│         Analysis (Python)            │
│                                      │
│  • Class distribution & imbalance    │
│  • Missing value patterns by group   │
│  • Sensitive attribute correlations  │
│  • Subgroup label distributions      │
│  • Demographic representation gaps   │
│  • Severity scoring                  │
│                                      │
│  Output: structured JSON             │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│       Layer 2 — Agent Pipeline       │
│       (LangGraph + LLM)              │
│                                      │
│  parse → analyze → interpret         │
│       → recommend → report           │
│                                      │
│  Input: Layer 1 JSON + task desc     │
│  • Which issues matter for this task?│
│  • What downstream harm is likely?   │
│  • What mitigations should be used?  │
│  • Code snippets for each fix        │
│                                      │
│  Output: structured interpretation   │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│       Layer 3 — Report               │
│                                      │
│  • Executive summary                 │
│  • Ranked issues by severity         │
│  • Visualizations                    │
│  • Mitigation code                   │
│  • Human review notice               │
│  • Reproducibility details           │
│                                      │
│  Output: PDF or markdown file        │
└─────────────────────────────────────┘
```

---

## Project Folder Structure

```
bias-audit-framework/
│
├── backend/
│   ├── main.py                    # FastAPI app entry point
│   ├── routers/
│   │   └── audit.py               # /upload and /analyze endpoints
│   ├── layer1/
│   │   ├── __init__.py
│   │   ├── class_distribution.py  # Class imbalance analysis
│   │   ├── missing_values.py      # Missing value patterns by group
│   │   ├── correlations.py        # Sensitive attribute correlations
│   │   ├── subgroup_analysis.py   # Subgroup label distributions
│   │   └── severity_scorer.py     # Scoring and ranking issues
│   ├── layer2/
│   │   ├── __init__.py
│   │   ├── agent.py               # LangGraph pipeline definition
│   │   ├── nodes/
│   │   │   ├── parse.py
│   │   │   ├── analyze.py
│   │   │   ├── interpret.py       # Core task-aware reasoning node
│   │   │   ├── recommend.py       # Mitigation strategies + code
│   │   │   └── report.py
│   │   └── prompts/
│   │       ├── interpret_prompt.py
│   │       └── recommend_prompt.py
│   ├── layer3/
│   │   ├── report_generator.py    # PDF/markdown output
│   │   └── visualizations.py     # Charts and plots
│   └── utils/
│       ├── schema.py              # Pydantic models / JSON schema
│       └── config.py             # API keys, thresholds, settings
│
├── frontend/
│   └── app.py                    # Streamlit UI
│
├── evaluation/
│   ├── datasets/                 # Links or loaders for COMPAS, Adult, CelebA
│   ├── run_eval.py               # Evaluation runner
│   └── results/                  # Saved evaluation outputs
│
├── tests/
│   ├── test_layer1.py
│   └── test_layer2.py
│
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Evaluation Datasets

Three well-understood datasets with documented biases are used to validate the system:

### COMPAS (Correctional Offender Management Profiling for Alternative Sanctions)
- **Task**: Predict likelihood of recidivism (re-offending)
- **Known bias**: Racial disparity — Black defendants were nearly twice as likely to be falsely flagged as high-risk compared to white defendants
- **What the system should catch**: Racial imbalance in label distribution, high correlation between race and predicted risk score, differential false positive rates across groups

### Adult Income Dataset (UCI)
- **Task**: Predict whether income exceeds $50,000/year
- **Known biases**: Gender gap (women significantly underrepresented in the >$50k class), racial representation gaps
- **What the system should catch**: Class imbalance within gender subgroups, demographic parity gap, strong correlation between sex/race and income label

### CelebA (Large-Scale CelebFaces Attributes Dataset)
- **Task**: Classify facial attributes (attractiveness, hair color, etc.)
- **Known biases**: Demographic imbalance, spurious correlations between protected attributes and target labels (e.g. "attractive" correlated with gender)
- **What the system should catch**: Representation gap across demographic groups, attribute-label correlations, skewed subgroup distributions

---

## Severity Scoring System

Each detected issue is assigned a severity score on three dimensions:

| Dimension | Description |
|---|---|
| Statistical magnitude | How large is the gap/imbalance numerically? |
| Task relevance | How directly does this issue affect the specific task? |
| Harm potential | What real-world harm could result from this bias in deployment? |

**Severity levels:**

- **High** — Issue is statistically significant, directly relevant to the task, and poses clear downstream harm risk. Requires mitigation before training.
- **Medium** — Issue is present and task-relevant but may not cause severe harm depending on deployment context. Mitigation recommended.
- **Low** — Issue is statistically detectable but likely to have limited impact on the specific task. Note for awareness.

---

---

# Week 1 — Build the Statistical Analysis Layer (Layer 1)

**Dates:** April 4 – 10
**Goal:** A fully working deterministic statistical auditing engine that accepts a CSV file and returns a structured JSON report containing bias metrics, detected issues, and severity scores. No LLM involved.

---

## What to build this week

Layer 1 is the foundation of the entire system. It must be:
- Deterministic: same input always produces same output
- Auditable: every metric computed with an explicit, known formula
- Schema-compliant: output is a strict JSON structure consumed by Layer 2
- Fast: should analyze a dataset with 100k rows in under 10 seconds

---

## Day-by-Day Breakdown

### Day 1 (Friday Apr 4) — Project setup + API skeleton

**Tasks:**
1. Create the project folder structure as defined above
2. Initialize a Python virtual environment, write `requirements.txt`
   ```
   fastapi
   uvicorn
   pandas
   scipy
   scikit-learn
   numpy
   python-multipart
   pydantic
   ```
3. Build a minimal FastAPI app in `main.py` with:
   - `POST /upload` — accepts a CSV file, returns column names and row count
   - `GET /health` — basic health check endpoint
4. Write a Pydantic schema for the audit output JSON (define it before building the analysis so the structure is locked in)
5. Test with a sample CSV using `curl` or Postman

**Output schema to define today:**
```json
{
  "dataset_info": {
    "rows": 48842,
    "columns": 14,
    "target_column": "income",
    "sensitive_columns": ["sex", "race"]
  },
  "issues": [
    {
      "issue_id": "class_imbalance_income",
      "type": "class_imbalance",
      "description": "Target column 'income' has imbalance ratio of 3.2:1",
      "affected_column": "income",
      "severity": "high",
      "metrics": {
        "majority_class": "<=50K",
        "minority_class": ">50K",
        "imbalance_ratio": 3.2
      }
    }
  ],
  "summary": {
    "total_issues": 5,
    "high_severity": 2,
    "medium_severity": 2,
    "low_severity": 1
  }
}
```

---

### Day 2 (Saturday Apr 5) — Class distribution + imbalance detection

**File:** `layer1/class_distribution.py`

**What to implement:**
- Accept: DataFrame + target column name
- Compute: value counts, percentage breakdown, imbalance ratio (count of majority class / count of minority class)
- Flag as issue if:
  - Binary classification: imbalance ratio > 1.5 → medium; > 3.0 → high
  - Multiclass: any class with < 10% representation → medium; < 5% → high
- Return: structured dict ready to be appended to the issues list

**Key metrics:**
```python
imbalance_ratio = majority_count / minority_count
gini_impurity = 1 - sum(p**2 for p in proportions)
```

**Test:** Load the Adult Income dataset, verify it catches the ~3.2:1 imbalance between `<=50K` and `>50K` classes.

---

### Day 3 (Sunday Apr 6) — Missing value analysis by group

**File:** `layer1/missing_values.py`

**What to implement:**
- For each sensitive column (e.g. sex, race), compute: missingness rate per group in every other column
- Detect differential missingness: if group A has 2% missing in column X and group B has 15% missing, that's a bias risk
- Flag as issue if missingness rate difference between any two groups exceeds threshold (default: 5 percentage points)

**Why it matters for bias:**
Differential missing data is a hidden form of bias. If the system is trained on records where one group's data is systematically incomplete, the model will have worse performance for that group — even if class distribution looks balanced.

**Test:** Manually introduce missing values in a dummy dataset at different rates for different groups, verify detection.

---

### Day 4 (Monday Apr 7) — Sensitive attribute correlations

**File:** `layer1/correlations.py`

**What to implement:**
- Measure correlation between each sensitive attribute and the target label
- For categorical–categorical: Cramér's V
- For binary categorical–continuous: point-biserial correlation
- For continuous–continuous: Pearson or Spearman
- Flag as issue if Cramér's V or |r| > 0.1 → medium; > 0.3 → high

**Why it matters:**
If a sensitive attribute is strongly correlated with the target label, the model can use it (or proxies for it) to make predictions — even if the sensitive attribute is not explicitly used as a feature.

**Formula for Cramér's V:**
```
V = sqrt(chi2 / (n * (min(r,c) - 1)))
```
where chi2 is the chi-squared statistic, n is sample size, r and c are number of rows/columns in the contingency table.

---

### Day 5 (Tuesday Apr 8) — Subgroup label distributions + demographic parity

**File:** `layer1/subgroup_analysis.py`

**What to implement:**
- For each sensitive column and each subgroup within it, compute: positive label rate (what fraction of that group has the positive target class)
- Compute: demographic parity gap = max positive rate across groups − min positive rate across groups
- Flag as issue if demographic parity gap > 0.05 → medium; > 0.15 → high

**Example output:**
```
sex=Male:   positive label rate = 30.4%
sex=Female: positive label rate = 11.4%
Demographic parity gap = 19.0% → HIGH severity
```

---

### Day 6 (Wednesday Apr 9) — Severity scoring + full pipeline wiring

**File:** `layer1/severity_scorer.py` + update `routers/audit.py`

**What to implement:**
- Severity scorer: takes raw metric values, applies thresholds, returns severity level + justification string
- Wire all Layer 1 modules into a single function: `run_layer1_audit(df, target_col, sensitive_cols) -> dict`
- Update the `/analyze` endpoint to call this function and return the full JSON

**Severity threshold config** (make these configurable in `config.py`):
```python
SEVERITY_THRESHOLDS = {
    "imbalance_ratio": {"medium": 1.5, "high": 3.0},
    "cramers_v": {"medium": 0.1, "high": 0.3},
    "demographic_parity_gap": {"medium": 0.05, "high": 0.15},
    "differential_missingness": {"medium": 0.05, "high": 0.15}
}
```

---

### Day 7 (Thursday Apr 10) — Testing + smoke test on Adult Income

**Tasks:**
1. Write unit tests in `tests/test_layer1.py` for each module
2. Download the Adult Income dataset from UCI
3. Run the full Layer 1 audit on it. Expected to catch:
   - Class imbalance (~3.2:1)
   - Gender demographic parity gap (~19%)
   - Racial demographic parity gap
   - Correlation between sex and income label
4. Manually verify that the JSON output is correct and complete
5. Fix any bugs, ensure the schema is clean

**End of week checkpoint:** POST a CSV to `/analyze` → receive a valid, complete JSON audit report with all detected issues and severity scores.

---

## Week 1 Deliverable

A working `POST /analyze` endpoint that accepts any tabular CSV and returns a structured JSON bias audit report. Validated against the Adult Income dataset.

---

---

# Week 2 — Build the Agent Interpretation Pipeline (Layer 2)

**Dates:** April 11 – 17
**Goal:** An LLM-based agentic pipeline built with LangGraph that takes Layer 1's JSON output + the user's task description and produces task-aware bias interpretation, downstream impact reasoning, and mitigation recommendations with implementation code.

---

## What to build this week

Layer 2 is what differentiates this system from every other bias tool. It does not just report metrics — it explains what those metrics mean for the specific ML task the user is building.

The pipeline is structured as a LangGraph state machine with five nodes:

```
parse → analyze → interpret → recommend → report
```

Each node receives the current state and adds its output to it before passing to the next node.

---

## The State Object

Define this as a TypedDict that flows through all nodes:

```python
class AuditState(TypedDict):
    raw_json: dict               # Layer 1 output
    task_description: str        # User's task description
    parsed_issues: list          # Issues parsed from raw_json
    task_context: dict           # Structured task understanding
    interpretations: list        # Per-issue task-aware explanations
    mitigations: list            # Per-issue mitigation strategies + code
    clarifying_questions: list   # Optional: questions for the user
    needs_clarification: bool    # Whether to ask questions
    final_report: dict           # Assembled output for Layer 3
```

---

## Day-by-Day Breakdown

### Day 1 (Friday Apr 11) — Add task input to API + LangGraph scaffold

**Tasks:**
1. Update the `/analyze` endpoint to accept both a file and a `task_description` string
2. Install LangGraph: `pip install langgraph langchain langchain-openai`
3. Set up API key handling in `config.py` using environment variables
4. Create `layer2/agent.py` with the state graph definition — define all five nodes as placeholder functions that just pass state through
5. Wire the graph: `parse → analyze → interpret → recommend → report`
6. Add a conditional edge after `analyze`: if clarification is needed, route to a `clarify` node before `interpret`

**Skeleton for the graph:**
```python
from langgraph.graph import StateGraph, END

workflow = StateGraph(AuditState)
workflow.add_node("parse", parse_node)
workflow.add_node("analyze", analyze_node)
workflow.add_node("interpret", interpret_node)
workflow.add_node("recommend", recommend_node)
workflow.add_node("report", report_node)

workflow.set_entry_point("parse")
workflow.add_edge("parse", "analyze")
workflow.add_conditional_edges("analyze", check_clarity, {
    "needs_clarification": "clarify",
    "ready": "interpret"
})
workflow.add_edge("interpret", "recommend")
workflow.add_edge("recommend", "report")
workflow.add_edge("report", END)
```

---

### Day 2 (Saturday Apr 12) — Parse node + Analyze node

**Parse node** (`layer2/nodes/parse.py`):
- Takes the raw Layer 1 JSON
- Extracts: list of issues sorted by severity, target column, sensitive columns, dataset size
- Structures this into a clean `parsed_issues` list for downstream nodes
- No LLM call — pure Python

**Analyze node** (`layer2/nodes/analyze.py`):
- LLM call #1: task understanding
- Prompt the LLM to extract from the task description:
  - Task type (binary classification / multiclass / regression)
  - What the positive class represents
  - Who is likely affected by model decisions
  - What a false positive and false negative mean in this context
  - How sensitive/high-stakes this task is
- Output: `task_context` dict
- **Prompt example:**
  ```
  Task description: "predict whether a loan applicant will default"

  Extract the following and return as JSON:
  - task_type
  - positive_class_meaning
  - affected_population
  - false_positive_consequence
  - false_negative_consequence
  - stakes_level (low / medium / high)
  ```

---

### Day 3 (Sunday Apr 13) — Interpret node (most important node)

**File:** `layer2/nodes/interpret.py`

This is the core of the system. This node explains, for each detected issue, why it matters specifically for the user's task.

**What the prompt needs to accomplish:**
For each issue in `parsed_issues`, given the `task_context`, produce:
- Why this statistical pattern is problematic for this specific task
- Which subgroup(s) are at risk
- What the likely downstream model behavior will be (e.g. "the model will have higher false positive rates for X group")
- Severity assessment in the context of the task (may differ from the statistical severity)

**Prompt template (in `layer2/prompts/interpret_prompt.py`):**
```
You are an ML bias auditor. You have been given:

1. A statistical audit report of a dataset
2. A description of the ML task this dataset will be used for

Your job is to interpret each statistical issue in the context of the task.

Task context:
{task_context}

Statistical issue:
{issue}

For this issue, provide:
1. A plain-English explanation of why this specific statistical pattern is harmful for this specific task
2. Which group(s) are most at risk and how
3. What the likely impact on model behavior will be if this is not addressed
4. Whether the task-level severity is higher, lower, or equal to the statistical severity and why

Be specific. Ground your reasoning in the task context. Avoid generic statements about bias.
```

**Critical note:** Spend time on this prompt. Iterate it against the Adult Income dataset with the task "predict income > $50k" and verify it produces reasoning that is specific and accurate — not generic LLM boilerplate.

---

### Day 4 (Monday Apr 14) — Recommend node

**File:** `layer2/nodes/recommend.py`

For each interpreted issue, generate ranked mitigation strategies with implementation code.

**Categories of mitigations to cover:**
1. **Resampling** — oversample minority class, undersample majority class, SMOTE
2. **Reweighting** — assign sample weights to balance group representation
3. **Data collection** — recommend collecting more data for underrepresented groups
4. **Feature engineering** — remove proxy features that encode sensitive attributes
5. **Algorithmic** — fairness-aware algorithms (e.g. adversarial debiasing, calibrated equal odds)
6. **Post-processing** — threshold adjustment per group

For each mitigation, provide:
- When to use it (pros/cons given the task context)
- A working Python code snippet
- Estimated difficulty (easy / medium / hard)
- Tradeoffs with model performance

**Example mitigation code snippet (for class imbalance):**
```python
from imblearn.over_sampling import SMOTE

smote = SMOTE(random_state=42)
X_resampled, y_resampled = smote.fit_resample(X_train, y_train)

print(f"Original class distribution: {Counter(y_train)}")
print(f"Resampled class distribution: {Counter(y_resampled)}")
```

---

### Day 5 (Tuesday Apr 15) — Clarifying questions logic

**What to implement:**
- In the `analyze` node, after extracting `task_context`, check if the task description is ambiguous
- Ambiguity criteria:
  - Task type cannot be determined
  - Sensitive columns are not identifiable from context
  - Stakes level is unclear
- If ambiguous: set `needs_clarification = True`, populate `clarifying_questions` with 1–2 targeted questions
- For MVP: surface these questions in the Streamlit UI and let the user respond before continuing
- Keep this simple — the goal is to ask one clarifying question max, not build a full multi-turn chat

---

### Day 6 (Wednesday Apr 16) — Report node + agent wiring

**File:** `layer2/nodes/report.py`

- Assembles all node outputs into a single structured `final_report` dict
- This dict is what Layer 3 will consume to generate the PDF
- Structure:
  ```json
  {
    "task_description": "...",
    "task_context": {...},
    "issues": [
      {
        "statistical": {...},
        "interpretation": "...",
        "severity_task_adjusted": "high",
        "mitigations": [...]
      }
    ],
    "summary": "...",
    "disclaimer": "This report was generated with LLM assistance. Human review is recommended before making decisions based on these findings."
  }
  ```

Update `/analyze` endpoint to run Layer 1 → Layer 2 in sequence and return the `final_report`.

---

### Day 7 (Thursday Apr 17) — Basic Streamlit UI + end-to-end test

**File:** `frontend/app.py`

Build a minimal but functional Streamlit interface:
- File uploader for CSV
- Text input for task description
- Dropdowns to specify: target column, sensitive columns
- "Run Audit" button
- Display: spinner while running, then show the issues as expandable cards
- Show severity badges (high/medium/low) next to each issue
- Show interpretation and mitigation per issue

This does not need to be polished this week — functional is the goal.

**End-to-end test:**
1. Upload the Adult Income dataset
2. Task: "Predict whether a person earns more than $50,000 per year based on census data"
3. Target: `income`, Sensitive: `sex`, `race`
4. Verify the full pipeline runs and produces sensible output
5. Check that the interpret node produces specific, task-grounded reasoning (not generic)

**End of week checkpoint:** Full pipeline working end-to-end in the browser. CSV + task description → Layer 1 → Layer 2 → structured output displayed in Streamlit.

---

## Week 2 Deliverable

End-to-end working system in the browser. User uploads a dataset, describes their task, and receives a task-aware bias audit with mitigation recommendations.

---

---

# Week 3 — Report Generation + Deployment (Layer 3)

**Dates:** April 18 – 24
**Goal:** A downloadable, professional-quality PDF/markdown report and a live public deployment on Hugging Face Spaces.

---

## What to build this week

Layer 3 takes the structured `final_report` dict from Layer 2 and produces a human-readable document that can be downloaded and shared. The system is also deployed publicly this week — that's the milestone that makes it real and shareable.

---

## Day-by-Day Breakdown

### Day 1 (Friday Apr 18) — Report template design

**File:** `layer3/report_generator.py`

Define the report structure before writing any code:

```
1. Cover page
   - Dataset name
   - Task description
   - Date of audit
   - System version

2. Executive summary
   - 2–3 sentences: what was found, overall risk level
   - Summary table: N issues found, X high severity, Y medium, Z low

3. Dataset overview
   - Row/column count
   - Target column and class distribution chart
   - Sensitive columns identified

4. Issues (one section per issue, ranked high → medium → low)
   For each issue:
   - Issue title + severity badge
   - Statistical finding (what the numbers show)
   - Task-aware interpretation (what it means for this task)
   - Affected groups
   - Visualizations
   - Mitigation strategies (ranked by ease/effectiveness)
   - Implementation code

5. Disclaimer
   - "This report was generated with LLM-assisted interpretation."
   - "Statistical findings are deterministic and reproducible."
   - "Interpretations and recommendations should be reviewed by a qualified ML practitioner."
   - "Human review is strongly recommended before making deployment decisions."

6. Reproducibility
   - Layer 1 parameters used
   - LLM model used
   - Severity thresholds applied
   - Timestamp and dataset hash
```

---

### Day 2 (Saturday Apr 19) — Visualizations

**File:** `layer3/visualizations.py`

Build chart-generating functions that produce matplotlib figures to be embedded in the report:

1. **Class distribution bar chart** — count of each target class, colored by severity
2. **Demographic parity chart** — grouped bar chart showing positive label rate per subgroup per sensitive attribute
3. **Correlation heatmap** — Cramér's V between all sensitive attributes and the target label
4. **Missing value chart** — heatmap showing missingness rates across groups
5. **Severity summary chart** — horizontal bar chart of all issues sorted by severity

All charts should:
- Use a clean, minimal style (`plt.style.use('seaborn-v0_8-whitegrid')`)
- Have clear axis labels and titles
- Be saved as PNG to a temp directory, then embedded in the report
- Work in a headless environment (no display, use `matplotlib.use('Agg')`)

---

### Day 3 (Sunday Apr 20) — PDF generation

**Choice:** Use WeasyPrint (HTML → PDF) rather than ReportLab — it's much easier to style and produces cleaner output.

**Approach:**
1. Build an HTML template for the report using Jinja2
2. Render the template with the `final_report` data and chart image paths
3. Run WeasyPrint to convert HTML → PDF
4. Return the PDF as a download in the FastAPI response

**Install:**
```
pip install weasyprint jinja2
```

**Alternative (simpler):** If WeasyPrint causes environment issues (it can be finicky), use pandoc to convert a markdown file to PDF. Test WeasyPrint first.

---

### Day 4 (Monday Apr 21) — Polish the Streamlit UI

Make the Streamlit app feel like a real product:

1. **Progress indicator:** Show which step is running (uploading → running statistical analysis → running agent → generating report) with a progress bar
2. **Results display:** Show issues as expandable cards with severity color coding
3. **Download button:** `st.download_button` for the generated PDF
4. **Column selector:** Let the user visually select which columns are sensitive from a dropdown populated by the uploaded CSV
5. **Error handling:** Show friendly error messages if the file is malformed or the API key is missing
6. **"Human review recommended" banner:** Always show this prominently at the top of results

---

### Day 5 (Tuesday Apr 22) — Dockerize the application

Create a `Dockerfile` for deployment:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpango-1.0-0 libpangoft2-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["streamlit", "run", "frontend/app.py", "--server.port=7860", "--server.address=0.0.0.0"]
```

Note: The system dependencies (libpango etc.) are needed for WeasyPrint.

Test the Docker build locally before pushing.

---

### Day 6 (Wednesday Apr 23) — Deploy to Hugging Face Spaces

1. Create a new Hugging Face Space (type: Docker or Streamlit)
2. Add API keys via HF Spaces secrets (Settings → Variables and secrets)
3. Push the repository
4. Test the live deployment with a real dataset upload
5. Verify PDF download works end-to-end
6. Note the public URL — this is your shareable demo link

**HF Spaces `README.md` header** (required for Spaces):
```yaml
---
title: Bias Audit Framework
emoji: 🔍
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
---
```

---

### Day 7 (Thursday Apr 24) — Integration testing + fixes

1. Test the full pipeline on at least 3 different datasets (Adult Income, a synthetic dataset, one of your own)
2. Test edge cases: very small datasets, datasets with no sensitive columns detected, missing target column
3. Test PDF download on different browsers
4. Fix any deployment bugs
5. Confirm the live URL works for a fresh user with no context

**End of week checkpoint:** Public URL is live. Anyone can go to the Hugging Face Space, upload a CSV, describe their task, and download a PDF audit report.

---

## Week 3 Deliverable

Live public deployment on Hugging Face Spaces. Working PDF report download. The system is demo-ready.

---

---

# Week 4 — Evaluation Suite + Documentation

**Dates:** April 25 – 30
**Goal:** Prove the system works against known biased datasets. Write comprehensive documentation. Make the project shareable as a portfolio piece or research contribution.

---

## What to build this week

This week is about validating and documenting. The system runs — now prove it works correctly, know where it fails, and explain it clearly.

---

## Day-by-Day Breakdown

### Day 1 (Friday Apr 25) — Evaluation framework design

**File:** `evaluation/run_eval.py`

Define what "working correctly" means for this system:

**Layer 1 evaluation criteria:**
- Does it detect the known biases in each dataset? (recall of known issues)
- Does it produce false alarms on balanced synthetic datasets? (precision)
- Are severity scores consistent and calibrated correctly?

**Layer 2 evaluation criteria (harder to automate):**
- Does the interpretation correctly identify which group is at risk?
- Is the reasoning specific to the task or generic?
- Are the mitigations appropriate for the issue and task type?

**Evaluation output:** For each dataset, produce:
- List of expected issues (ground truth, manually defined)
- List of issues detected by Layer 1
- Recall: what fraction of expected issues were caught?
- Manual scores for Layer 2 interpretation quality (1–5 scale, scored by you)

---

### Day 2 (Saturday Apr 26) — COMPAS evaluation

**Setup:**
- Download COMPAS dataset (available via ProPublica's GitHub)
- Task description: "Predict whether a defendant will re-offend within two years (recidivism prediction)"
- Target column: `two_year_recid`
- Sensitive columns: `race`, `sex`

**Expected findings Layer 1 should catch:**
1. Racial demographic parity gap (Black defendants have significantly higher positive label rate)
2. Correlation between race and recidivism label
3. Class distribution within race subgroups

**Expected Layer 2 interpretation:**
- Should explain that in a recidivism prediction task, false positives (predicting someone will re-offend when they won't) result in harsher sentencing or denial of parole
- Should identify that the racial disparity means Black defendants are more likely to receive unjustly harsh treatment
- Should recommend reweighting by race, fairness-aware training, or post-processing threshold adjustment

**Document:** What was caught, what was missed, quality of interpretation (with quotes from the actual output).

---

### Day 3 (Sunday Apr 27) — Adult Income evaluation

**Setup:**
- Download from UCI Machine Learning Repository
- Task: "Predict whether a person's annual income exceeds $50,000 based on census features"
- Target: `income`, Sensitive: `sex`, `race`, `age`

**Expected findings:**
1. Class imbalance (~3.2:1)
2. Gender demographic parity gap (~19 percentage points)
3. Racial demographic parity gap
4. Correlation between sex and income label (Cramér's V ~0.22)
5. Age as a proxy — correlation between age and income

**Document results** in the same format as COMPAS evaluation.

---

### Day 4 (Monday Apr 28) — CelebA evaluation

CelebA is larger and image-based — you won't upload the raw images, but you can use the attribute annotations CSV (which is tabular and available separately).

**Setup:**
- Download `list_attr_celeba.txt` (attribute annotations for 200k faces)
- Task: "Predict whether a face is 'attractive' based on facial attribute annotations"
- Target: `Attractive`, Sensitive: `Male` (gender attribute in dataset)

**Expected findings:**
1. Gender imbalance in "Attractive" label
2. Spurious correlations between gender and multiple target attributes
3. Representation gaps

**Note in documentation:** CelebA evaluation is inherently limited because the "ground truth" labels in CelebA are themselves biased human annotations — mention this as a limitation of the evaluation.

---

### Day 5 (Tuesday Apr 29) — Limitations documentation

**Write a clear, honest limitations section** for the README and the report template:

1. **Interpretation accuracy:** The LLM interpretation layer can produce plausible-sounding but incorrect reasoning. It does not have domain knowledge about every ML task. Human review is mandatory.

2. **Sensitive column detection:** Currently requires the user to specify sensitive columns. Automated detection of sensitive columns (e.g. identifying that "zip code" is a proxy for race) is not implemented.

3. **Intersectionality:** The current implementation analyzes sensitive attributes independently. It does not compute intersectional bias (e.g. Black women vs. white women vs. Black men). This is a known gap.

4. **Text and image data:** Layer 1 focuses on tabular data. Text distribution skews and image-level demographic bias are partially addressed but not fully implemented in the MVP.

5. **Mitigation effectiveness:** The system recommends mitigations but does not measure their effectiveness. It cannot tell you how much a resampling strategy will improve fairness in practice.

6. **Proxy variables:** The system detects correlation between explicitly sensitive columns and the target. It does not systematically audit for proxy variables (other columns that are correlated with sensitive attributes).

---

### Day 6 (Wednesday Apr 30 — morning) — README and documentation

Write a comprehensive `README.md`:

```markdown
# Bias Audit Framework

An agentic audit framework for ML datasets combining statistical analysis
with LLM-based interpretation.

## What it does
## Architecture
## Quick start (local)
## Usage
## How the severity scores work
## Evaluation results (summary table: COMPAS, Adult, CelebA)
## Known limitations
## Tech stack
## Reproducibility
## License
```

Include:
- Screenshot of the Streamlit UI
- Example audit output (Adult Income, task: predict income)
- Summary table of evaluation results
- Architecture diagram (even a simple ASCII one)

---

### Day 7 (Wednesday Apr 30 — afternoon) — Final polish + retrospective

1. Fix any remaining bugs found during evaluation
2. Add the live demo link prominently to the README
3. Review: does every report include the "human review recommended" disclaimer? Is it prominent, not buried?
4. Write a short project retrospective note: what worked, what didn't, what you'd do differently
5. Tag a `v0.1.0` release on GitHub

---

## Week 4 Deliverable

Evaluation report with results on 3 known-biased datasets. Comprehensive README. Polished public demo. GitHub repository ready to share.

---

---

# Summary Table

| Week | Theme | Key deliverable |
|---|---|---|
| 1 (Apr 4–10) | Statistical analysis layer | POST /analyze returns JSON bias audit for any CSV |
| 2 (Apr 11–17) | Agent interpretation pipeline | Full pipeline: CSV + task → bias audit in browser |
| 3 (Apr 18–24) | Reports + deployment | Live HF Spaces URL + downloadable PDF report |
| 4 (Apr 25–30) | Evaluation + documentation | Results on COMPAS/Adult/CelebA + shareable README |

---

# Key Risks and Mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| LangGraph complexity slows Week 2 | Medium | Start with a simple sequential chain, add graph complexity after core nodes work |
| WeasyPrint environment issues | Medium | Fall back to pandoc markdown → PDF if needed |
| LLM interpretation is too generic | High | Invest time in prompt engineering on Day 3 of Week 2; evaluate early against Adult Income |
| HF Spaces deployment issues | Low | Test Docker locally before pushing; have a Streamlit Cloud fallback |
| CelebA dataset size | Medium | Use only the attribute annotations CSV, not raw images |

---

# One-Line Reminder

**This is not just detecting bias — it explains what the bias means for a specific ML task and how to fix it.**

---

*MVP plan version 1.0 — generated April 2026*
