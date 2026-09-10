#!/bin/bash
cd /volume1/data/line_goodmorning
unset PYTHONPATH
/usr/bin/python3 run_daily.py >> /volume1/data/line_goodmorning/logs/run.log 2>&1
