import os
import glob
import argparse
import re
import statistics
from collections import OrderedDict, defaultdict
import pandas as pd

def collect_data(iteration_dir):
    for sub_dir in glob.glob(os.path.join(iteration_dir, '*')):
        # sub_dir == baseline in this case
        file_list = glob.glob(os.path.join(sub_dir, '*_res.txt'))
        with open(iteration_dir + '/../results.txt', 'a') as file:
            file.write("=================================================================\n")
            file.write(iteration_dir.split('/')[-1])
            file.write("\n")
            
        for res_file in file_list:
            with open(res_file, 'r') as f:
                lines = f.readlines()
                data = lines[-22:]
                with open(iteration_dir + '/../results.txt', 'a') as file:
                    file.write(res_file.split('/')[-1])
                    file.write("\n")
                    for line in data:
                        if "0x" in line:
                            continue
                        file.write(line)
                    file.write("\n")

                
                

def main():
    # Parse command line arguments
    # Argument here represents iteration directory
    parser = argparse.ArgumentParser(description='Read all text files in a given iteration directory.')
    parser.add_argument('benchmark', type=str, help='Benchmark Name')
    args = parser.parse_args()

    # Directory containing the iteration directories
    base_directory = os.path.join('/mydata/results/', args.benchmark)

    # with open(base_directory + '/results.txt', 'a') as file:
        # file.write("START\n")

    for iteration_directory in glob.glob(os.path.join(base_directory, 'iteration_*')):
        if not os.path.isdir(iteration_directory):
            print(f'Directory {iteration_directory} does not exist.')
            return
        # Read files in the specified iteration directory
        collect_data(iteration_directory)
#    for k,v in results.items():
#        stats[k] = [min(v), max(v), statistics.median(v), statistics.mean(v), statistics.stdev(v)]
#
#    df = pd.DataFrame.from_dict(stats, orient='index', columns=['min', 'max', 'median', 'mean', 'stdev'])
#    df = df.sort_index()
#    file = f'/mydata/results/{args.benchmark}/df.txt'
#    with open(file, 'a') as f:
#        f.write(df.to_string(index=True))
#        f.write('\n\n')


if __name__ == '__main__':
    main()
