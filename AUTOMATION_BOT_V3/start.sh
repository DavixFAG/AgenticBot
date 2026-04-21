#!/bin/bash
export MALLOC_ARENA_MAX=2
echo "Starting Trading Bot..."
python main.py &
echo "Starting Streamlit Dashboard..."
streamlit run dashboard.py --server.port $PORT --server.address 0.0.0.0 --browser.gatherUsageStats false --server.headless true
