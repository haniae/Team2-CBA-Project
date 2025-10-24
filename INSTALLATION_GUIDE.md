# BenchmarkOS Chatbot Installation Guide

## 🚀 Quick Installation

### Prerequisites
- **Python 3.10+** (✅ Already installed)
- **Node.js 16+** (❌ Needs installation)
- **Git** (✅ Already installed)

### 1. Install Node.js

#### Option A: Using Node Version Manager (Recommended)
```bash
# Install nvm (Node Version Manager)
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash

# Reload shell
source ~/.bashrc

# Install and use Node.js 18
nvm install 18
nvm use 18
nvm alias default 18
```

#### Option B: Direct Download
1. Go to [Node.js Official Website](https://nodejs.org/)
2. Download LTS version (18.x or higher)
3. Install following the instructions for your OS

#### Option C: Using Package Manager

**macOS (using Homebrew):**
```bash
brew install node
```

**Ubuntu/Debian:**
```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

**Windows (using Chocolatey):**
```bash
choco install nodejs
```

### 2. Verify Installation
```bash
# Check Node.js version
node --version
# Should show v18.x.x or higher

# Check npm version
npm --version
# Should show 9.x.x or higher
```

### 3. Run Setup Script
```bash
# Make setup script executable
chmod +x setup.py

# Run setup
python setup.py
```

### 4. Manual Setup (if script fails)

#### Python Setup
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

#### Node.js Setup
```bash
# Navigate to webui directory
cd webui

# Install Node.js dependencies
npm install

# Go back to root directory
cd ..
```

### 5. Environment Configuration
```bash
# Copy environment template
cp env.example .env

# Edit .env file with your configuration
# Required variables:
# - OPENAI_API_KEY=your_openai_api_key
# - DATABASE_URL=sqlite:///data/sqlite/benchmarkos_chatbot.sqlite3
```

### 6. Start the Application

#### Option A: Python Chatbot Only
```bash
# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate    # On Windows

# Start chatbot
python run_chatbot.py
```

#### Option B: Full Stack (Python + Web Dashboard)
```bash
# Terminal 1: Start Python backend
source venv/bin/activate
python run_chatbot.py

# Terminal 2: Start Web dashboard
cd webui
npm start
```

## 🔧 Troubleshooting

### Node.js Installation Issues

**Issue: npm command not found**
```bash
# Solution: Reinstall Node.js with npm
# Make sure to download from official website
# Or use nvm to manage Node.js versions
```

**Issue: Permission denied**
```bash
# Solution: Use sudo (Linux/macOS) or run as administrator (Windows)
sudo npm install -g npm
```

**Issue: Version conflicts**
```bash
# Solution: Use nvm to manage versions
nvm install 18
nvm use 18
```

### Python Issues

**Issue: Virtual environment not activated**
```bash
# Solution: Activate virtual environment
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate    # On Windows
```

**Issue: Package installation fails**
```bash
# Solution: Upgrade pip and try again
pip install --upgrade pip
pip install -r requirements.txt
```

### Database Issues

**Issue: Database not found**
```bash
# Solution: Initialize database
python -c "from src.benchmarkos_chatbot.database import init_db; init_db()"
```

**Issue: Permission denied on database**
```bash
# Solution: Check file permissions
chmod 664 data/sqlite/benchmarkos_chatbot.sqlite3
```

## 📦 Dependencies Overview

### Python Dependencies
- **FastAPI**: Web framework for API
- **Uvicorn**: ASGI server
- **OpenAI**: AI/ML integration
- **SQLAlchemy**: Database ORM
- **Pandas**: Data processing
- **Requests**: HTTP client

### Node.js Dependencies
- **Express**: Web server
- **Chart.js**: Data visualization
- **Axios**: HTTP client
- **CORS**: Cross-origin requests
- **Helmet**: Security headers

## 🚀 Running the Application

### Development Mode
```bash
# Start with auto-reload
uvicorn src.benchmarkos_chatbot.web:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
# Start with multiple workers
uvicorn src.benchmarkos_chatbot.web:app --host 0.0.0.0 --port 8000 --workers 4
```

### Web Dashboard
```bash
# Start web dashboard
cd webui
npm start
# Access at http://localhost:3000
```

## 🔍 Verification

### Check Python Setup
```bash
# Activate virtual environment
source venv/bin/activate

# Test imports
python -c "import fastapi, uvicorn, openai; print('✅ Python setup successful')"
```

### Check Node.js Setup
```bash
# Test Node.js
node --version
npm --version

# Test web dashboard
cd webui
npm start
# Should start server on port 3000
```

### Check Application
```bash
# Start chatbot
python run_chatbot.py
# Should start server on port 8000

# Test API
curl http://localhost:8000/health
# Should return health status
```

## 📱 Access Points

- **Chatbot API**: http://localhost:8000
- **Web Dashboard**: http://localhost:3000
- **CFI Dashboard**: http://localhost:3000/dashboard
- **Comparison Tool**: http://localhost:3000/compare
- **API Documentation**: http://localhost:8000/docs

## 🆘 Support

If you encounter issues:

1. **Check logs**: Look at console output for error messages
2. **Verify dependencies**: Make sure all packages are installed
3. **Check environment**: Ensure .env file is configured correctly
4. **Restart services**: Try stopping and starting again
5. **Clean install**: Remove node_modules and venv, then reinstall

## 📝 Notes

- **Virtual Environment**: Always activate before running Python commands
- **Node.js Version**: Use LTS version (18.x) for stability
- **Port Conflicts**: Make sure ports 8000 and 3000 are available
- **Firewall**: Ensure firewall allows connections on these ports
- **Permissions**: Check file permissions for database and logs directories
