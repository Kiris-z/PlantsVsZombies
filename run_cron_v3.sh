#!/bin/bash
cd /Users/maosen/code/PythonPlantsVsZombies
export SDL_VIDEODRIVER=dummy
export SDL_AUDIODRIVER=dummy
python3 test_qa_cron_v3.py 2>&1
