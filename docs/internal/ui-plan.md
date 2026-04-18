# Streamlit UI Plan

### Frontend for AuditLens — two phases from functional to polished

---

## Context

The backend API is complete through Layer 3. All audit logic, LLM interpretation, and PDF report generation is working and tested. The only missing piece before deployment is a user-facing interface. Without it, the system is only usable by developers hitting endpoints directly.

This document covers two phases:
- **Phase 1** — a functional but minimal Streamlit UI that wires up the full pipeline end-to-end
- **Phase 2** — a polished UI that is good enough to demo publicly and hand to a non-technical user

Deployment to Hugging Face Spaces is **out of scope** for both phases and will be planned separately after Phase 2 is complete.

---

## Existing API Endpoints the UI Will Use

| Endpoint | Used for |
|---|---|
| `POST /upload` | Preview CSV columns and row count immediately after file upload |
| `POST /analyze-task-report-pdf` | Main audit flow — runs all 3 layers, returns base64 PDF |
| `POST /analyze-task-report` | Alternative if PDF fails — returns Markdown report |
| `POST /analyze-task-report-jobs` | Async job submission for large datasets |
| `GET /analyze-task-report-jobs/{job_id}` | Poll async job status |
| `GET /reports/{artifact_id}/download` | Download stored report file |

The clarification flow is handled by the same `/analyze-task-report-pdf` endpoint — when the task description is ambiguous, the API returns `status: needs_clarification` with a list of questions. The UI must handle this response and allow the user to answer before resubmitting.

---

## Phase 1 — Functional UI

**Goal:** full pipeline working in the browser. Functional, not pretty. No polish required.

### File: `frontend/app.py`

This is the only file needed for Phase 1. Keep it in a top-level `frontend/` folder so it is clearly separated from the backend.

### User Flow

```
1. User uploads a CSV file
        ↓
2. App calls POST /upload → gets column names + row count
        ↓
3. User selects: target column, sensitive columns (multiselect)
        ↓
4. User types a task description (free text)
        ↓
5. User clicks "Run Audit"
        ↓
6. App calls POST /analyze-task-report-pdf with spinner
        ↓
   [if needs_clarification]
7a. Show clarifying questions as text inputs
7b. User fills answers and clicks "Submit Answers"
7c. App resubmits with clarification_answers
        ↓
   [if complete]
8. Show results: ranked issues list, interpretations, recommendations
        ↓
9. Show PDF download button (decode base64 → bytes)
```

### Screens / Components

**Step 1 — Upload**
- `st.file_uploader` accepting `.csv` only
- On upload: call `/upload`, display column count and row count as a small preview line
- Show a sample of the dataframe (`st.dataframe`, first 5 rows)

**Step 2 — Configuration**
- `st.selectbox` for target column (populated from /upload response)
- `st.multiselect` for sensitive columns (same list, exclude selected target)
- `st.text_area` for task description with a placeholder like: *"e.g. predict whether a loan applicant will default"*

**Step 3 — Run**
- `st.button("Run Audit")`
- On click: show `st.spinner("Running audit...")`
- Make the POST request to `/analyze-task-report-pdf`

**Step 4a — Clarification (conditional)**
- If `status == "needs_clarification"`: show each question as a labeled `st.text_input`
- Show a `st.button("Submit Answers")`
- Resubmit with `clarification_answers` JSON

**Step 4b — Results**
- Show a success banner: dataset name, row count, issue count
- For each issue in the report: show title, severity badge (high/medium/low), description, and recommendations as plain text
- Show a `st.download_button` for the PDF (decode base64 → raw bytes, mime type `application/pdf`)

### Phase 1 Non-Goals
- No charts rendered inline (PDF already has them)
- No session history
- No sidebar layout
- No styling beyond default Streamlit
- No async job polling (use synchronous endpoint only for now)

---

## Phase 2 — Polished UI

**Goal:** a UI good enough to demo publicly and hand to a non-technical user. Clean, clear, and trustworthy-looking.

### Layout Changes

Move inputs into a **left sidebar** (`st.sidebar`). Main content area is used entirely for results. This is the standard Streamlit pattern for tool UIs and immediately feels more professional.

```
┌─────────────────┬──────────────────────────────────────────┐
│   SIDEBAR       │   MAIN CONTENT                           │
│                 │                                          │
│  Upload CSV     │   [Before run] Welcome / instructions   │
│  Target col     │                                          │
│  Sensitive cols │   [After run]                            │
│  Task desc      │   Summary banner                         │
│  [Run Audit]    │   Issue cards (severity-ranked)          │
│                 │   Charts (inline)                        │
│                 │   Download buttons                       │
└─────────────────┴──────────────────────────────────────────┘
```

