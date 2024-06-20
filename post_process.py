import os
import glob
import argparse
import re
import statistics
import threading
from itertools import combinations, chain
from collections import OrderedDict, defaultdict
import pandas as pd

# Create a default dict that'll store key = page_addr; value = list of pairs where pair = (address_indices, page_node)
# page_dict = defaultdict(list)
# access_counter_per_page = defaultdict(list)
# switch_counter_per_page = defaultdict(list)
# nid_of_page = defaultdict(list)

def read_files_in_directory(directory):
    # We're currently in iteration directory /mydata/results/benchmark/iteration_x/
    print(directory.split('/')[-1])

    # sub-dir represents our different parameter modification
    for sub_dir in glob.glob(os.path.join(directory, '*')):
        thread_migration_ratio = []
        page_migration_ratio = []
        remote_mem_access_ratio = []
        local_mem_access_ratio = []
        # create a map of tid : list of pages it accesses
        thread_to_pages = defaultdict(set)

        if os.path.isdir(sub_dir):
            # Get the list of all output text files in the subdirectory (which is per-thread file)
            file_list = glob.glob(os.path.join(sub_dir, 'output_*.txt'))
            for file_path in file_list:
                # Check if the path is a file (not a directory)
                if os.path.isfile(file_path):
                    tid = ""
                    find= re.search(r'output_(\d+)\.txt', file_path)
                    if find:
                        tid = find.group(1)
                    # print(tid) 
                    access_counter_per_page = defaultdict(lambda: defaultdict(int, OrderedDict()))
                    switch_counter_per_page = defaultdict(int, OrderedDict())
                    nid_of_page = defaultdict(int, OrderedDict())
                    
                    # this is to see the ratio of residency of thread at each node (i.e. Node 0: 20%, Node 1: 80%)
                    thread_nid_residency = defaultdict(lambda: defaultdict(int, OrderedDict())) 
                    switch_counter_thread = 0
                    nid_of_thread = 0
                    idx = 0 
                    # Open and read the per thread file
                    with open(file_path, 'r') as file:
                        print(file_path)
                        remote_access_count = 0
                        local_access_count = 0

                        for line in file:
                            mem_addrs = line.strip().split(',')
                            for addr in mem_addrs:
                                if len(addr) < 3:
                                    # print(f"Abnormal ADDR: {addr}") 
                                    continue
                                thread_location = int(addr[-2])
                                page_location = int(addr[-1])
                                page_addr = addr[:-2]

                                thread_to_pages[tid].add(page_addr)

                                if page_addr[-1] == "-":
                                    # print(f"Weird Addr: {page_addr}")
                                    continue 
                                if page_location == thread_location:
                                    local_access_count += 1
                                    thread_nid_residency[thread_location][0] += 1
                                else:
                                    remote_access_count += 1
                                    thread_nid_residency[thread_location][1] += 1
                                
                                if idx == 0:
                                    nid_of_thread = thread_location
                                    idx = -1

                                access_counter_per_page[page_addr][page_location] += 1
                                # update data map
                                if page_addr in nid_of_page:
                                    if nid_of_page[page_addr] != page_location:
                                        switch_counter_per_page[page_addr] += 1
                                nid_of_page[page_addr] = page_location
                                
                                if nid_of_thread != thread_location:
                                    switch_counter_thread += 1
                                    nid_or_thread = thread_location

                    # we finished collecting stat for specific thread file
                    resfile = sub_dir + '/' + tid + '_res.txt'
                    total_memory_access = 0
                    for nid in access_counter_per_page.values():
                        total_memory_access += sum(nid.values())
                    
                    thread_migration_ratio.append(100 * switch_counter_thread / total_memory_access)
                    page_migration_ratio.append(sum(switch_counter_per_page.values()) / total_memory_access)
                    remote_mem_access_ratio.append(remote_access_count * 100 / (remote_access_count + local_access_count))
                    local_mem_access_ratio.append(local_access_count * 100 / (local_access_count + remote_access_count))
                    
                    with open(resfile, 'a') as file:
                        for page,access_per_nid in access_counter_per_page.items():
                            file.write(f"Page {page} Migration%: {100 * switch_counter_per_page[page] / sum(access_per_nid.values())}; # Migration: {switch_counter_per_page[page]}; # Access: {sum(access_per_nid.values())}; # Node 0: {access_per_nid[0]} ({100 * access_per_nid[0] / (access_per_nid[0] + access_per_nid[1])}%); # Node 1: {access_per_nid[1]} ({100 * access_per_nid[1] / (access_per_nid[0] + access_per_nid[1])}%)\n")
                        file.write("\n")
                        file.write(f"# Thread Migration: {switch_counter_thread}\n")  
                        file.write(f"% Thread Migration: {100 * switch_counter_thread / total_memory_access}\n")
                        file.write("\n")
                        file.write(f"# Mem Access: {total_memory_access}\n")
                        file.write(f"# of Pages: {len(nid_of_page)}\n")
                        file.write(f"# of Page Migration: {sum(switch_counter_per_page.values())}\n")
                        file.write(f"% of Page Migration: {sum(switch_counter_per_page.values()) / total_memory_access}\n")
                        file.write("\n")
                        file.write(f"# of Remote Mem Access: {remote_access_count}\n")
                        file.write(f"% of Remote Mem Access: {remote_access_count * 100 / (remote_access_count + local_access_count)}\n")
                        file.write(f"# of Local Mem Access: {local_access_count}\n")
                        file.write(f"% of Local Mem Access: {local_access_count * 100 / (local_access_count + remote_access_count)}\n")
                        file.write("\n")
                        if sum(thread_nid_residency[0].values()) == 0:
                            file.write("NO ACCESS FROM NODE 0\n")
                        else: 
                            file.write(f"# of Remote Access from Node 0: {thread_nid_residency[0][1]}\n")
                            file.write(f"% of Remote Access from Node 0: {100 * thread_nid_residency[0][1] / sum(thread_nid_residency[0].values())}\n")
                            file.write(f"# of Local Access from Node 0: {thread_nid_residency[0][0]}\n")
                            file.write(f"% of Local Access from Node 0: {100 * thread_nid_residency[0][0] / sum(thread_nid_residency[0].values())}\n")
                        file.write("\n")

                        if sum(thread_nid_residency[1].values()) == 0: 
                            file.write("NO ACCESS FROM NODE 1\n")
                        else:            
                            file.write(f"# of Remote Access from Node 1: {thread_nid_residency[1][1]}\n")
                            file.write(f"% of Remote Access from Node 1: {100 * thread_nid_residency[1][1] / sum(thread_nid_residency[1].values())}\n")
                            file.write(f"# of Local Access from Node 1: {thread_nid_residency[1][0]}\n")
                            file.write(f"% of Local Access from Node 1: {100 * thread_nid_residency[1][0] / sum(thread_nid_residency[1].values())}\n")
            
            
        shared_pages = {}
        thread_combinations = chain.from_iterable(combinations(thread_to_pages.keys(), r) for r in range(2, len(thread_to_pages) + 1))

        for comebo in thread_combinations:
            shared_page = set.intersection(*(thread_to_pages[tid] for tid in combo))
            shared_pages[combo] = shared_page

        private_pages = {}
        for tid, pages in thread_to_pages.items():
            other_pages_union = set().union(*(thread_to_pages[other_tid] for other_tid in thread_to_pages if other_tid != tid))
            private_pages[tid] = pages - other_pages_union

        with open(sub_dir + '/shared_pages.txt', 'a') as file:
            for thread_pair, shared_pages in shared_pages.items():
                file.write(f"{thread_pair}\n")
                for shared_page in shared_pages:
                    file.write(f"{shared_page}\n")
                file.write(f"\n")

            file.write("Private Pages:\n")
            for tid, private_page_set in private_pages.items():
                file.write(f"{tid}\n")
                for page in private_page_set:
                    file.write(f"{page}\n")
                file.write(f"\n")
 
        thread_migration_stat = [min(thread_migration_ratio), max(thread_migration_ratio), statistics.mean(thread_migration_ratio), statistics.median(thread_migration_ratio), statistics.stdev(thread_migration_ratio)]
        page_migration_stat = [min(page_migration_ratio), max(page_migration_ratio), statistics.mean(page_migration_ratio), statistics.median(page_migration_ratio), statistics.stdev(page_migration_ratio)]
        remote_mem_access_stat = [min(remote_mem_access_ratio), max(remote_mem_access_ratio), statistics.mean(remote_mem_access_ratio), statistics.median(remote_mem_access_ratio), statistics.stdev(remote_mem_access_ratio)]
        local_mem_access_stat = [min(local_mem_access_ratio), max(local_mem_access_ratio), statistics.mean(local_mem_access_ratio), statistics.median(local_mem_access_ratio), statistics.stdev(local_mem_access_ratio)]

        data = [thread_migration_stat, page_migration_stat, remote_mem_access_stat, local_mem_access_stat]
        df = pd.DataFrame(data, columns=['min', 'max', 'mean', 'median', 'stdev'])
        file = sub_dir + '/df.txt'
        with open(file, 'a') as f:
            f.write("Thread Migration, Page Migration, Remote Mem Access, Local Mem Access\n")
            f.write(df.to_string())
            f.write("\n")


def main():
    # Parse command line arguments
    # Argument here represents iteration directory
    parser = argparse.ArgumentParser(description='Read all text files in a given iteration directory.')
    parser.add_argument('benchmark', type=str, help='Benchmark Name')
    args = parser.parse_args()

    # Directory containing the iteration directories
    base_directory = os.path.join('/mydata/results/', args.benchmark)
    
    iteration_directories = glob.glob(os.path.join(base_directory, '*'))
    # threads = []

    for iteration_directory in iteration_directories:
        if not os.path.isdir(iteration_directory):
            print(f'Directory {iteration_directory} does not exist.')
            return
        # thread = threading.Thread(target=read_files_in_directory, args=(iteration_directory,))
        # threads.append(thread)
        # thread.start()

    # for thread in threads:
        # thread.join()
        # Read files in the specified iteration directory
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
