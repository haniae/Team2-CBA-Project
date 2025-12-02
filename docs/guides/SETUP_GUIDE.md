# BenchmarkOS Chatbot Setup Guide

## Table of Contents

1. [Quick Start](#-quick-start)
2. [Dependencies](#-dependencies)
3. [Configuration Files](#-configuration-files)
4. [Project Structure](#️-project-structure)
5. [Running the Application](#-running-the-application)
6. [Troubleshooting](#-troubleshooting)
7. [Features](#-features)
8. [Security Notes](#-security-notes)
9. [Performance Tips](#-performance-tips)
10. [Support](#-support)
11. [Development Notes](#-development-notes)

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10 or higher
- Node.js 16+ (for web dashboard)
- Git

### 1. Clone Repository

```bash
git clone <repository-url>
cd Team2-CBA-Project-1
```

### 2. Python Environment Setup

**On Windows:**
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt
```

**On macOS/Linux:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your configuration
# On Windows: notepad .env
# On macOS/Linux: nano .env
```

**Required variables:**
- `OPENAI_API_KEY` - Your OpenAI API key (required)
- `DATABASE_URL` - Database connection string (required)
- `SEC_API_KEY` - SEC API key (optional, for SEC data fetching)

### 4. Database Setup

```bash
# Initialize database
python -c "from src.finanlyzeos_chatbot.database import init_db; init_db()"
```

**Optional:** Load sample data for testing:

```bash
python scripts/utility/load_sample_data.py
```

### 5. Web Dashboard Setup (Optional)

If you want to use the web dashboard:

```bash
# Navigate to webui directory
cd webui

# Install Node.js dependencies
npm install

# Start web server
npm start
```

> **Alternative**: You can also use Python's built-in HTTP server:
> ```bash
> python -m http.server 8000
> ```

### 6. Run Chatbot

Start the chatbot server:

```bash
# From project root directory
python run_chatbot.py
```

> **Alternative**: Use the web interface launcher:
> ```bash
> python serve_chatbot.py
> ```

## 📦 Dependencies

### Python Dependencies

Core packages required for the chatbot backend:

| Category | Packages | Purpose |
|----------|----------|---------|
| **Core Framework** | FastAPI, Uvicorn | Web framework and ASGI server |
| **Database** | SQLAlchemy, psycopg2-binary | ORM and PostgreSQL driver |
| **AI/ML** | OpenAI, python-dotenv | LLM integration and environment management |
| **Data Processing** | requests, openpyxl | HTTP requests and Excel file handling |
| **Documentation** | fpdf2, python-pptx | PDF and PowerPoint generation |
| **Testing** | pytest | Unit and integration testing |

**Install all dependencies:**
```bash
pip install -r requirements.txt
```

### Node.js Dependencies

Required for the web dashboard (optional):

| Package | Version | Purpose |
|---------|---------|---------|
| **express** | ^4.18.2 | Web server framework |
| **axios** | ^1.6.0 | HTTP client for API calls |
| **chart.js** | ^4.4.0 | Financial data visualization |

**Install Node.js dependencies:**
```bash
cd webui
npm install
```

## 🔧 Configuration Files

### .env.example
```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4

# Database Configuration
DATABASE_URL=sqlite:///data/sqlite/finanlyzeos_chatbot.sqlite3
# For PostgreSQL:
# DATABASE_URL=postgresql://user:password@localhost:5432/finanlyzeos

# SEC API Configuration (optional)
SEC_API_KEY=your_sec_api_key_here
SEC_USER_AGENT=your_company_name

# Web Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=True

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE=logs/chatbot.log
```

### package.json (for webui)
```json
{
  "name": "finanlyzeos-webui",
  "version": "1.0.0",
  "description": "BenchmarkOS Chatbot Web Interface",
  "main": "app.js",
  "scripts": {
    "start": "node app.js",
    "dev": "nodemon app.js",
    "build": "webpack --mode production"
  },
  "dependencies": {
    "express": "^4.18.2",
    "axios": "^1.6.0",
    "chart.js": "^4.4.0"
  },
  "devDependencies": {
    "nodemon": "^3.0.0",
    "webpack": "^5.89.0"
  }
}
```

## 🗂️ Project Structure

```
Team2-CBA-Project-1/
├── src/
│   └── finanlyzeos_chatbot/
│       ├── __init__.py
│       ├── analytics_engine.py
│       ├── chatbot.py
│       ├── database.py
│       ├── web.py
│       └── ...
├── webui/
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   ├── cfi_dashboard.html
│   ├── cfi_compare.html
│   └── data/
├── data/
│   ├── sqlite/
│   └── external/
├── scripts/
│   ├── utility/
│   └── ingestion/
├── tests/
├── requirements.txt
├── pyproject.toml
├── package.json
├── .env.example
└── README.md
```

## 🚀 Running the Application

### Option 1: Python Only
```bash
# Start chatbot server
python run_chatbot.py

# Access at http://localhost:8000
```

### Option 2: With Web Dashboard
```bash
# Terminal 1: Start Python backend
python serve_chatbot.py

# Terminal 2: Start web dashboard
cd webui
npm start

# Access dashboard at http://localhost:3000
```

### Option 3: Development Mode
```bash
# Start with auto-reload
uvicorn src.finanlyzeos_chatbot.web:app --reload --host 0.0.0.0 --port 8000
```

## 🔍 Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```bash
   # Check database file exists
   ls -la data/sqlite/
   
   # Recreate database
   python -c "from src.finanlyzeos_chatbot.database import init_db; init_db()"
   ```

2. **OpenAI API Error**
   ```bash
   # Check API key
   echo $OPENAI_API_KEY
   
   # Test API connection
   python -c "import openai; print('API Key valid')"
   ```

3. **Port Already in Use**
   ```bash
   # Find process using port
   lsof -i :8000
   
   # Kill process
   kill -9 <PID>
   ```

4. **Node.js Dependencies**
   ```bash
   # Clear npm cache
   npm cache clean --force
   
   # Reinstall dependencies
   rm -rf node_modules package-lock.json
   npm install
   ```

### Logs
```bash
# Check application logs
tail -f logs/chatbot.log

# Check error logs
grep ERROR logs/chatbot.log
```

## 📊 Features

### Chatbot Features
- ✅ Single ticker analysis
- ✅ Multi-ticker comparison
- ✅ Time period filtering
- ✅ KPI calculations
- ✅ Professional formatting

### Web Dashboard Features
- ✅ CFI Dashboard
- ✅ Company comparison
- ✅ Interactive charts
- ✅ Data export
- ✅ Responsive design

## 🔐 Security Notes

> **Important**: Follow these security best practices to protect your system and data.

1. **Never commit `.env` files** - Environment files contain sensitive API keys and credentials
2. **Use environment variables for secrets** - Never hardcode API keys in source code
3. **Rotate API keys regularly** - Update your API keys periodically for better security
4. **Use HTTPS in production** - Always use encrypted connections in production environments
5. **Validate all user inputs** - Sanitize and validate all user-provided data

**Additional Recommendations:**
- Use secrets management tools (e.g., AWS Secrets Manager, HashiCorp Vault) in production
- Implement rate limiting to prevent abuse
- Regularly update dependencies to patch security vulnerabilities
- Use strong passwords for database connections
- Enable authentication for production deployments

## 📈 Performance Tips

1. **Database Indexing**: Ensure proper indexes on frequently queried columns
2. **Caching**: Use Redis for session management
3. **Rate Limiting**: Implement API rate limiting
4. **Monitoring**: Use logging and monitoring tools
5. **Scaling**: Consider using load balancers for production

## 🆘 Support

If you encounter issues or have questions:

1. **Check this setup guide** - Many common issues are covered here
2. **Review error logs** - Check `logs/chatbot.log` for detailed error messages
3. **Check GitHub issues** - Search existing issues or create a new one
4. **Contact team members** - Reach out to the development team for assistance

**Useful Resources:**
- [RAG Explained](../RAG_EXPLAINED.md) - Understanding the RAG system
- [Architecture Documentation](../ARCHITECTURE_TECHNICAL_FLOW.md) - System architecture details
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Additional troubleshooting steps

## 📝 Development Notes

- Use `black` for code formatting
- Use `pytest` for testing
- Follow PEP 8 style guide
- Document all functions and classes
- Use type hints where possible
