#!/bin/bash
python main.py &
streamlit run dashboard.py --server.headless true
