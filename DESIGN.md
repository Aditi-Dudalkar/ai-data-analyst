# AI-Powered Data Analysis Agent

## 1. Overview

An AI-powered data analysis application that allows users to upload structured datasets such as CSV files and ask questions about the data using natural language.

The system uses an LLM to understand the user's question, generate a structured analysis plan, execute the required analysis using Python/SQL tools, and return evidence-backed insights along with relevant visualizations.

The primary goal is to build an end-to-end AI system rather than a simple LLM wrapper.

---

# 2. Problem Statement

Traditional data analysis requires users to understand SQL, Python, or BI tools to answer questions from datasets.

This application provides a natural-language interface over structured data.

Example:

> "Which product category generated the highest revenue in 2025?"

The system should be able to:

1. Understand the question.
2. Identify the relevant columns.
3. Determine the required analysis.
4. Generate an executable analysis plan.
5. Validate the generated plan.
6. Execute the analysis.
7. Validate the results.
8. Generate a concise explanation.
9. Produce a visualization when appropriate.

The generated answer should be backed by actual computed results rather than allowing the LLM to invent numerical values.

---

# 3. Goals

## Primary Goals

* Upload and analyze CSV datasets.
* Automatically profile uploaded datasets.
* Accept natural-language analytical questions.
* Use an LLM to generate structured analysis plans.
* Execute analysis using controlled Python/SQL tools.
* Generate evidence-backed answers.
* Automatically generate relevant visualizations.
* Expose the system through an API.
* Deploy the application.
* Maintain a clean separation between AI, data, and application layers.

## Secondary Goals

* Support multiple datasets.
* Maintain conversation context.
* Track analysis history.
* Add caching for repeated questions.
* Add basic observability and logging.

---

# 4. Non-Goals for MVP

The first version will NOT attempt to:

* Train a custom LLM.
* Build a general-purpose autonomous agent.
* Support arbitrary Python execution.
* Support every database system.
* Perform advanced ML automatically.
* Replace professional BI platforms.
* Guarantee perfect answers to ambiguous questions.

The MVP will focus on reliable analysis of structured tabular data.

---

# 5. High-Level Architecture

```text
                         ┌─────────────────┐
                         │      User       │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │   Streamlit UI  │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │    FastAPI      │
                         │      API        │
                         └────────┬────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    │             │             │
                    ▼             ▼             ▼
             ┌───────────┐ ┌───────────┐ ┌─────────────┐
             │  Dataset  │ │   Agent   │ │  Analysis   │
             │  Manager  │ │  Service  │ │   Engine    │
             └─────┬─────┘ └─────┬─────┘ └──────┬──────┘
                   │             │               │
                   ▼             ▼               ▼
             ┌───────────┐ ┌───────────┐ ┌─────────────┐
             │ Dataset   │ │    LLM    │ │ DuckDB /    │
             │ Profiler  │ │   Client  │ │   Pandas    │
             └───────────┘ └───────────┘ └─────────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Validation /    │
                         │ Safety Layer    │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Visualization   │
                         │    Engine       │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Final Response  │
                         └─────────────────┘
```

---

# 6. Core Components

## 6.1 Frontend

### Responsibility

Provide the user interface for:

* Dataset upload.
* Dataset preview.
* Dataset statistics.
* Natural-language questions.
* Analysis results.
* Generated charts.
* Conversation history.

### Initial Technology

* Streamlit

The frontend should remain thin. Business logic should not live inside Streamlit.

---

# 6.2 API Layer

### Responsibility

Expose application functionality through REST APIs.

### Technology

* FastAPI

### Initial endpoints

```text
POST   /datasets
GET    /datasets/{dataset_id}
GET    /datasets/{dataset_id}/profile

POST   /analysis
GET    /analysis/{analysis_id}

GET    /health
```

---

# 6.3 Dataset Manager

Responsible for handling uploaded datasets.

### Responsibilities

* Store uploaded files.
* Generate dataset IDs.
* Validate file type.
* Validate file size.
* Load datasets.
* Maintain dataset metadata.

Example metadata:

```json
{
    "dataset_id": "ds_123",
    "filename": "sales.csv",
    "rows": 100000,
    "columns": 12,
    "created_at": "...",
    "storage_path": "..."
}
```

---

# 6.4 Dataset Profiler

Before asking the LLM to analyze a dataset, the system should understand the dataset.

