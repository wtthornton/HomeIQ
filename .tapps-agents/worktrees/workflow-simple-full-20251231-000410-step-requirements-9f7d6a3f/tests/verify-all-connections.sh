#!/bin/bash
# Run all connection verification tests

echo "======================================================================"
echo "🧪 AI Automation Service - Connection Verification Suite"
echo "======================================================================"
echo ""

# Check python available
if ! command -v python3 &> /dev/null; then
    echo "❌ python3 not found. Please install Python 3.11+"
    exit 1
fi

# Check required packages
echo "📦 Checking required packages..."
REQUIRED_PACKAGES="paho-mqtt python-dotenv requests openai"
MISSING_PACKAGES=""

for package in $REQUIRED_PACKAGES; do
    if ! python3 -c "import ${package//-/_}" 2>/dev/null; then
        MISSING_PACKAGES="$MISSING_PACKAGES $package"
    fi
done

if [ -n "$MISSING_PACKAGES" ]; then
    echo "⚠️  Missing packages:$MISSING_PACKAGES"
    echo ""
    echo "Install with:"
    echo "  pip install$MISSING_PACKAGES"
    echo ""
    read -p "Install now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install$MISSING_PACKAGES
    else
        echo "❌ Cannot proceed without required packages"
        exit 1
    fi
fi

echo "✅ All required packages installed"
echo ""

# Test 1: MQTT
echo "======================================================================"
echo "Test 1/3: MQTT Connection"
echo "======================================================================"
python3 tests/verify-mqtt-connection.py
MQTT_RESULT=$?

echo ""
echo ""

# Test 2: Home Assistant API
echo "======================================================================"
echo "Test 2/3: Home Assistant API"
echo "======================================================================"
python3 tests/verify-ha-connection.py
HA_RESULT=$?

echo ""
echo ""

# Test 3: OpenAI API
echo "======================================================================"
echo "Test 3/3: OpenAI API"
echo "======================================================================"
python3 tests/verify-openai-connection.py
OPENAI_RESULT=$?

echo ""
echo ""

# Summary
echo "======================================================================"
echo "📊 FINAL SUMMARY"
echo "======================================================================"
echo ""

if [ $MQTT_RESULT -eq 0 ]; then
    echo "✅ MQTT Connection:           PASS"
else
    echo "❌ MQTT Connection:           FAIL"
fi

if [ $HA_RESULT -eq 0 ]; then
    echo "✅ Home Assistant API:        PASS"
else
    echo "❌ Home Assistant API:        FAIL"
fi

if [ $OPENAI_RESULT -eq 0 ]; then
    echo "✅ OpenAI API:                PASS"
else
    echo "❌ OpenAI API:                FAIL"
fi

echo ""
echo "======================================================================"

if [ $MQTT_RESULT -eq 0 ] && [ $HA_RESULT -eq 0 ] && [ $OPENAI_RESULT -eq 0 ]; then
    echo ""
    echo "🎉 All connection tests passed!"
    echo ""
    echo "✅ Story AI1.1 (MQTT Configuration) - COMPLETE"
    echo "🚀 Ready to proceed with Story AI1.2 (Backend Foundation)"
    echo ""
    exit 0
else
    echo ""
    echo "⚠️  Some tests failed. Please fix configuration and retry."
    echo ""
    echo "Run individual tests:"
    echo "  python3 tests/verify-mqtt-connection.py"
    echo "  python3 tests/verify-ha-connection.py"
    echo "  python3 tests/verify-openai-connection.py"
    echo ""
    exit 1
fi

