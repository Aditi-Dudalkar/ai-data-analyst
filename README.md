# AI-Powered Data Analysis Agent

An end-to-end AI system that enables natural-language data analysis over tabular datasets (CSV).

---

## Milestone 1: CSV Upload & Dataset Profiler

Milestone 1 implements the core deterministic data layer:
- **CSV Validation**: Validates file extension, size boundaries, and structural integrity (detecting empty files, missing headers, and malformed CSVs).
- **Dataset Manager**: Securely stores uploaded CSV datasets, creates unique IDs (`ds_...`), persists metadata registries, and manages dataset retrieval.
- **Dataset Profiler**: Extracts comprehensive dataset and column-level profiling metrics:
  - Dataset level: row count, column count, duplicate rows count, missing cells count.
  - Column level: simplified data type inference (`integer`, `float`, `string`, `boolean`, `datetime`), null counts & percentages, unique value counts, and sample values.
  - Numerical statistics: mean, median, min, max, and standard deviation.
  - Categorical statistics: frequency distributions of top values.
  - Context generation: formats concise schema representation (`to_llm_context_str()`) ready for LLM prompt context in future milestones.

---

## Milestone 2: Structured Analysis Plan & Manual Planning

Milestone 2 establishes the formal contract between questions, profiles, and execution engines:
- **Structured Analysis Plan Schema**: Pydantic models for `AnalysisPlan`, `Metric`, `FilterCondition`, `SortSpec`, and `VisualizationSpec` matching Section 7 of `DESIGN.md`.
- **Fluent Plan Builder (`AnalysisPlanBuilder`)**: Programmatic API to construct and validate analytical plans.
- **Manual Planner (`ManualPlanner`)**: Question-to-plan resolution for canonical benchmark questions without an LLM.
- **Unit Tests**: Full schema validation, constraints testing, JSON serialization/deserialization, and canonical question resolution.

---

## Project Structure

```text
ai-data-analyst/
├── DESIGN.md                  # Comprehensive architectural design document
├── README.md                  # Project overview and setup instructions
├── requirements.txt           # Python dependencies
├── .env.example               # Environment configuration template
│
├── app/
│   ├── core/
│   │   ├── config.py          # Storage and threshold settings
│   │   └── exceptions.py      # Custom domain exceptions
│   ├── datasets/
│   │   ├── manager.py         # Dataset storage, retrieval, and lifecycle management
│   │   ├── profiler.py        # Column-level and dataset-level profiling engine
│   │   ├── schemas.py         # Pydantic models for profiles and metadata
│   │   └── validator.py       # CSV structure and security validation
│   └── agent/
│       ├── schemas.py         # Structured analysis plan models & enums
│       ├── plan_builder.py    # Fluent builder API for AnalysisPlan
│       └── manual_planner.py  # Question-to-plan manual generator
│
├── data/
│   └── sample/
│       └── sales.csv          # Sample sales dataset for testing and demonstration
│
└── tests/
    ├── test_manager.py        # Unit tests for DatasetManager and DatasetValidator
    ├── test_profiler.py       # Unit tests for DatasetProfiler
    └── test_analysis_plan.py  # Unit tests for AnalysisPlan and ManualPlanner
```

---

## Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env` to customize settings:
```bash
cp .env.example .env
```

### 3. Run Unit Tests
```bash
python -m pytest tests/ -v
```

---

## Python Usage Examples

### Milestone 1: Load and Profile a Dataset
```python
from pathlib import Path
from app.datasets.manager import DatasetManager

manager = DatasetManager(upload_dir=Path("data/uploads"))
metadata, profile = manager.save_dataset(
    filename="sales.csv",
    content=Path("data/sample/sales.csv")
)

print(f"Dataset ID: {metadata.dataset_id}")
print(f"Rows: {profile.row_count}, Columns: {profile.column_count}")
print(profile.to_llm_context_str())
```

### Milestone 2: Generate an Analysis Plan Manually
```python
from app.agent.manual_planner import ManualPlanner

planner = ManualPlanner()
plan = planner.generate_plan("Which region generated the highest revenue?")

print(plan.to_json())
```