### Profiling information

For every column:

* Name
* Data type
* Null count
* Null percentage
* Unique count
* Sample values

For numerical columns:

* Mean
* Median
* Min
* Max
* Standard deviation

For categorical columns:

* Top values
* Frequency

Dataset-level information:

* Number of rows
* Number of columns
* Duplicate rows
* Missing values

Example:

```text
Dataset: sales.csv

Rows: 100,000
Columns: 8

customer_id    integer
order_date     datetime
product        string
category       string
quantity       integer
price          float
region         string
revenue        float
```

This profile becomes part of the context supplied to the AI system.

---

# 6.5 Agent Service

This is the core AI component.

Its responsibility is to convert:

```text
Natural Language Question
```

into:

```text
Structured Analysis Plan
```

The LLM should NOT directly execute arbitrary Python code.

---

# 7. Analysis Plan

The LLM should produce a structured object.

Example:

```json
{
    "question": "Which region generated the highest revenue?",
    "operation": "aggregation",
    "group_by": ["region"],
    "metrics": [
        {
            "column": "revenue",
            "aggregation": "sum"
        }
    ],
    "sort": {
        "column": "revenue",
        "direction": "desc"
    },
    "limit": 5,
    "visualization": {
        "type": "bar",
        "x": "region",
        "y": "revenue"
    }
}
```

This gives the application a predictable contract between the LLM and the execution engine.

---

# 8. Tool Layer

The agent will have access to a limited set of tools.

Initial tools:

```text
profile_dataset()
get_column_information()
execute_sql()
execute_pandas_analysis()
create_visualization()
```

The LLM decides which tool is required.

Example:

```text
User:
"Show monthly revenue for 2025."

        ↓

LLM

        ↓

execute_sql()

        ↓

Result

        ↓

Visualization

        ↓

Final answer
```

---

# 9. Validation Layer

This is an important part of the project.

The LLM output should never be trusted blindly.

The validation layer checks:

### Schema validation

Does the requested column exist?

```text
"revenue" → exists
"sales_amount" → does not exist
```

### Operation validation

Is the requested aggregation supported?

```text
sum
avg
count
min
max
median
```

### Query validation

For SQL:

* Only SELECT statements allowed.
* No INSERT.
* No UPDATE.
* No DELETE.
* No DROP.
* No ALTER.

### Resource validation

Prevent excessively expensive operations.

Example:

```text
Maximum returned rows: 10,000
Maximum query execution time: 10 seconds
```

---

# 10. Analysis Engine

The analysis engine executes validated analysis plans.

Initial implementation:

```text
DuckDB + Pandas
```

DuckDB is useful because it provides SQL analytics directly over data files/DataFrames without requiring a separate database server.

Example:

```sql
SELECT
    region,
    SUM(revenue) AS total_revenue
FROM dataset
GROUP BY region
ORDER BY total_revenue DESC;
```

The engine returns structured results rather than raw text.

```json
{
    "columns": ["region", "total_revenue"],
    "rows": [
        ["South", 1250000],
        ["West", 1120000],
        ["North", 980000]
    ]
}
```

---

# 11. Insight Generation

The LLM receives the computed results.

Important:

```text
LLM
 ↓
Analysis Plan

Analysis Engine
 ↓
Actual Results

LLM
 ↓
Explanation
```

The LLM should NOT calculate the numerical result itself when the system can calculate it deterministically.

Example final response:

```text
The South region generated the highest revenue at ₹12.5 lakh,
followed by West at ₹11.2 lakh.

The South region contributed approximately 34% of total revenue.
```

The numbers must come from the analysis engine.

---

# 12. Visualization Engine

The visualization engine receives the analysis result and visualization specification.

Initial supported charts:

```text
Bar chart
Line chart
Histogram
Scatter plot
Pie chart
```

Example:

```json
{
    "type": "line",
    "x": "order_date",
    "y": "revenue",
    "aggregation": "sum"
}
```

Technology:

```text
Plotly
```

The visualization engine should generate the chart independently of the LLM.

---

# 13. End-to-End Request Flow

Example question:

> "Which product category had the highest revenue last year?"

### Step 1 — User

Uploads:

```text
sales.csv
```

### Step 2 — Dataset Manager

Stores dataset and creates:

```text
dataset_id = ds_123
```

