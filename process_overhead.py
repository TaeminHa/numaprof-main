import os
import glob
import argparse
import re
import statistics
import threading
from itertools import combinations, chain
from collections import OrderedDict, defaultdict
import pandas as pd

def process_overheads(benchmark_directory):
    overhead = []
    elapsed_times = []
    overhead_percentage = []

    # we are in specific benchmark 
    for iteration_dir in glob.glob(os.path.join(benchmark_directory, '*')):
        overhead_file = iteration_dir + '/overhead.txt'
        try:
            with open(f'{overhead_file}', 'r') as file:
                for line in file:
                    if 'FINAL' in line:
                        pattern = r"(\d+\.\d+)"

                        # Find all matches in the string
                        matches = re.findall(pattern, line)

                        # Extract the values
                        numa_overhead = float(matches[0]) if matches else None
                        total_time = float(matches[1]) if len(matches) > 1 else None
                        percentage = float(matches[2]) if len(matches) > 2 else None

                        overhead.append(numa_overhead)
                        elapsed_times.append(total_time)
                        overhead_percentage.append(percentage)
        except FileNotFoundError:
            print(f"File {overhead_file} does not exist\n")
    # we need a list of TIDs that we are interested in for filtering purposes
    # print(overhead)
    # print(elapsed_times)
    # print(overhead_percentage)
    with open(f'{benchmark_directory}/../total_overhead.txt', 'a') as file:
        if len(overhead) == 0 or len(elapsed_times) == 0 or len(overhead_percentage) == 0:
            return
        bench = os.path.basename(benchmark_directory)
        file.write(f"For {bench} [Min, Max, Mean, Median, Stdev]\n")
        file.write(f"Time in NUMA: {[min(overhead), max(overhead), statistics.mean(overhead), statistics.median(overhead), statistics.stdev(overhead)]}\n")
        file.write(f"Time in Total: {[min(elapsed_times), max(elapsed_times), statistics.mean(elapsed_times), statistics.median(elapsed_times), statistics.stdev(elapsed_times)]}\n")
        file.write(f"Overhead %: {[min(overhead_percentage), max(overhead_percentage), statistics.mean(overhead_percentage), statistics.median(overhead_percentage), statistics.stdev(overhead_percentage)]}\n")
        file.write(f"\n")


def main():
    # Directory containing the iteration directories
    base_directory = os.path.join('/mydata/results/')

    benchmarks = glob.glob(os.path.join(base_directory, '*'))

    for benchmark_directory in benchmarks:
        if not os.path.isdir(benchmark_directory):
            continue
        process_overheads(benchmark_directory)

if __name__ == '__main__':
    main()
