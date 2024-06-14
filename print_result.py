import os
import glob
import argparse

def read_files_in_directory(directory):
    # We're currently in iteration directory /users/taeminha/results/iteration_x/
    
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
            print(f"For {sub_dir} Remote: {remote_count} || {100 * remote_count / (remote_count + local_count)}")
            print(f"For {sub_dir} Local: {local_count} || {100 * local_count / (remote_count + local_count)}")
                    

def main():
    # Parse command line arguments
    # Argument here represents iteration directory
    parser = argparse.ArgumentParser(description='Read all text files in a given iteration directory.')
    parser.add_argument('benchmark', type=str, help='Benchmark Name')
    parser.add_argument('iteration', type=int, help='Iteration number')
    args = parser.parse_args()

    # Directory containing the iteration directories
    base_directory = os.path.join('/users/taeminha/results/', args.benchmark)
    # Directory for the specified iteration
    iteration_directory = os.path.join(base_directory, f'iteration_{args.iteration}')

    # Check if the iteration directory exists
    if not os.path.isdir(iteration_directory):
        print(f'Directory {iteration_directory} does not exist.')
        return

    # Read files in the specified iteration directory
    read_files_in_directory(iteration_directory)

if __name__ == '__main__':
    main()