### Step 3 — Dataset Profiler

Generates:

```text
category → string
revenue → float
order_date → datetime
```

### Step 4 — User asks question

```text
Which product category had the highest revenue last year?
```

### Step 5 — Agent

Receives:

```text
Question
+
Dataset Schema
+
Dataset Profile
```

Generates:

```json
{
    "operation": "aggregation",
    "group_by": ["category"],
    "metrics": [
        {
            "column": "revenue",
            "aggregation": "sum"
        }
    ],
    "filters": [
        {
            "column": "order_date",
            "operator": "year",
            "value": 2025
        }
    ],
    "sort": {
        "column": "revenue",
        "direction": "desc"
    },
    "limit": 1
}
```

### Step 6 — Validation

Verify:

```text
category exists       ✓
revenue exists        ✓
order_date exists     ✓
aggregation allowed   ✓
filter valid          ✓
```

### Step 7 — Analysis Engine

Executes the analysis.

### Step 8 — Result

```text
Electronics → ₹42.5 lakh
Furniture   → ₹31.2 lakh
Clothing    → ₹28.4 lakh
```

### Step 9 — Visualization

Generate a bar chart.

### Step 10 — Insight Generation

LLM receives the actual results and generates the explanation.

### Step 11 — API Response

```json
{
    "answer": "Electronics generated the highest revenue...",
    "data": [...],
    "visualization": {...},
    "analysis_plan": {...}
}
```

---

# 14. Suggested Project Structure

```text
ai-data-analyst/
│
├── README.md
├── DESIGN.md
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
│
├── app/
│   │
│   ├── main.py
│   │
│   ├── api/
│   │   ├── datasets.py
│   │   ├── analysis.py
│   │   └── health.py
│   │
│   ├── agent/
│   │   ├── agent.py
│   │   ├── prompts.py
│   │   ├── schemas.py
│   │   └── tools.py
│   │
│   ├── analysis/
│   │   ├── engine.py
│   │   ├── sql_executor.py
│   │   └── pandas_executor.py
│   │
│   ├── datasets/
│   │   ├── manager.py
│   │   ├── profiler.py
│   │   └── validator.py
│   │
│   ├── visualization/
│   │   └── charts.py
│   │
│   ├── services/
│   │   ├── llm.py
│   │   └── insight_generator.py
│   │
│   └── core/
│       ├── config.py
│       ├── logging.py
│       └── exceptions.py
│
├── frontend/
│   └── streamlit_app.py
│
├── tests/
│   ├── test_profiler.py
│   ├── test_validator.py
│   ├── test_analysis.py
│   └── test_api.py
│
├── data/
│   └── sample/
│
└── docs/
    └── architecture.md
```

---

# 15. Data Flow

```text
CSV
 │
 ▼
Dataset Manager
 │
 ▼
Dataset Profiler
 │
 ▼
Schema + Metadata
 │
 ▼
User Question
 │
 ▼
Agent / LLM
 │
 ▼
Structured Analysis Plan
 │
 ▼
Validation
 │
 ├──── Invalid ────► Retry / Clarification
 │
 ▼
Analysis Engine
 │
 ▼
Computed Results
 │
 ├──────────────► Visualization Engine
 │
 ▼
Insight Generator
 │
 ▼
Final Response
```

---

# 16. Error Handling

The system should gracefully handle:

### Invalid dataset

```text
Unsupported file format
Corrupt CSV
Empty dataset
Missing headers
```

### Invalid question

```text
"Tell me something interesting."
```

The system should request clarification rather than hallucinating an analysis.

### Invalid LLM output

If the generated analysis plan fails schema validation:

```text
LLM
 ↓
Invalid output
 ↓
Retry with validation error
 ↓
LLM
 ↓
Valid output
```

Retry limit:

```text
Maximum 2 retries
```

### Analysis failure

Return a controlled error:

```json
{
    "error": {
        "code": "ANALYSIS_FAILED",
        "message": "Unable to execute the generated analysis."
    }
}
```

---

# 17. Security Considerations

The system executes AI-generated analytical instructions, so security is a core concern.

Initial safeguards:

* Never execute arbitrary Python generated by the LLM.
* Validate all structured outputs.
* Allow only approved SQL operations.
* Restrict query execution time.
* Limit result size.
* Validate uploaded files.
* Never expose environment variables to the LLM.
* Keep API keys server-side.
* Sanitize user-provided input.
* Log tool execution and failures.

