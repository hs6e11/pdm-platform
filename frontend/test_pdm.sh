#!/bin/bash

echo "🏭 PDM Platform Test Script"
echo "=========================="
echo

# Test 1: Backend Health Check
echo "1️⃣  Testing Backend Health..."
curl -s http://localhost:8000/api/iot/test
if [ $? -eq 0 ]; then
    echo "✅ Backend is running!"
else
    echo "❌ Backend not accessible. Start with: uvicorn simple_api:app --host 0.0.0.0 --port 8000 --reload"
    exit 1
fi
echo

# Test 2: Egypt Client Status
echo "2️⃣  Testing Egypt Client Status..."
curl -s http://localhost:8000/api/iot/clients/egypt_client_001/status
if [ $? -eq 0 ]; then
    echo "✅ Egypt client accessible!"
else
    echo "❌ Egypt client not found"
fi
echo

# Test 3: Send Test Data to Egypt Client
echo "3️⃣  Sending Test Data to Egypt Client..."
curl -X POST http://localhost:8000/api/iot/data/egypt_client_001 \
  -H "Authorization: Bearer egypt_secure_api_key_2024" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "egypt_client_001",
    "machine_id": "EG_M001",
    "machine_name": "CNC Mill Alpha",
    "timestamp": "2024-01-15T10:30:00Z",
    "location": "Cairo, Egypt",
    "timezone": "Africa/Cairo",
    "sensors": {
      "temperature": 48.5,
      "power_consumption": 15.2,
      "spindle_speed": 1800,
      "vibration": 25.3,
      "efficiency": 89.5,
      "status": "running"
    }
  }'

if [ $? -eq 0 ]; then
    echo "✅ Test data sent successfully!"
else
    echo "❌ Failed to send test data"
fi
echo

# Test 4: Get Egypt Machines List
echo "4️⃣  Getting Egypt Machines List..."
curl -s http://localhost:8000/api/iot/clients/egypt_client_001/machines
if [ $? -eq 0 ]; then
    echo "✅ Egypt machines data retrieved!"
else
    echo "⚠️  Egypt machines endpoint not available (this is okay for basic testing)"
fi
echo

# Test 5: Frontend Access Check
echo "5️⃣  Checking Frontend Access..."
if curl -s http://localhost:8080/pages/login.html > /dev/null; then
    echo "✅ Frontend is accessible at http://localhost:8080"
    echo "📱 Test URLs:"
    echo "   Login: http://localhost:8080/pages/login.html"
    echo "   Egypt Dashboard: http://localhost:8080/pages/egypt-dashboard.html"
    echo "   Oil & Gas: http://localhost:8080/pages/oil-gas-dashboard.html"
else
    echo "❌ Frontend not accessible. Start with: python -m http.server 8080 (from frontend directory)"
fi
echo

echo "🎯 Test Summary:"
echo "==============="
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:8080"
echo "Egypt Client ID: egypt_client_001"
echo "API Key: egypt_secure_api_key_2024"
echo
echo "Next Steps:"
echo "1. Visit http://localhost:8080/pages/login.html"
echo "2. Use credentials: egypt@manufacturing.eg / egypt2024"
echo "3. Monitor real-time Egypt dashboard"
echo
echo "✨ Happy Testing! ✨"
