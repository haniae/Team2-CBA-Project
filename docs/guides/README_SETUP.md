# BenchmarkOS Chatbot - Complete Setup Guide

## 🎯 Overview

This repository contains a complete financial chatbot system with:
- **Python Backend**: FastAPI-based chatbot with financial analytics
- **Web Dashboard**: Node.js frontend with CFI dashboard
- **Database**: SQLite/PostgreSQL support
- **AI Integration**: OpenAI GPT-4 integration

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)
```bash
# 1. Clone repository
git clone <repository-url>
cd Team2-CBA-Project-1

# 2. Run automated setup
python setup.py

# 3. Install Node.js dependencies (after Node.js is installed)
./install_node_deps.sh

# 4. Start everything
./start_all.sh
```

### Option 2: Manual Setup
```bash
# 1. Python Setup
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. Node.js Setup
cd webui
npm install
cd ..

# 3. Environment Setup
cp env.example .env
# Edit .env with your configuration

# 4. Start Services
python run_chatbot.py  # Terminal 1
cd webui && npm start  # Terminal 2
```

## 📋 Prerequisites

### Required Software
- **Python 3.10+** ✅
- **Node.js 16+** (Install from [nodejs.org](https://nodejs.org/))
- **Git** ✅

### Required API Keys
- **OpenAI API Key** (Get from [platform.openai.com](https://platform.openai.com/))
- **SEC API Key** (Optional, get from [sec.gov](https://www.sec.gov/))

## 📁 Project Structure

```
Team2-CBA-Project-1/
├── src/finanlyzeos_chatbot/     # Python backend
├── webui/                       # Node.js frontend
├── data/                        # Database and data files
├── scripts/                     # Utility scripts
├── tests/                       # Test files
├── requirements.txt             # Python dependencies
├── webui/package.json          # Node.js dependencies
├── env.example                  # Environment template
├── setup.py                     # Automated setup script
├── run_chatbot.py              # Python server starter
├── start_all.sh                 # Start everything script
└── install_node_deps.sh         # Node.js dependencies installer
```

## 🔧 Configuration

### Environment Variables (.env)
```env
# Required
OPENAI_API_KEY=your_openai_api_key_here
DATABASE_URL=sqlite:///data/sqlite/finanlyzeos_chatbot.sqlite3

# Optional
SEC_API_KEY=your_sec_api_key_here
HOST=0.0.0.0
PORT=8000
DEBUG=True
```

### Node.js Configuration (webui/package.json)
```json
{
  "dependencies": {
    "express": "^4.18.2",
    "chart.js": "^4.4.0",
    "axios": "^1.6.0"
  }
}
```

## 🚀 Running the Application

### Development Mode
```bash
# Start with auto-reload
./start_all.sh
```

### Production Mode
```bash
# Python backend
source venv/bin/activate
uvicorn src.finanlyzeos_chatbot.web:app --host 0.0.0.0 --port 8000 --workers 4

# Node.js frontend
cd webui
npm start
```

## 📱 Access Points

- **Chatbot API**: http://localhost:8000
- **Web Dashboard**: http://localhost:3000
- **CFI Dashboard**: http://localhost:3000/dashboard
- **Comparison Tool**: http://localhost:3000/compare
- **API Documentation**: http://localhost:8000/docs

## 🔍 Features

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

## 🛠️ Development

### Python Development
```bash
# Activate virtual environment
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest

# Format code
black src/
```

### Node.js Development
```bash
# Navigate to webui
cd webui

# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npm test
```

## 🔧 Troubleshooting

### Common Issues

1. **Node.js not found**
   ```bash
   # Install Node.js from https://nodejs.org/
   # Or use nvm: curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
   ```

2. **Python dependencies fail**
   ```bash
   # Upgrade pip and try again
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Database connection error**
   ```bash
   # Initialize database
   python -c "from src.finanlyzeos_chatbot.database import init_db; init_db()"
   ```

4. **Port already in use**
   ```bash
   # Find and kill process
   lsof -i :8000
   kill -9 <PID>
   ```

### Logs
```bash
# Check application logs
tail -f logs/chatbot.log

# Check error logs
grep ERROR logs/chatbot.log
```

## 📦 Dependencies

### Python Dependencies
- **FastAPI**: Web framework
- **Uvicorn**: ASGI server
- **OpenAI**: AI integration
- **SQLAlchemy**: Database ORM
- **Pandas**: Data processing
- **Plotly**: Interactive data visualization
- **Dash**: Web application framework
- **Requests**: HTTP client

### Node.js Dependencies
- **Express**: Web server
- **Chart.js**: Data visualization
- **Plotly.js**: Interactive charts
- **Axios**: HTTP client
- **CORS**: Cross-origin requests

## 🔐 Security

- Never commit `.env` files
- Use environment variables for secrets
- Rotate API keys regularly
- Use HTTPS in production
- Validate all user inputs

## 📈 Performance

- Database indexing for fast queries
- Caching for frequently accessed data
- Rate limiting for API endpoints
- Monitoring and logging
- Load balancing for production

## 🆘 Support

For issues and questions:
1. Check this setup guide
2. Review error logs
3. Check GitHub issues
4. Contact team members

## 📝 Development Notes

- Use `black` for Python code formatting
- Use `pytest` for testing
- Follow PEP 8 style guide
- Document all functions and classes
- Use type hints where possible
- Test all new features

## 🎉 Success!

Once everything is running, you should see:
- ✅ Python backend on port 8000
- ✅ Node.js frontend on port 3000
- ✅ Database initialized
- ✅ All dependencies installed
- ✅ Environment configured

**Happy coding!** 🚀
