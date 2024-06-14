import re
import os
import argparse
import statistics
from collections import OrderedDict, defaultdict
import pandas as pd

parser = argparse.ArgumentParse(description='Benchmark to look for')
parser.add_argument('benchmark', type=str, help='Benchmark name')
args = parser.parser_args()

timelist = defaultdict(list, OrderedDict())
stats = defaultdict(list, OrderedDict())
idx = 0

base_addr = os.path.join('/users/taeminha/results/', args.benchmark)
if not os.path.isdir(base_addr):
    print(f'Directory {base_addr} does not exist')
    exit()

# now that we have acess to /benchmark, we want to iterate through all iteration_x directories
# for each iteration_x directories, there should be a file named "iteration_x_result.txt" created by print_result.py

for i in range(1, 6):
    iteration_x_dir = os.path.join(base_addr, f'iteration_{i}')
    if not os.path.isdir(iteration_x_dir):
        print(f'Directory {iteration_x_dir} does not exist')
        exit()
    file_list = glob.glob.(os.path.join(iteration_x_dir, '*.txt')
    for file in file_list:        
        with open(file) as f:
            for line in f:
                if "Remote" in line:
                    timelist[idx % 50].append(float(re.search(r"\d+\.\d+", line).group()))
                    idx += 1
        

# print(timelist)
print()

for k,v in timelist.items():
    stats[k] = [min(v), max(v), statistics.median(v), statistics.mean(v), statistics.stdev(v)]

# print(stats)

df = pd.DataFrame.from_dict(stats, orient='index', columns=['min', 'max', 'median', 'mean', 'std_dev'])
print(df)
