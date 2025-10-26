# Contributing to BenchmarkOS Chatbot

Thank you for your interest in contributing to BenchmarkOS! This document provides guidelines for organizing code, submitting contributions, and maintaining project quality.

## Table of Contents

- [Getting Started](#getting-started)
- [File Organization Guidelines](#file-organization-guidelines)
- [Development Workflow](#development-workflow)
- [Code Standards](#code-standards)
- [Testing Requirements](#testing-requirements)
- [Pull Request Process](#pull-request-process)

## Getting Started

### Prerequisites

- Python 3.10 or higher
- Git for version control
- Virtual environment tool (venv, conda, or similar)

### Initial Setup

```bash
# Clone the repository
git clone https://github.com/haniae/Team2-CBA-Project.git
cd Team2-CBA-Project

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows
# source .venv/bin/activate    # macOS/Linux

# Install dependencies
pip install -r requirements.txt
pip install -e .

# Configure environment
cp env.example .env
# Edit .env with your settings
```

## File Organization Guidelines

### Directory Structure

Our repository follows a strict organizational structure. **Always place files in the correct directory:**

#### `/src/benchmarkos_chatbot/`
**Purpose:** Core application code (production-ready modules)

**What belongs here:**
- Analytics engine components
- Database abstraction layers
- Data ingestion pipelines
- LLM client integrations
- Web API endpoints
- Parsing/NLP modules

**What does NOT belong here:**
- Test files (go to `/tests/`)
- Scripts (go to `/scripts/`)
- Documentation (go to `/docs/`)
- Experimental code (go to `/analysis/experiments/`)

#### `/scripts/`
**Purpose:** Executable scripts and utilities

**Subdirectories:**
- `ingestion/` - Data ingestion scripts (SEC filings, quotes, etc.)
- `utility/` - Helper scripts (monitoring, validation, status checks)

**Examples:**
- `scripts/ingestion/fill_data_gaps.py` - Smart gap-filling ingestion
- `scripts/utility/check_database_simple.py` - Database verification
- `scripts/utility/quick_status.py` - Quick status reports

#### `/docs/`
**Purpose:** All documentation files

**Subdirectories:**
- `reports/` - Generated analysis and improvement reports
- `analysis/` - Consolidated analysis documentation from experiments

**File naming conventions:**
- Use UPPER_CASE for major guides: `INSTALLATION_GUIDE.md`, `SETUP_GUIDE.md`
- Use lowercase for technical docs: `architecture.md`, `orchestration_playbook.md`
- Use descriptive names: `PHASE1_ANALYTICS_FEATURES.md` vs `features.md`

#### `/tests/`
**Purpose:** All test files and test utilities

**Subdirectories:**
- `regression/` - Regression test suites
- `cache/` - Test cache data
- `data/` - Test fixtures and sample data
- `outputs/` - Test output files

**Naming conventions:**
- Test files MUST start with `test_`: `test_analytics.py`, `test_database.py`
- Verification scripts start with `verify_`: `verify_metrics.py`

#### `/analysis/`
**Purpose:** Experimental and analysis code (not production-ready)

**Subdirectories:**
- `experiments/` - Experimental feature implementations
- `scripts/` - Analysis and validation scripts

**When to use:**
- Testing new algorithms or approaches
- Performance benchmarking
- Feature prototypes before production integration

#### `/data/`
**Purpose:** Data files and databases

**Subdirectories:**
- `sqlite/` - SQLite database files
- `tickers/` - Ticker universe lists
- `external/` - External data sources (IMF, etc.)

#### `/tools/`
**Purpose:** Standalone tools and maintenance scripts

**Examples:**
- `refresh_ticker_catalog.py` - Ticker catalog management

#### `/webui/`
**Purpose:** Web interface files

**Contains:**
- HTML, CSS, JavaScript files
- Static assets
- Frontend configuration

#### `/cache/`
**Purpose:** Runtime cache files (generated, not committed)

**Contains:**
- Downloaded EDGAR data
- Temporary processing files
- Progress markers

### Root Directory Files

**Keep the root directory clean!** Only these types of files should be in the root:

✅ **Allowed in root:**
- `README.md` - Main project README
- `CONTRIBUTING.md` - This file
- `LICENSE` - Project license
- `pyproject.toml` - Project configuration
- `requirements.txt` - Python dependencies
- `env.example` - Environment variable template
- `.gitignore` - Git ignore rules
- Entry point scripts: `run_chatbot.py`, `serve_chatbot.py`
- Shell scripts for common tasks: `run_data_ingestion.ps1`, `run_data_ingestion.sh`
- Generated tracking files: `fill_gaps_summary.json`

❌ **Do NOT put in root:**
- Documentation files (move to `/docs/`)
- Utility scripts (move to `/scripts/utility/`)
- Test files (move to `/tests/`)
- Reports (move to `/docs/reports/` or `/docs/analysis/`)

## Development Workflow

### Before Starting Work

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Ensure your environment is up to date:**
   ```bash
   git pull origin main
   pip install -r requirements.txt
   ```

### During Development

1. **Follow the file organization guidelines above**
2. **Write tests for new features**
3. **Update documentation as needed**
4. **Keep commits focused and descriptive**

### Before Committing

1. **Run tests:**
   ```bash
   pytest
   ```

2. **Check for linting issues:**
   ```bash
   # Optional: Run linter if configured
   # ruff check .
   # black --check .
   ```

3. **Verify your changes:**
   ```bash
   # Test the chatbot
   python run_chatbot.py
   
   # Test the web interface
   python serve_chatbot.py --port 8000
   ```

## Code Standards

### Python Style

- Follow PEP 8 style guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Keep functions focused and modular

### Documentation

- Update README.md if adding new features
- Add docstrings to new functions and classes
- Create/update relevant documentation in `/docs/`
- Include usage examples for new scripts

### Example Function Documentation

```python
def fetch_company_metrics(ticker: str, years: int = 5) -> dict:
    """
    Fetch financial metrics for a company.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        years: Number of years of historical data (default: 5)
    
    Returns:
        Dictionary containing metric snapshots and metadata
    
    Raises:
        ValueError: If ticker is invalid
        ConnectionError: If SEC API is unreachable
    
    Example:
        >>> metrics = fetch_company_metrics('AAPL', years=3)
        >>> print(metrics['revenue'])
    """
    # Implementation
    pass
```

## Testing Requirements

### Test Coverage

- All new features must include tests
- Aim for >80% code coverage
- Test both success and failure cases

### Test Types

1. **Unit Tests** - Test individual functions/classes
   ```python
   # tests/test_analytics.py
   def test_calculate_revenue_growth():
       result = calculate_growth(100, 120)
       assert result == 0.20
   ```

2. **Integration Tests** - Test component interactions
   ```python
   # tests/test_data_ingestion.py
   def test_ingest_and_retrieve():
       ingest_company('AAPL')
       metrics = fetch_metrics('AAPL')
       assert len(metrics) > 0
   ```

3. **Regression Tests** - Ensure bug fixes stay fixed
   ```python
   # tests/regression/test_ticker_resolution.py
   def test_jp_morgan_ticker_resolution():
       # Regression test for Issue #123
       result = resolve_ticker("JP Morgan")
       assert result == "JPM"
   ```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_analytics.py

# Run with coverage
pytest --cov=src/benchmarkos_chatbot

# Run only regression tests
pytest tests/regression/
```

## Pull Request Process

### 1. Pre-PR Checklist

- [ ] Code follows file organization guidelines
- [ ] All tests pass locally
- [ ] New features have tests
- [ ] Documentation is updated
- [ ] No unnecessary files in root directory
- [ ] Commit messages are clear and descriptive

### 2. Creating the PR

1. **Push your branch:**
   ```bash
   git push origin feature/your-feature-name
   ```

2. **Create PR on GitHub:**
   - Navigate to the repository
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template

3. **PR Title Format:**
   - `Feature: Add sector benchmarking analytics`
   - `Fix: Resolve ticker resolution for JP Morgan`
   - `Docs: Update installation guide`
   - `Refactor: Reorganize analysis directory`

4. **PR Description Should Include:**
   - Summary of changes
   - Related issues (e.g., "Fixes #123")
   - Testing performed
   - Screenshots (if UI changes)
   - Breaking changes (if any)

### 3. Code Review Process

- Address reviewer feedback promptly
- Keep discussions focused and professional
- Make requested changes in new commits
- Mark conversations as resolved when addressed

### 4. After Approval

- Squash commits if requested
- Ensure CI/CD checks pass
- Merge using "Squash and merge" (preferred) or "Merge commit"

## Common Contribution Patterns

### Adding a New Script

1. Determine correct location:
   - Data ingestion → `scripts/ingestion/`
   - Utility/monitoring → `scripts/utility/`
   - Experimental → `analysis/scripts/`

2. Create the script with proper documentation:
   ```python
   """
   Script Name: fill_data_gaps.py
   Purpose: Intelligently fill missing data for specified years
   Author: Your Name
   Date: 2025-10-26
   
   Usage:
       python scripts/ingestion/fill_data_gaps.py --years 5
   """
   ```

3. Add to documentation in README.md

### Adding a New Feature

1. Design the feature (discuss in issues if major)
2. Create feature branch
3. Implement in appropriate module under `src/benchmarkos_chatbot/`
4. Write comprehensive tests
5. Update documentation
6. Submit PR with examples

### Fixing a Bug

1. Create issue describing the bug (if doesn't exist)
2. Write a failing test that reproduces the bug
3. Fix the bug
4. Verify test now passes
5. Add regression test to prevent recurrence
6. Submit PR referencing the issue

## Questions or Issues?

- **General questions:** Open a GitHub Discussion
- **Bug reports:** Open a GitHub Issue with reproduction steps
- **Feature requests:** Open a GitHub Issue with use case description
- **Security concerns:** Email the team directly (see README.md)

## License

By contributing to BenchmarkOS, you agree that your contributions will be licensed under the same license as the project.

---

Thank you for contributing to BenchmarkOS! Your efforts help build a better financial analytics platform for everyone.

