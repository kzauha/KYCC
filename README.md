# KYCC — AI-Driven Supply Chain Credit Scoring

**Know Your Customer's Customer (KYCC)** is an intelligent credit scoring platform that predicts the financial risk of companies in a supply chain.

> 🧠 **Core Philosophy:** "The Scorecard is King, Artificial Intelligence is the Advisor."

Unlike black-box AI models that deny loans without explanation, KYCC uses an **Expert Scorecard** (fully transparent rules) as the Source of Truth. Our AI watches in the background, learning from data day and night, and proposes *improvements* to the scorecard only when it finds a better way to predict risk.

---

## 🚀 How It Works (The "Student & Teacher" Model)

Imagine a classroom where a wise Professor (The Expert Scorecard) grades students. A brilliant Student (The AI) sits in the back, watching.

1.  **The Professor (Expert Scorecard V1.0)** makes the initial decisions based on years of banking experience.
    *   *Rule:* "If a company is young (< 2 years), deduct points."
2.  **The Student (ML Model)** studies thousands of these decisions and compares them to what *actually happened* (did the borrower pay back?).
3.  **The Insight:** The Student notices: "Wait, young companies *with high transaction volume* actually pay back 99% of the time."
4.  **The Refinement:** The Student raises its hand. "Professor, we should update the rule."
5.  **The New Standard (Scorecard V1.1):** The Professor accepts the advice. Now, young companies with high volume get a *higher* score.

This loop repeats forever, making the system smarter every day while staying 100% explainable.

---

## 📖 The "Urban Retailers" Journey (Beginner Example)

Let's follow one client, **Urban Retailers Ltd.**, through the entire pipeline to see how this works in practice.

### Client Profile: Urban Retailers Ltd.
*   **Company Age:** 2 years (Young)
*   **Activity:** 50 transactions/month (Very High!)
*   **Network:** Only 1 supplier (Risky concentration)

### Step 1: Ingestion (The "Raw Data")
The system pulls data from the supply chain network.
*   It sees: "Urban Retailers created 2 years ago."
*   It sees: "50 invoices paid last month."
*   **Status:** Just raw numbers in a database.

### Step 2: Label Generation (The "Teacher's Guess")
We need to train our AI. But we don't have 5 years of history yet. So, we ask the **Expert Scorecard (V1.0)** to grade them.
*   **Rules (V1.0):**
    *   Young Business? (-20 points)
    *   Small Network? (-10 points)
    *   High Activity? (+10 points)
*   **Result:** Score **550 (Fair)**. The system labels them as "Safe" but barely.

### Step 3: AI Training (The "Student's Insight")
The AI looks at Urban Retailers and 10,000 other companies. It spots a pattern the Expert missed.
*   **Observation:** "Every company with >40 txns/month paid back their loan, even if they were young."
*   **Conclusion:** "Transaction Volume is a **much stronger** predictor of safety than Company Age."

### Step 4: Refinement (The "Upgrade")
The pipeline runs a **Refinement Step**.
*   The AI proposes increasing the weight of `transaction_count` from **10** to **30**.
*   The system checks: "Does this improve accuracy?" **YES > 2% improvement.**
*   **Action:** A new **Scorecard V1.1** is created and activated.

### Step 5: Final Scoring (The "Decision")
Now, Urban Retailers applies for a loan. They are scored using the **NEW V1.1 Scorecard**.
*   **Calculation (V1.1):**
    *   Young Business? (-20 points)
    *   Small Network? (-10 points)
    *   High Activity? (**+30 points** - *Updated!*)
*   **Final Score:** **610 (Good)**.
*   **Outcome:** **APPROVED**. The system correctly identified that their high activity compensated for their age.

---

## 🏗️ Technical Architecture

The entire process is automated by a data pipeline built on **Dagster**.

### The Stack
*   **Orchestrator:** [Dagster](https://dagster.io/) (Manages the flow of data)
*   **Database:** [PostgreSQL](https://www.postgresql.org/) (Stores profiles, scores, and versions)
*   **Backend:** [FastAPI](https://fastapi.tiangolo.com/) (Serves the credit scores to apps)
*   **Frontend:** [React](https://react.dev/) (Visualizes the supply chain)

### The Pipeline Steps (Dagster Assets)

1.  `ingest_synthetic_batch` - Loads data.
2.  `features_all` - Calculates metrics (Age, Volume, Network Size).
3.  `generate_scorecard_labels` - **Critical:** Uses the *current* scorecard to create training labels.
4.  `validate_labels` - Ensures data quality (no missing values).
5.  `train_model_asset` - Trains a Logistic Regression model to mimic/improve the scorecard.
6.  `refine_scorecard` - **The Magic:** Extracts ML weights and updates the Scorecard Version if quality gates pass.
7.  `score_batch` - Scores the customers using the *newest* active scorecard.

---

## ⚡ Quick Start

Want to run this yourself?

### 1. Start the System
```bash
# Start Database, Dagster, and API
docker compose up -d
```

### 2. Run the Pipeline
Open Dagster UI at `http://localhost:3000` and launch the `training_pipeline`.
OR run manually:
```bash
docker exec -it kycc-dagster-1 bash
python scripts/run_full_pipeline.py
```

### 3. See the Results
Check the API at `http://localhost:8000/docs` or query the database:
```sql
-- See the scoreboard history
SELECT version, status, ml_auc FROM scorecard_versions;

-- See the decisions
SELECT party_id, final_score, decision FROM score_requests;
```