---

# 18. Observability

Each analysis request should have a unique ID.

Example:

```text
analysis_id = an_456
```

Log:

```text
analysis_id
dataset_id
user_question
generated_plan
validation_result
execution_time
execution_status
result_size
LLM latency
LLM token usage
errors
```

This will make debugging much easier once the system is deployed.

---

# 19. MVP

The first working version should contain only:

```text
CSV upload
      ↓
Dataset profiling
      ↓
Natural language question
      ↓
LLM
      ↓
Structured analysis plan
      ↓
Validation
      ↓
DuckDB/Pandas execution
      ↓
Result
      ↓
LLM explanation
      ↓
Basic visualization
```

No authentication.

No multi-user support.

No vector database.

No RAG.

No complex agent framework.

No autonomous multi-agent architecture.

---

# 20. Future Extensions

After the MVP is stable:

### V2

* Multiple datasets
* Conversation memory
* Query history
* Better error recovery
* Caching
* More visualization types

### V3

* PostgreSQL/MySQL connections
* Natural-language SQL generation
* Automated EDA
* Anomaly detection
* Statistical hypothesis testing
* Forecasting

### V4

* RAG over business documentation
* Business metric definitions
* Persistent user workspaces
* Authentication
* Role-based access
* Production monitoring
* Evaluation framework

---

# 21. AI Evaluation

The project should eventually have an evaluation dataset containing:

```text
Question
Expected operation
Expected columns
Expected result
Expected visualization
```

Example:

```text
Question:
"What was the average order value by region?"

Expected:
GROUP BY region
AVG(order_value)
```

Evaluation metrics can include:

* Plan validity rate
* Column selection accuracy
* SQL execution success rate
* Answer correctness
* Visualization correctness
* Average latency
* LLM cost per query

This is important because an AI application should be evaluated like a system, not just demonstrated with a few successful examples.

---

# 22. Deployment Architecture

Initial deployment:

```text
                    Internet
                       │
                       ▼
                ┌─────────────┐
                │  Streamlit  │
                └──────┬──────┘
                       │
                       ▼
                ┌─────────────┐
                │   FastAPI   │
                └──────┬──────┘
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
       LLM API      DuckDB       Storage
```

Everything should be containerized using Docker.

---

# 23. Development Strategy

Build vertically rather than creating every folder first.

### Milestone 1

Load CSV and generate dataset profile.

### Milestone 2

Ask a question and manually generate an analysis plan.

### Milestone 3

Connect the LLM and generate the analysis plan automatically.

### Milestone 4

Validate and execute the plan.

### Milestone 5

Generate explanations from actual results.

### Milestone 6

Add visualizations.

### Milestone 7

Expose everything through FastAPI.

### Milestone 8

Add Streamlit UI.

### Milestone 9

Add tests, logging, Docker, and deployment.

### Milestone 10

Create evaluation dataset and benchmark the system.

---

# 24. Design Principles

The project should follow these principles:

1. **LLM proposes; deterministic code executes.**
2. **Never trust generated code blindly.**
3. **Computed results are the source of truth.**
4. **Keep AI logic separate from business logic.**
5. **Prefer simple architectures over unnecessary frameworks.**
6. **Every important component should be testable independently.**
7. **Build the MVP before adding advanced AI features.**
8. **Measure AI quality rather than relying only on demos.**

---

# 25. MVP Success Criteria

The MVP is considered successful when a user can:

1. Upload a CSV.
2. See its profile.
3. Ask a natural-language analytical question.
4. Receive a valid structured analysis plan.
5. Have that plan validated.
6. Execute the analysis against the dataset.
7. Receive the actual computed result.
8. Receive an explanation grounded in that result.
9. Receive an appropriate visualization.
10. Repeat the process with another question.

The system should fail safely when it cannot answer a question instead of inventing an answer.

---

# 26. First Implementation Task

The first implementation should NOT involve an LLM.

Start with:

```text
CSV
 ↓
Pandas
 ↓
Dataset Profiler
 ↓
Structured Dataset Profile
```

Once the deterministic data layer works, add the AI layer on top of it.

This gives us a stable foundation and makes it much easier to debug whether a problem comes from:

```text
Data
   vs
Analysis
   vs
LLM
   vs
Visualization
```

