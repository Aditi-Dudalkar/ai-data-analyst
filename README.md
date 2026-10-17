# AI-Powered Data Analysis Agent

An end-to-end AI system that enables natural-language data analysis over tabular datasets (CSV).

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
│   └── datasets/
│       ├── manager.py         # Dataset storage, retrieval, and lifecycle management
│       ├── profiler.py        # Column-level and dataset-level profiling engine
│       ├── schemas.py         # Pydantic models for profiles and metadata
│       └── validator.py       # CSV structure and security validation
│
├── data/
│   └── sample/
│       └── sales.csv          # Sample sales dataset for testing and demonstration
│
└── tests/
    ├── test_manager.py        # Unit tests for DatasetManager and DatasetValidator
    └── test_profiler.py       # Unit tests for DatasetProfiler
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
pytest tests/ -v
```

---

## Python Usage Example

```python
from pathlib import Path
from app.datasets.manager import DatasetManager

# Initialize manager
manager = DatasetManager(upload_dir=Path("data/uploads"))

# Save and profile a dataset
sales_path = Path("data/sample/sales.csv")
metadata, profile = manager.save_dataset(
    filename="sales.csv",
    content=sales_path
)

print(f"Dataset ID: {metadata.dataset_id}")
print(f"Rows: {profile.row_count}, Columns: {profile.column_count}")

# Generate LLM context schema representation
print(profile.to_llm_context_str())
```
