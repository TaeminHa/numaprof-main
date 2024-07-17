import os
import glob
import argparse
import re
import statistics
from collections import defaultdict

local_accesses = []
remote_accesses = []
times = []
page_migration_tracker = defaultdict(lambda: defaultdict(list))
page_access_tracker = defaultdict(lambda: defaultdict(int))

def read_files_in_directory(directory):
    iteration = directory.split('/')[-1][-1]
    print(f"Iteration {iteration}\n")
    local_count = 0
    remote_count = 0

    file_list = glob.glob(os.path.join(directory, '*'))
    for file_path in file_list:
        if os.path.isfile(file_path):
            print(f"Processing {file_path}")
            with open(file_path, 'r') as file:
                lines = file.readlines()
                for line in lines:
                    if file_path.split('/')[-1] == 'time.time':
                        times.append(float(line))
                        continue
                    if '-' in line:
                        continue
                    if line[0] == 'R':
                        remote_count += 1
                    else:
                        local_count += 1
                    page_addr = line[3:]
                    if len(page_migration_tracker[iteration][page_addr]) == 0 or page_migration_tracker[iteration][page_addr][-1] != line[2]:
                        page_migration_tracker[iteration][page_addr].append(line[2])
                    page_access_tracker[iteration][page_addr] += 1

    local_accesses.append(local_count)
    remote_accesses.append(remote_count)

def main():
    parser = argparse.ArgumentParser(description='Read all text files in a given iteration directory.')
    parser.add_argument('benchmark', type=str, help='Benchmark Name')
    args = parser.parse_args()

    base_directory = os.path.join('/mydata/results/', args.benchmark)

    for iteration_directory in glob.glob(os.path.join(base_directory, '*')):
        if not os.path.isdir(iteration_directory):
            continue
        read_files_in_directory(iteration_directory)

    remote_access_percentage = [remote_accesses[i] / (remote_accesses[i] + local_accesses[i]) for i in range(len(remote_accesses))]

    mem_access_stats = [
        min(remote_access_percentage),
        max(remote_access_percentage),
        statistics.median(remote_access_percentage),
        statistics.mean(remote_access_percentage),
        statistics.stdev(remote_access_percentage)
    ]

    num_migrations_per_iteration = [
        sum(len(page_migration_tracker[str(iteration)][page_addr]) for page_addr in page_migration_tracker[str(iteration)])
        for iteration in range(len(remote_accesses))
    ]
    page_migration_stats = [
        min(num_migrations_per_iteration),
        max(num_migrations_per_iteration),
        statistics.median(num_migrations_per_iteration),
        statistics.mean(num_migrations_per_iteration),
        statistics.stdev(num_migrations_per_iteration)
    ]
    time_stats = [
        min(times),
        max(times),
        statistics.median(times),
        statistics.mean(times),
        statistics.stdev(times)
    ]

    print(mem_access_stats)
    print(page_migration_stats)
    print(time_stats)

    output_file = '/mydata/results/mem_access_to_time.txt'
    with open(output_file, 'a') as f:
        f.write(f'{args.benchmark}\n')
        f.write(f'{mem_access_stats}\n')
        f.write(f'{page_migration_stats}\n')
        f.write(f'{time_stats}\n\n')
if __name__ == '__main__':
    main()
