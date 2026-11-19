Bash:
1. WSL: Reopen Folder in WSL.
2. cd /mnt/c/UNI/Masters/AIT2/assigment_1/Start-Kit

./build/lifelong \
  -i example_problems/random.domain/random-example_400.json \
  -o output_python_scheduler.json \
  -s 1000 \
  --schedulerPython true

  3. cd /mnt/c/UNI/Masters/AIT2/assigment_1/PlanViz

/root/planviz-venv/bin/python script/run.py \
  --map /mnt/c/UNI/Masters/AIT2/assigment_1/Start-Kit/example_problems/random.domain/maps/random-64-64-10.map \
  --plan /mnt/c/UNI/Masters/AIT2/assigment_1/Start-Kit/output_python_scheduler.json \
  --start 0 --end 1000


  # Default: C++ planner, scheduler, and executor
./build/lifelong -i example_problems/random.domain/random-example_400.json \
  -o output-cpp.json -s 1000

# Python scheduler; C++ planner and executor
./build/lifelong -i example_problems/random.domain/random-example_400.json \
  -o output-python-scheduler.json -s 1000 --schedulerPython true

# Python planner; C++ scheduler and executor
./build/lifelong -i example_problems/random.domain/random-example_400.json \
  -o output-python-planner.json -s 1000 --plannerPython true

# Python planner, scheduler, and executor
./build/lifelong -i example_problems/random.domain/random-example_400.json \
  -o output-all-python.json -s 1000 \
  --plannerPython true --schedulerPython true --executorPython true



Change the number of robots
The sample input specifies 400 agents. There isn’t a command-line option for changing that count: it’s determined by the problem files. The input JSON’s teamSize must agree with the number of starting locations in its agentFile. So, don’t just edit teamSize; make a matching agent file with that many valid, distinct starting locations and update the input JSON to reference it. The input format is described in Input_Output_Format.md.

Other useful things to experiment with
-o FILE: choose where the result JSON is saved.
-t MS: minimum time between planner updates; default is 1000 ms.
-n MS: initial planner time limit, default 1000 ms. This is not the number of agents.
-p MS: preprocessing time limit.
-a MS: per-execution-tick action time limit.
-x MS: executor plan-processing time limit.
-c 1, -c 2, or -c 3: control how much detail is written to the output JSON.
You can also experiment with the problem JSON settings: numTasksReveal, agentCounter, agentSize, and delayConfig (including its delay probability, duration range, and random seed). Make a copy of the input JSON before changing these, so you can compare runs against the original. The available command-line options and input settings are documented in Input_Output_Format.md.