### Progress Indicator

Replace the generic spinner with a **step-by-step progress display** during the audit:

```
✓  Dataset loaded (312 rows, 15 columns)
✓  Layer 1 — Statistical analysis complete
⟳  Layer 2 — Interpreting findings for your task...
```

This is achievable with `st.status` (Streamlit 1.28+) or a manual placeholder + rerun approach.

### Issue Cards

Instead of plain text, render each issue as a styled card using `st.container` + `st.columns`:

```
┌──────────────────────────────────────────────────────┐
│  🔴 HIGH   Gender imbalance in target label          │
│  ─────────────────────────────────────────────────── │
│  Why it matters: For loan default prediction, the    │
│  70/30 gender split in positive outcomes creates a   │
│  systematic disadvantage for female applicants...    │
│                                                      │
│  Recommended fix: Apply class reweighting using      │
│  sklearn's compute_class_weight before training.     │
└──────────────────────────────────────────────────────┘
```

Severity colors: red for high, amber for medium, grey for low.

### Inline Charts

The PDF already contains charts as embedded images (generated by `backend/layer3/visualizations.py`). For Phase 2, **also render the charts inline** in the Streamlit app using `st.pyplot`. This means calling the visualization functions directly rather than relying on the PDF.

Charts to render inline:
- Class distribution bar chart (from `visualizations.py`)
- Severity breakdown pie/bar
- Subgroup outcome comparison (if subgroup issues exist)

This requires the Streamlit app to either call the backend layer functions directly (if running in the same process) or expose a separate `/charts` endpoint. Simplest approach: import and call the visualization functions directly since the frontend and backend will run in the same Streamlit process.

### Async Job Support

For large datasets (> 50k rows), the synchronous endpoint will time out in the browser. Add a toggle:

- Small datasets (< 50k rows): use synchronous `/analyze-task-report-pdf`
- Large datasets: use `/analyze-task-report-jobs`, then poll `/analyze-task-report-jobs/{job_id}` with `st.rerun()` on a 3-second interval until `status == "complete"`, then fetch the result

The UI should handle this transparently — detect row count from the `/upload` response and choose the right path automatically.

### Download Buttons

Provide two download options:
- `Download PDF Report` — primary CTA, prominent placement
- `Download Markdown Report` — secondary, for users who want to edit or embed in docs

### Error Handling

Phase 1 errors are silent or raw. Phase 2 should handle:
- Upload failure → "Could not read this file. Make sure it is a valid CSV."
- API timeout → "The audit is taking longer than expected. Try a smaller dataset or use async mode."
- LLM provider error (503) → "Interpretation service unavailable. Check your API key in settings."
- No sensitive columns selected → inline warning before allowing run

### Session State

Use `st.session_state` to persist:
- Uploaded file and column list (so re-running doesn't require re-uploading)
- Last audit results (so navigating away and back doesn't wipe results)
- Clarification answers (so partial answers are not lost on rerun)

---

## File Structure

```
frontend/
└── app.py          # single file for Phase 1, grows in place for Phase 2
```

No extra pages, no multi-file structure needed for MVP. If the app grows beyond ~300 lines, split into helper modules inside `frontend/`.

---

## Dependencies to Add

```
streamlit>=1.28.0
requests           # for calling the FastAPI backend
```

Add to `requirements.txt`. The Streamlit app calls the FastAPI backend over HTTP (`http://localhost:8000`) — do not import backend modules directly in Phase 1. In Phase 2, direct imports of visualization functions are acceptable since both run in the same environment.

---

## Running Locally (Both Phases)

```bash
# Terminal 1 — backend
uvicorn backend.main:app --reload

# Terminal 2 — frontend
streamlit run frontend/app.py
```

---

## Definition of Done

**Phase 1 complete when:**
- User can upload any CSV, configure columns, describe a task, and receive a downloadable PDF audit report in the browser
- Clarification flow works end-to-end (questions shown, answers resubmitted)
- Runs without errors on the Adult Income dataset smoke test case

**Phase 2 complete when:**
- Sidebar layout in place
- Step-by-step progress visible during audit
- Issue cards rendered with severity colors
- At least 2 charts rendered inline
- Error states handled gracefully for the 4 cases above
- Async path works for large CSV files
- Both PDF and Markdown download buttons present
