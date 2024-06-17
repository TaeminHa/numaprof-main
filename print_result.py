import os
import glob
import argparse
import re
import statistics
from collections import OrderedDict, defaultdict
import pandas as pd

results = defaultdict(list, OrderedDict())
stats = defaultdict(list, OrderedDict())

def read_files_in_directory(directory):
    # We're currently in iteration directory /mydata/results/benchmark/iteration_x/
    print(directory.split('/')[-1])
    
    # sub-dir represents our different parameter modification
    for sub_dir in glob.glob(os.path.join(directory, '*')):
        if os.path.isdir(sub_dir):
            remote_count = 0
            local_count = 0

            # Get the list of all text files in the subdirectory (which is per-thread file)
            file_list = glob.glob(os.path.join(sub_dir, '*.txt'))
            for file_path in file_list:
                # Check if the path is a file (not a directory)
                if os.path.isfile(file_path):
                    
                    # Open and read the file
                    with open(file_path, 'r') as file:
                        # Read each line in the file
                        for line in file:
                            remote_count += line.count('R')
                            local_count += line.count('L')
            
            resfile = directory + '/../results.txt'
            with open(resfile, 'a') as file:
                proc_modification = os.path.basename(sub_dir)
                results[proc_modification].append(remote_count * 100 / (remote_count + local_count))
                print(proc_modification)
                file.write(f"{proc_modification}\n")
                file.write(f"For {proc_modification} Remote: {remote_count} || {100 * remote_count / (remote_count + local_count)}\n")
                file.write(f"For {proc_modification} Local: {local_count} || {100 * local_count / (remote_count + local_count)}\n\n")

def main():
    # Parse command line arguments
    # Argument here represents iteration directory
    parser = argparse.ArgumentParser(description='Read all text files in a given iteration directory.')
    parser.add_argument('benchmark', type=str, help='Benchmark Name')
    args = parser.parse_args()

    # Directory containing the iteration directories
    base_directory = os.path.join('/mydata/results/', args.benchmark)
    
    for iteration_directory in glob.glob(os.path.join(base_directory, '*')):
        if not os.path.isdir(iteration_directory):
            print(f'Directory {iteration_directory} does not exist.')
            return
        # Read files in the specified iteration directory
        read_files_in_directory(iteration_directory)
    for k,v in results.items():
        stats[k] = [min(v), max(v), statistics.median(v), statistics.mean(v), statistics.stdev(v)]

    df = pd.DataFrame.from_dict(stats, orient='index', columns=['min', 'max', 'median', 'mean', 'stdev'])
    df = df.sort_index()
    file = f'/mydata/results/{args.benchmark}/df.txt'
    with open(file, 'a') as f:
        f.write(df.to_string(index=True))
        f.write('\n\n')


if __name__ == '__main__':
    main()
