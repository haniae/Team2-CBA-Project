# Package Requirements Guide

## Overview
This document outlines all Python packages required to run the BenchmarkOS Chatbot, categorized by importance and functionality.

## ✅ Essential Packages (Required)

These packages are **required** for the chatbot to function:

### Core Framework
- **fastapi>=0.111.0** - Web framework for the API and web interface
- **uvicorn[standard]>=0.30.0** - ASGI server to run the FastAPI application
- **python-dotenv>=1.0.1** - Environment variable management (has fallback if missing)

### AI/ML
- **openai>=1.35.0** - OpenAI API client for LLM integration (optional if using local mode)

### Database
- **psycopg2-binary>=2.9.9** - PostgreSQL adapter (optional if using SQLite only)
- **SQLAlchemy>=2.0** - Database ORM (optional if using SQLite only)

### HTTP & API
- **requests>=2.32.0** - HTTP library for API calls to SEC EDGAR, Yahoo Finance, etc.

### Financial Data Sources
- **yfinance>=0.2.40** - Yahoo Finance API client for market data (has fallback if missing)

### Data Processing
- **pandas>=2.0.0** - Data manipulation and analysis
- **numpy>=1.26,<2.3** - Numerical computing (required by pandas and ML modules)

## 📦 Optional Packages (Recommended)

These packages enhance functionality but have fallbacks:

### Financial Data Sources
- **fredapi>=0.5.0** - Federal Reserve Economic Data API (optional)
- **pandas-datareader>=0.10.0** - Additional financial data sources (optional)

### Data Visualization
- **plotly>=5.17.0** - Interactive charts and graphs
- **matplotlib>=3.7.0** - Static plotting
- **seaborn>=0.12.0** - Statistical visualization

### Document Generation
- **fpdf2>=2.7.8** - PDF generation
- **python-pptx>=0.6.23** - PowerPoint generation
- **openpyxl>=3.1.5** - Excel file handling

### ML Forecasting (Optional)
- **pmdarima>=2.0.0** - ARIMA time series forecasting
- **statsmodels>=0.14.0** - Statistical modeling
- **prophet>=1.1.0** - Facebook Prophet forecasting
- **scikit-learn>=1.3.0** - Machine learning utilities
- **scipy>=1.11.0** - Scientific computing
- **optuna>=3.0.0** - Hyperparameter optimization
- **shap>=0.42.0** - Model explainability
- **ruptures>=1.1.8** - Change point detection
- **pandas-ta>=0.3.14b0** - Technical indicators

### Deep Learning (Optional)
- **torch>=2.1.0** - PyTorch deep learning framework
- **tensorflow>=2.13.0** - TensorFlow deep learning framework
- **keras>=2.13.0** - High-level neural networks API
- **transformers>=4.35.0** - Hugging Face transformers
- **sentence-transformers>=2.2.0** - Sentence embeddings

### NLP (Optional)
- **langchain>=0.1.0** - LLM application framework (not currently used - custom RAG implementation)
- **nltk>=3.8.0** - Natural language processing
- **spacy>=3.7.0** - Advanced NLP
- **textblob>=0.17.0** - Text processing
- **openai-whisper>=20231117** - Speech recognition

### Web & Frontend (Optional)
- **jinja2>=3.1.0** - Template engine
- **aiofiles>=23.0.0** - Async file operations
- **streamlit>=1.28.0** - Streamlit web apps
- **gradio>=4.0.0** - Gradio web interfaces
- **flask>=2.3.0** - Flask web framework (alternative to FastAPI)
- **dash>=2.14.0** - Plotly Dash web apps

### Real-time & WebSocket (Optional)
- **websockets>=12.0** - WebSocket support
- **socketio>=5.10.0** - Socket.IO support
- **redis>=5.0.0** - Redis caching
- **celery>=5.3.0** - Distributed task queue

### Testing (Development)
- **pytest>=8.2.0** - Testing framework
- **pytest-asyncio>=0.21.0** - Async testing support
- **pytest-cov>=4.0.0** - Coverage reporting

### Development Tools
- **black>=23.0.0** - Code formatter
- **flake8>=6.0.0** - Linter
- **mypy>=1.5.0** - Type checker

### Logging & Monitoring
- **structlog>=23.0.0** - Structured logging
- **rich>=13.0.0** - Rich text and formatting

### Security
- **cryptography>=41.0.0** - Cryptographic utilities
- **python-jose[cryptography]>=3.3.0** - JWT token handling

### Utilities
- **click>=8.1.0** - CLI framework
- **tqdm>=4.65.0** - Progress bars
- **python-dateutil>=2.8.0** - Date utilities
- **pyyaml>=6.0.0** - YAML parsing

## 📋 Installation

### Minimal Installation (Essential Packages Only)
```bash
pip install fastapi uvicorn[standard] python-dotenv requests pandas numpy yfinance openai
```

### Full Installation (All Packages)
```bash
pip install -r requirements.txt
```

### Installation from pyproject.toml
```bash
pip install -e .
```

This will install the essential packages defined in `pyproject.toml`.

## 🔍 Package Dependency Analysis

### Import Analysis
- **fastapi** - Used in `web.py` (required)
- **uvicorn** - Used in `serve_chatbot.py` (required)
- **pandas** - Used in `data_ingestion.py`, `analytics_engine.py`, and many ML modules (required)
- **numpy** - Required by pandas and ML modules (required)
- **requests** - Used in `chatbot.py`, `data_sources.py` (required)
- **openai** - Used in `llm_client.py` (required if using OpenAI, optional for local mode)
- **yfinance** - Used in `data_sources.py`, `external_data.py` (has fallback if missing)
- **pydantic** - Comes with fastapi (required)
- **python-dotenv** - Used in `config.py` (has fallback if missing)

### Optional Dependencies with Fallbacks
The codebase includes try/except blocks for these packages:
- `yfinance` - Falls back to manual HTTP requests if missing
- `python-dotenv` - Falls back to os.getenv if missing
- `pandas` - Some modules have fallbacks, but most require it
- `fredapi` - Optional, only used if available

## ✅ Verification

To verify all essential packages are installed:

```bash
python -c "import fastapi, uvicorn, pandas, numpy, requests, yfinance, openai, pydantic; print('All essential packages installed')"
```

## 🚨 Common Issues

### Missing pandas
If pandas is missing, the chatbot will fail during data ingestion and analytics.

### Missing fastapi/uvicorn
If these are missing, the web interface will not start.

### Missing openai
If openai is missing and `LLM_PROVIDER=openai`, the chatbot will fail. Use `LLM_PROVIDER=local` for testing without OpenAI.

### Missing yfinance
If yfinance is missing, market data fetching will fail, but the chatbot can still function with SEC data only.

## 📝 Notes

1. **pyproject.toml** includes only essential packages for minimal installation
2. **requirements.txt** includes all packages (essential + optional)
3. Some packages have version constraints (e.g., numpy<2.3 for pmdarima compatibility)
4. PostgreSQL packages (psycopg2-binary, SQLAlchemy) are optional if using SQLite only
5. ML packages are optional unless using forecasting features
6. Web frontend packages (streamlit, gradio, dash) are optional unless using those interfaces

