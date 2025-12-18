# KYCC - Know Your Customer's Customer

## Overview

KYCC (Know Your Customer's Customer) is an enterprise-grade supply chain credit scoring platform. It models companies (parties), their business relationships, and transaction history to compute creditworthiness scores using a transparent, auditable scorecard model enhanced by machine learning.

### Core Philosophy

**"The Scorecard is King, Artificial Intelligence is the Advisor."**

Unlike black-box AI models that make decisions without explanation, KYCC uses an Expert Scorecard as the source of truth. The scorecard contains human-defined rules based on domain expertise. Machine learning operates in an advisory capacity, analyzing patterns in historical data and proposing improvements to scorecard weights only when it can demonstrate measurable performance gains.

This approach ensures:

- Full transparency and explainability for every credit decision
- Regulatory compliance with credit scoring requirements
- Human oversight of the scoring logic
- Continuous improvement through ML-driven refinement

### What the System Does

1. **Models Supply Chain Entities**: Stores parties (suppliers, manufacturers, distributors, retailers), their relationships, and transaction history
2. **Extracts Features**: Automatically derives meaningful signals from raw data including KYC scores, transaction patterns, and network metrics
3. **Computes Credit Scores**: Applies weighted scorecard rules to produce 300-900 credit scores
4. **Learns and Improves**: ML models train on historical outcomes and propose scorecard refinements
5. **Maintains Auditability**: Logs all scoring requests with full feature snapshots for compliance

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Backend API | FastAPI + Python 3.11 | REST API with automatic OpenAPI documentation |
| Database | PostgreSQL 15 + SQLAlchemy 2.x | Relational storage with ORM |
| Orchestration | Dagster | Data pipeline orchestration and scheduling |
| Validation | Pydantic v2 | Type-safe API schemas |
| Frontend | React + Vite | Interactive web interface |
| Visualization | Recharts, ReactFlow | Score charts and network graphs |

### Technology Rationale

- **FastAPI**: Type hints, async support, automatic OpenAPI documentation, Pydantic integration
- **SQLAlchemy 2.x**: Modern async support, clear ORM relationships, session management
- **PostgreSQL**: Native JSON support for feature snapshots, recursive CTEs for graph traversal, ACID guarantees
- **Dagster**: Asset-based pipelines, built-in observability, backfill support
- **Pydantic v2**: Strict validation, ORM mode for automatic conversion

---

## Key Concepts

### Parties

Parties are the core entities in the supply chain. Each party represents a business entity such as:

- Suppliers
- Manufacturers
- Distributors
- Retailers
- Customers

### Relationships

Relationships model the business connections between parties:

- `supplies_to`: Supplier provides goods to another party
- `manufactures_for`: Manufacturer produces for another party
- `distributes_for`: Distributor handles logistics for another party
- `sells_to`: Retailer sells to end customer

### Transactions

Transactions record financial activity between parties:

- Invoices
- Payments
- Credit notes

### Features

Features are computed numeric values derived from raw data that feed into the scoring model:

- KYC features (verification status, company age)
- Transaction features (volume, regularity, recency)
- Network features (counterparty count, network depth)

### Credit Scores

Credit scores range from 300-900 (similar to FICO) and are computed by applying scorecard weights to extracted features. Scores are categorized into bands:

| Band | Score Range | Interpretation |
|------|-------------|----------------|
| Excellent | 750-900 | Very low risk |
| Good | 650-749 | Low risk |
| Fair | 500-649 | Moderate risk |
| Poor | 300-499 | High risk |

---

## Project Structure

```
KYCC/
├── backend/                    # FastAPI backend
│   ├── app/
│   │   ├── api/               # API route handlers
│   │   ├── adapters/          # Data source adapters
│   │   ├── cache/             # TTL cache implementation
│   │   ├── config/            # Configuration management
│   │   ├── db/                # Database connection and CRUD
│   │   ├── extractors/        # Feature extractors
│   │   ├── models/            # SQLAlchemy models
│   │   ├── rules/             # Business rule evaluation
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── scorecard/         # Scorecard engine
│   │   ├── services/          # Business logic services
│   │   └── validators/        # Data validators
│   ├── dagster_home/          # Dagster pipeline definitions
│   ├── data/                  # Synthetic data files
│   ├── scripts/               # Utility scripts
│   ├── tests/                 # Test suite
│   └── main.py                # FastAPI application entry
├── frontend/                   # React frontend
│   ├── src/
│   │   ├── api/               # API client
│   │   ├── components/        # Reusable components
│   │   └── pages/             # Page components
│   └── package.json
├── docs/                       # Documentation (this site)
├── docker-compose.yml          # Docker orchestration
└── mkdocs.yml                  # Documentation configuration
```

---

## Quick Links

- [Quick Start Guide](getting-started/quickstart.md) - Get up and running in minutes
- [Architecture Overview](architecture/overview.md) - Understand the system design
- [API Reference](api/overview.md) - Complete API documentation
- [ML Pipeline](ml/pipeline.md) - Machine learning workflow
