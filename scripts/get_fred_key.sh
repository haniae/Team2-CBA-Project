#!/bin/bash
# Quick script to help get FRED API key

echo "============================================================"
echo "FRED API Key Setup"
echo "============================================================"
echo ""
echo "Step 1: Open your browser and visit:"
echo "   https://fred.stlouisfed.org/docs/api/api_key.html"
echo ""
echo "Step 2: Click 'Request API Key' button"
echo ""
echo "Step 3: Fill out the form:"
echo "   - Email address (required)"
echo "   - Organization (can be 'Personal')"
echo "   - Intended use (e.g., 'Financial analysis research')"
echo ""
echo "Step 4: Submit the form"
echo "   - API key will be sent to your email instantly"
echo ""
echo "Step 5: Copy the API key from your email"
echo ""
echo "============================================================"
echo ""
read -p "Press Enter when you have your API key ready..."
echo ""
read -p "Enter your FRED API key: " FRED_KEY

if [ -z "$FRED_KEY" ]; then
    echo "No API key provided. Exiting."
    exit 1
fi

# Save to .env file
if [ -f .env ]; then
    # Check if FRED_API_KEY already exists
    if grep -q "FRED_API_KEY" .env; then
        echo ""
        read -p "FRED_API_KEY already exists in .env. Overwrite? (y/n): " overwrite
        if [ "$overwrite" = "y" ]; then
            # Remove old line and add new one
            sed -i '/^FRED_API_KEY=/d' .env
            echo "FRED_API_KEY=$FRED_KEY" >> .env
            echo "✅ Updated FRED_API_KEY in .env"
        else
            echo "Skipping .env update"
        fi
    else
        echo "" >> .env
        echo "# FRED API Key" >> .env
        echo "FRED_API_KEY=$FRED_KEY" >> .env
        echo "✅ Added FRED_API_KEY to .env"
    fi
else
    # Create new .env file
    echo "FRED_API_KEY=$FRED_KEY" > .env
    echo "✅ Created .env file with FRED_API_KEY"
fi

# Set environment variable for current session
export FRED_API_KEY="$FRED_KEY"
echo "✅ Set FRED_API_KEY for current session"
echo ""
echo "Testing connection..."
echo ""

# Test the connection (activate venv first)
if [ -d ".venv" ]; then
    source .venv/bin/activate
    python scripts/test_fred_api.py
else
    python3 scripts/test_fred_api.py
fi

if [ $? -eq 0 ]; then
    echo ""
    echo "============================================================"
    echo "✅ FRED API Setup Complete!"
    echo "============================================================"
    echo ""
    echo "Next steps:"
    echo "1. Restart your chatbot server to load the API key"
    echo "2. Test with a query like: 'What is Apple's revenue?'"
    echo "3. You should see economic context from FRED in responses"
    echo ""
else
    echo ""
    echo "⚠️  Setup complete but connection test failed"
    echo "   Please check your API key and try again"
    echo ""
fi

