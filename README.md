\# BIFlow — Automating the BI pipeline with a multi-agent architecture



\*\*From raw files to an explained BI dashboard, automatically.\*\*

BIFlow takes any dataset (CSV, TSV, Excel, Parquet, JSON — one or several tables) and delivers, with no code to write and no human validation:

a cleaned and tested \*\*star-schema data warehouse\*\*, a \*\*catalog of KPIs\*\*, \*\*verified insights\*\*, an \*\*interactive dashboard\*\*, and an \*\*explainability chat\*\* that answers \*"why did BIFlow do that?"\*.



| | |

|---|---|

| \*\*Module\*\* | Advanced Data Science Project — ESPRIT |

| \*\*Team\*\* | Nexora — \*\*Chiheb Mejri\*\* \& \*\*Molka Jerbi\*\* |

| \*\*Repository\*\* | https://github.com/molkajerbi/BIFlow-Nexora-team |

| \*\*LLM\*\* | Qwen 2.5 7B Instruct, \*\*run locally\*\* (no external API, no API key) |

| \*\*Stack\*\* | Python 3.11 · pandas · scikit-learn · DuckDB · LangGraph · sentence-transformers · Ollama · FastAPI · Next.js 15 / React 19 |



\---



\## Table of contents

1\. \[Problem statement](#1-problem-statement)

2\. \[Approach and architecture](#2-approach-and-architecture)

3\. \[The notebook, step by step (parts 1 to 3)](#3-the-notebook-step-by-step)

4\. \[Repository organization](#4-repository-organization)

5\. \[Requirements](#5-requirements)

6\. \[Installation](#6-installation)

7\. \[Execution](#7-execution)

8\. \[Outputs](#8-outputs)

9\. \[Reproducibility](#9-reproducibility)

10\. \[Results](#10-results)

11\. \[Limitations](#11-limitations)

12\. \[Data, ethics and confidentiality](#12-data-ethics-and-confidentiality)

13\. \[Use of generative AI](#13-use-of-generative-ai)



\---



\## 1. Problem statement



Building a BI dashboard usually takes days of manual work by data engineers and analysts: understanding the files, cleaning

them, designing a data warehouse, choosing and computing KPIs, analysing trends, building the dashboard, and documenting every choice.

Each step is slow, error-prone (wrong joins, double counting, invented values) and hard to audit.



\*\*Goal:\*\* automate this whole chain end to end, for \*any\* dataset, while keeping it \*\*reliable\*\* (every result is tested),

\*\*traceable\*\* (every action is logged) and \*\*explainable\*\* (every decision can be justified in plain language).



\*\*Main challenges addressed\*\*

\- \*\*Genericity\*\*: no line of code is written for a specific dataset; structure, quality rules and KPIs are inferred or learned from the data.

\- \*\*LLM reliability\*\*: a small local LLM can hallucinate; every LLM decision is checked by a deterministic supervisor.

\- \*\*Correctness of BI numbers\*\*: avoiding the double-counting trap (fan-out), reconciling every amount with the source.

\- \*\*Auditability\*\*: a tamper-evident audit log, row-level lineage and a decision ledger.



\---



\## 2. Approach and architecture



BIFlow is a \*\*multi-agent system\*\*. Each agent combines deterministic tools (statistics, SQL, rules) with a local LLM, following one principle:



> \*\*The LLM decides, the code verifies, everything is traced.\*\*

> An LLM decision is only applied if a supervisor validates it (closed catalog of actions, consistency checks, anti-hallucination check on numbers).

> A rejected decision is sent back to the LLM with the reason so it can correct itself; if it still fails, a cautious deterministic fallback takes over.

> The pipeline never depends entirely on the LLM.



```mermaid

flowchart LR

&#x20;   A\[Raw files] --> P1

&#x20;   subgraph P1\[Part 1 · Data Preparation Agent]

&#x20;       S1\[1 Contract \& ingestion<br/>BRONZE] --> S2\[2 Profiler tools] --> S3\[3 Domain + Profiler agents<br/>LLM] --> S4\[4 Quality \& Cleaning agent<br/>SILVER] --> S5\[5 ETL agent<br/>GOLD star schema]

&#x20;   end

&#x20;   P1 --> P2

&#x20;   subgraph P2\[Part 2 · BI \& Insight Agent]

&#x20;       S7\[7 KPI knowledge base<br/>RAG] --> S8\[8 KPI agent] --> S9\[9 Analyst agent] --> S10\[10 Dashboard agent]

&#x20;   end

&#x20;   P2 --> P3

&#x20;   subgraph P3\[Part 3 · Explainability \& orchestration]

&#x20;       S12\[12 XAI agent<br/>chat] --> S13\[13 Global orchestrator]

&#x20;   end

```



\- \*\*Medallion architecture\*\*: \*bronze\* (raw, immutable) → \*silver\* (typed and cleaned) → \*gold\* (star schema, KPIs).

\- \*\*Orchestration\*\*: each part is a \*\*LangGraph state graph\*\* (steps 6 and 11), chained by a global graph (step 13).

&#x20; After each node a conditional edge decides: continue, or stop cleanly (`blocked`, `failed`).

\- \*\*Quality gates\*\*: a step only runs if the previous one passed its checkpoint (e.g. a blocking quality issue forbids the ETL).



\---



\## 3. The notebook step by step



The full pipeline is a single notebook of 13 steps. Every step ends with a \*\*checkpoint\*\* (raw data unchanged, audit chain intact, step-specific tests).



\### Part 1 · Data Preparation Agent (steps 1–6)



| Step | Agent / content | Main techniques |

|---|---|---|

| \*\*1\*\* Foundations \& ingestion | Frozen configuration; \*\*tamper-evident audit log\*\*; \*\*automatic data contract inference\*\* (encoding, separator, semantic types, date formats, grain, relationships, fact/dimension roles, confidence score); traceable ingestion into the \*\*bronze\*\* zone with row-level \*\*lineage\*\* | SHA-256 hash chain, inclusion dependencies, smallest unique key (1–3 columns), immutable store with fingerprints |

| \*\*2\*\* Data Profiler tools | 5 audited, deterministic tools: column profile, grain \& duplicates, relationships (orphans, undeclared links), \*\*explained missing values\*\*, \*\*anomaly detection\*\*; health map and findings | `@audited` decorator, closed tool registry, Cramér's V, Jaccard, IQR, MAD robust z-score, Isolation Forest |

| \*\*3\*\* LLM agents | Local LLM; \*\*Domain \& Contract Agent\*\* (understands the business domain, reviews the contract through a closed catalog of corrections); \*\*Profiler Agent\*\*: deterministic screening → \*\*LLM-driven investigation (tool calling)\*\* → findings classified by \*\*DAMA dimension\*\* → \*\*business interpretation\*\* of each finding | ReAct-like loop, supervisor validation, feedback \& retries, anti-hallucination check on numbers, fallback, autonomy rate |

| \*\*4\*\* Data Quality \& Cleaning Agent | Typing (\*\*silver\*\* zone); treatment policy for missing, impossible and extreme values; \*\*DAMA rule engine\*\* (rules generated from the contract + \*\*business rules learned from the data\*\*, within and across tables); scores before cleaning; candidate fixes \*\*simulated in a sandbox\*\*; LLM decides propose/dismiss; \*\*automatic risk policy\*\*; controlled application (each changed cell logged before → after); re-validation, row flags and quality report | Group median (η²), Cramér's V, log-scale IQR per group, rule mining (≥ 99 % / ≥ 95 % support), sandbox simulation, side-effect check by hashing, quality gate `blocked / ready\_with\_warnings / ready` |

| \*\*5\*\* ETL Agent | Pre-check and SQL warehouse; staging with date keys, generated calendar and \*\*time indicators discovered from the data\*\* (durations, overruns); \*\*automatic star-schema design\*\* (aggregated/flattened dimensions, "unknown" members, dimensions extracted by functional dependencies, \*\*separate aggregates against double counting\*\*); LLM chooses the build order; every table is tested; \*\*fan-out demonstration\*\* | DuckDB (SQLite fallback), Kimball conventions, topological sort, tests: unique grain, row count, lineage, \*\*sum reconciliation\*\*, foreign keys |

| \*\*6\*\* Sub-orchestrator | The agents become nodes of a LangGraph graph; single entry point `run\_data\_preparation()` | LangGraph (built-in mini engine as fallback), shared state, conditional edges |



\### Part 2 · BI \& Insight Agent (steps 7–11)



| Step | Agent / content | Main techniques |

|---|---|---|

| \*\*7\*\* Bridge \& knowledge base | What part 1 hands over; semantic inventory of what can be computed; \*\*KPI knowledge base\*\* per business sector and its validation; \*\*semantic search (RAG)\*\*; feasibility of each KPI on this dataset; business sector (search proposes, LLM decides, code verifies) | Embeddings `intfloat/multilingual-e5-small` + TF-IDF (lexical fallback) |

| \*\*8\*\* BI Semantic \& KPI Agent | \*\*Compiler from a closed KPI language to SQL\*\* (and to pandas for an independent second computation); KPI-to-column binding (automatic when obvious, LLM when ambiguous); computation and tests of each KPI; KPIs proposed by the agent; KPI catalog | Closed DSL, double computation SQL / pandas, plausibility bounds by unit |

| \*\*9\*\* BI Analyst Agent | Reliable monthly series; statistical rules to detect changes; breakdown by segment; LLM-driven investigation; \*\*verified insights\*\* (every number and every direction of change is checked against the facts) | Statistical tests, segment analysis, anti-hallucination checks |

| \*\*10\*\* Dashboard Generator Agent | Dashboard candidates; layout chosen by the LLM, best practices enforced by the supervisor; self-contained `dashboard.html` | HTML/JS template, offline rendering |

| \*\*11\*\* Sub-orchestrator | `run\_bi\_insight()`: steps registry, graph, restart from a step, \*\*reproducibility diagnostic\*\* | LangGraph |



\### Part 3 · Explainability and global orchestration (steps 12–13)



| Step | Agent / content | Main techniques |

|---|---|---|

| \*\*12\*\* XAI Agent | \*\*Decision ledger\*\* (every decision of steps 1–11 with its reason, evidence, author and audit link); system rules read from the code; explanation search engine; answers built by the rules, rephrased by the LLM, verified by the code; \*\*chat\*\*; evaluation (coverage, retrievability, faithfulness) | Traceability, local and global explanations, counterfactuals ("what would have changed the decision") |

| \*\*13\*\* Global orchestrator | `run\_biflow()`: input check → Data Preparation → BI \& Insight → XAI → delivery, in one command; comparison with the cell-by-cell run; final checkpoint; XAI chat on the full run | Global LangGraph graph; explainability is always built, even after a stop |



\---



\## 4. Repository organization



| Branch | Content |

|---|---|

| `deploiement-web` \*(default)\* | \*\*Deployed application\*\*: FastAPI back end + Next.js web application (current version) |

| `notebook-complet-bi-xai` | \*\*Final notebook, full pipeline (parts 1, 2 and 3)\*\*: `biflowenglish.ipynb` |

| `data-preparation-agent-notebook` | Data Preparation Agent notebook (part 1) |

| `deployment` | First deployment, Streamlit interface |



\### Structure of the deployed application (`deploiement-web`)



```text

BIFlow-Nexora-team/

├── notebooks/

│   └── biflowenglisch.ipynb    # the notebook executed by the application (source of truth)

├── biflow/                     # pipeline engine

│   ├── \_\_main\_\_.py             # command line: extract | check | run

│   ├── extract.py              # notebook → biflow/steps/ (one file per cell, never modified by hand)

│   ├── engine.py               # runs the notebook cells in order = global orchestrator (step 13)

│   ├── llm.py                  # OllamaLLM client (local LLM, no API key)

│   ├── jobs.py                 # analyses: creation, launch, progress, results

│   ├── xai\_chat.py             # explainability chat on a finished analysis

│   └── steps/                  # generated cells + manifest.json

├── api/                        # FastAPI back end

│   ├── main.py                 # REST API (accounts, analyses, results, dashboard, chat, notifications)

│   ├── auth.py                 # local accounts (SQLite, PBKDF2 hashing), sessions, optional Google sign-in

│   └── notify.py               # notifications (in app, desktop, optional email)

├── web/                        # Next.js 15 / React 19 front end

│   ├── app/                    # pages: home, sign in, sign up, analyses, new analysis, profile

│   ├── components/             # interface components (charts, chat, notifications…)

│   └── lib/                    # API calls, formatting, session

├── app.py                      # Streamlit interface (alternative)

├── lancer.ps1                  # Windows: starts the API and the web application

├── requirements.txt            # Python dependencies

├── .env.exemple                # optional settings (Google sign-in, email) — copy to .env

└── .gitignore                  # data/, jobs/, .env, accounts database, node\_modules… are not versioned

```



Generated at run time and \*\*not versioned\*\*: `data/` (input datasets), `jobs/` (one folder per analysis), `biflow\_cache/`, `biflow\_accounts.sqlite3`, `.env`.



\---



\## 5. Requirements



| | Notebook (Kaggle) | Deployed application (local) |

|---|---|---|

| Python | Kaggle environment | \*\*3.11\*\* |

| GPU | \*\*GPU T4 × 2\*\* for Qwen 2.5 7B (one T4: use the 3B model) | Not required (Ollama runs on CPU, GPU used if available) |

| LLM | `Qwen/Qwen2.5-7B-Instruct` via `transformers` | \[Ollama](https://ollama.com) with `qwen2.5:7b` (≈ 4.7 GB) |

| Node.js | — | \*\*20 LTS\*\* (≥ 18.18) for the web application |

| RAM | Kaggle default | 16 GB recommended (8 GB minimum with `qwen2.5:3b`) |

| Internet | Needed once (model download) | Needed once (dependencies, model); analyses run offline |



\---



\## 6. Installation



\### 6.1 Notebook (Kaggle)

1\. Import the notebook `biflowenglish.ipynb` (branch `notebook-complet-bi-xai`) into Kaggle.

2\. \*\*Settings → Accelerator → GPU T4 × 2\*\*, and \*\*Internet: on\*\*.

3\. \*\*Add Input → attach exactly ONE dataset\*\* (the notebook finds it automatically and stops if there are zero or several).

&#x20;  `torch`, `transformers`, `pandas`, `scikit-learn` are preinstalled on Kaggle; `duckdb`, `langgraph` and `sentence-transformers` are imported or installed by the notebook itself.



> Locally (with an NVIDIA GPU): put the dataset in `./data/` or set the environment variable `BIFLOW\_DATA\_DIR`, then

> `pip install -r requirements.txt torch transformers accelerate jupyter`.



\### 6.2 Deployed application (Windows, PowerShell)



```powershell

\# 1. Get the code

git clone https://github.com/molkajerbi/BIFlow-Nexora-team.git

cd BIFlow-Nexora-team

\# (deploiement-web is the default branch: no checkout needed)



\# 2. Python environment

py -3.11 -m venv .venv

.\\.venv\\Scripts\\Activate.ps1

pip install -r requirements.txt



\# 3. Local LLM (install Ollama first from https://ollama.com/download)

ollama pull qwen2.5:7b

python -m biflow check          # expected: "OK : qwen2.5:7b disponible …"



\# 4. Web application

cd web

npm install

cd ..

```



macOS / Linux: same steps with `python3.11 -m venv .venv` and `source .venv/bin/activate`.



\### 6.3 Optional settings (`.env`)

Without `.env`, BIFlow works normally (email + password accounts, notifications in the app).

To enable \*\*Google sign-in\*\* or \*\*email notifications\*\*, copy `.env.exemple` to `.env` and fill in the fields

(`BIFLOW\_GOOGLE\_CLIENT\_ID`, `BIFLOW\_SMTP\_\*`). The `.env` file contains private settings and is never committed.



| Variable | Default | Role |

|---|---|---|

| `BIFLOW\_LLM\_MODEL` | `qwen2.5:7b` | Ollama model |

| `OLLAMA\_URL` | `http://localhost:11434` | Ollama address |

| `BIFLOW\_EMBED\_MODEL` | `intfloat/multilingual-e5-small` | Embedding model for the RAG (lexical fallback if unavailable) |

| `BIFLOW\_DATA\_DIR` | — | Notebook only: dataset folder |



\---



\## 7. Execution



\### 7.1 Notebook

\*\*Run All\*\*. Nothing to configure: the dataset is found automatically, the pipeline runs 100 % automatically,

and every step prints its checkpoint (`STEP n PASSED`). The last steps run everything again in one command (`run\_biflow()`)

and open the XAI chat, e.g. `ask("Why was the median used for this column?")`.



\### 7.2 Command line (deployed version)

```powershell

python -m biflow check                              # is Ollama ready?

python -m biflow run data\\my\_dataset                # full pipeline A → Z on a folder containing ONE dataset

python -m biflow run data\\my\_dataset --model qwen2.5:3b

python -m biflow extract                            # re-extract the cells after changing the notebook

```

Results: `jobs/<date>/result.json` and the deliverables folder.



\### 7.3 Web application

Make sure \*\*Ollama is running\*\*, then from the project root:

```powershell

.\\lancer.ps1

```

This opens the API (http://localhost:8000) and the web application (http://localhost:3000).

Or manually, in two terminals:

```powershell

\# terminal 1 — API

.\\.venv\\Scripts\\Activate.ps1

uvicorn api.main:app --port 8000



\# terminal 2 — web application

cd web

npm run dev

```

\*\*Demo flow:\*\* create an account → \*New analysis\* → upload files (or a ZIP) → follow the live progress →

explore the tabs (data preparation, quality before/after, star schema, KPIs, insights, dashboard) → ask questions in the XAI chat →

download the deliverables. A notification is sent when the analysis finishes.



\### 7.4 Streamlit interface (branch `deployment`)

```powershell

streamlit run app.py

```



\---



\## 8. Outputs



Each run writes to its own folder (`biflow\_runs/<RUN\_ID>/` in the notebook, `jobs/<id>/` in the application); a run never overwrites another.



| Path | Content |

|---|---|

| `audit\_log.jsonl` | Tamper-evident audit log (hash chain) of every action and decision |

| `data\_contract.json` | Inferred data contract (types, grain, relationships, roles, confidence) |

| `profiling/` | Tool results, health map, findings, profiling report, Profiler agent trace |

| `quality/` | Typing report, rules before/after, cleaning plan, every changed cell (before → after), removed rows, DAMA scores |

| `warehouse/` | `biflow\_star.duckdb` (star schema), one CSV per table, ETL tests, ETL agent trace, `etl\_manifest.json` |

| `data\_preparation\_output/` | Delivery of part 1 (cleaned data, star schema, reports, manifest) |

| `bi/` | KPI references, KPI catalog and monthly series, analysis, \*\*verified insights\*\*, `dashboard.html` |

| `xai/` | Decision ledger, system rules, XAI evaluation report |

| `biflow\_run\_report.json` | Global run report and manifest of all deliverables |

| `\*.mmd` | Orchestration graphs (Mermaid) |



\---



\## 9. Reproducibility



\- \*\*Fixed seed\*\* (`random\_seed = 42`) and \*\*deterministic LLM decoding\*\* (greedy, `do\_sample=False`).

\- \*\*Frozen configuration\*\* (`@dataclass(frozen=True)`), unique `RUN\_ID` per run, output folders never overwritten.

\- \*\*Integrity checks\*\* at every checkpoint: raw data fingerprint unchanged, audit hash chain verified, row counts explained.

\- \*\*Fingerprints\*\* (SHA-256) of the cleaning plan and of every generated SQL query, recorded in the audit log.

\- \*\*Reproducibility diagnostic\*\* (steps 11.6 and 13.3): the one-command run is compared with the cell-by-cell run.

\- The application \*\*executes the notebook cells themselves\*\* (`biflow/steps/` is generated from the notebook by `python -m biflow extract`):

&#x20; notebook and application cannot drift apart.

\- Dependencies listed in `requirements.txt`.



\---



\## 10. Results



\*\*Main dataset: Olist — Brazilian E-Commerce Public Dataset\*\* (9 related tables: orders, items, payments, reviews, customers,

sellers, products, geolocation, category translation; ≈ 100 000 orders, 2016–2018).

To check genericity and robustness, the deployed application was also tested on \*\*synthetic test datasets\*\* built by the team

with different structures: a single flat table, an Excel workbook, a JSON file, a multi-table retail dataset, a geolocation table,

and "hard" cases (disguised empty values, spelling variants, duplicates, impossible and extreme values, orphan keys).



\- \*\*Generic\*\*: the same code builds the contract, the quality rules, the star schema and the KPIs of each dataset, without any dataset-specific line.

\- \*\*Data quality\*\*: DAMA scores measured before and after cleaning with the \*same\* rules; every change is logged and reversible.

\- \*\*Correct numbers\*\*: every warehouse table passes its tests (unique grain, exact row count, complete lineage, sums reconciled with the source);

&#x20; the fan-out demonstration shows that a naive join overstates amounts while BIFlow's separate aggregates match the ground truth.

\- \*\*Controlled autonomy\*\*: the share of decisions taken by the LLM (autonomy rate), rejected decisions and fallbacks are measured for every agent.

\- \*\*Explainability\*\*: every decision can be explained in the chat with its evidence, author and counterfactual.



Detailed figures, experiments and analysis: see the \*\*technical report\*\*.



\---



\## 11. Limitations



\- \*\*Small local LLM (7B)\*\*: limited reasoning on complex domains; mitigated by supervisors and fallbacks, but some business nuances may be missed.

\- \*\*Performance\*\*: on CPU, a full analysis of a large dataset can take a long time (many LLM calls, e.g. KPI proposals).

\- \*\*Heuristic thresholds\*\* (99 % rule support, 30 % imputation limit, 3 IQR…) are general defaults, not tuned per domain.

\- \*\*Conservative cleaning\*\*: issues without a safe fix (orphan keys, probable duplicate entities) are flagged, not corrected.

\- \*\*Scope\*\*: tabular data only (no free-text analytics, images or streaming data); one dataset per analysis.

\- The web application is a local, single-machine deployment (no multi-user server deployment or admin panel).



\---



\## 12. Data, ethics and confidentiality



\- \*\*Olist dataset\*\*: public dataset published by Olist on Kaggle

&#x20; (https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce), license \*\*CC BY-NC-SA 4.0\*\*

&#x20; (non-commercial use, attribution, share-alike). The data is \*\*anonymized\*\* by the publisher (customers, sellers and orders

&#x20; are identified by hashed IDs; company names in the reviews were replaced).

\- \*\*Synthetic test datasets\*\*: generated by the team; they contain no real personal data.

\- \*\*All processing is local\*\*: the LLM, the embeddings and the database run on the user's machine; no data is sent to an external API.

\- Raw data is never modified (immutable bronze zone); estimated values are flagged; every change is traced.

\- User passwords are hashed (PBKDF2); Google sign-in only confirms the user's identity, no data is shared.



\---



\## 13. Use of generative AI



In accordance with the module rules, we explicitly declare the use of generative AI tools in this project.



\*\*1. Inside the product.\*\* BIFlow uses the open-source LLM \*\*Qwen 2.5 7B Instruct\*\* (Alibaba Cloud, Apache 2.0 license),

run locally, as the decision engine of its agents. Its decisions are always checked by deterministic supervisors (section 2).



\*\*2. During development.\*\* The team used \*\*Claude (Anthropic)\*\* as an AI assistant for:

\- help writing and refactoring parts of the code, in particular the web deployment (FastAPI back end, Next.js interface,

&#x20; notifications, Google sign-in) and the engine that runs the notebook in the application;

\- debugging and testing (error analysis, test scripts, checking the deployment end to end);

\- translating the notebook outputs and the interface into English;

\- documentation (this README, code comments) and help preparing the presentation and the demo voice-over.



The problem framing, the architecture, the methodological choices, the experiments and the validation of the results

were decided, reviewed and checked by the team. Every piece of AI-assisted code was read, executed and tested by the team,

and both members can explain every part of the project.

