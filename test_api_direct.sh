#!/bin/bash
# Test the chatbot API directly to verify backend is working

echo "========================================================================"
echo "Testing Chatbot API Directly (Bypasses Browser Cache)"
echo "========================================================================"
echo ""

echo "Test 1: What's Amazon trading at?"
echo "------------------------------------------------------------------------"
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What'\''s Amazon trading at?"}' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Dashboard: {data.get(\"dashboard\")}')
print(f'Reply preview: {data.get(\"reply\", \"\")[:200]}...')
print(f'Contains Amazon: {\"amazon\" in data.get(\"reply\", \"\").lower()}')
print(f'Contains AMZN: {\"amzn\" in data.get(\"reply\", \"\").lower()}')
print('')
"

echo ""
echo "Test 2: What's Microsoft's sales figures?"
echo "------------------------------------------------------------------------"
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What'\''s Microsoft'\''s sales figures?"}' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Dashboard: {data.get(\"dashboard\")}')
print(f'Reply preview: {data.get(\"reply\", \"\")[:200]}...')
print(f'Contains Microsoft: {\"microsoft\" in data.get(\"reply\", \"\").lower()}')
print(f'Contains MSFT: {\"msft\" in data.get(\"reply\", \"\").lower()}')
print('')
"

echo ""
echo "Test 3: How profitable is Microsoft?"
echo "------------------------------------------------------------------------"
curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt":"How profitable is Microsoft?"}' | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Dashboard: {data.get(\"dashboard\")}')
print(f'Reply preview: {data.get(\"reply\", \"\")[:200]}...')
print(f'Contains Microsoft: {\"microsoft\" in data.get(\"reply\", \"\").lower()}')
print('')
"

echo ""
echo "========================================================================"
echo "API Test Complete"
echo "========================================================================"
echo ""
echo "If all tests show 'Dashboard: None' and correct company mentions,"
echo "the backend is working correctly."
echo ""
echo "The issue in the browser UI is likely:"
echo "1. Browser is loading old conversation with old dashboards"
echo "2. LocalStorage has cached conversation data"
echo ""
echo "SOLUTION:"
echo "1. Open browser DevTools (F12)"
echo "2. Application tab -> Local Storage -> http://localhost:8000"
echo "3. Delete all items"
echo "4. Refresh page"
echo "5. Test in a NEW conversation"
echo ""

