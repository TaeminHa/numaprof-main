values=(20000 30000 40000 50000 60000)
scan_period_max_value=(50000 40000 30000 20000 1000)
scan_size_value=(64 128 256 512 1024)
msns_threshold=(1 2 3 5 6 7 8 9 10)
active_node_fraction=(1 2 4 5 6 7 8 9 10)
mem_distribution_threshold=(1 2 4)
task_migrate_interval=(128 256 512 2048)
period_adjust_threshold=(1 2 3 4 5 6 8 9 10)

# print current proc values
print_proc_vals() {
   printf "SYSCTL_NUMA_BALANCING_SCAN_PERIOD_MIN               %s\n" "$(cat /proc/sys/kernel/numa_balancing_scan_period_min)" >> results.txt 
   printf "SYSCTL_NUMA_BALANCING_SCAN_PERIOD_MAX               %s\n" "$(cat /proc/sys/kernel/numa_balancing_scan_period_max)" >> results.txt 
   printf "SYSCTL_NUMA_BALANCING_SCAN_SIZE                     %s\n" "$(cat /proc/sys/kernel/numa_balancing_scan_size)" >> results.txt
   printf "SYSCTL_NUMA_BALANCING_MSNS_THRESHOLD                %s\n" "$(cat /proc/sys/kernel/numa_balancing_msns_threshold)" >> results.txt
   printf "SYSCTL_NUMA_BALANCING_ACTIVE_NODE_FRACTION          %s\n" "$(cat /proc/sys/kernel/numa_balancing_active_node_fraction)" >> results.txt
   printf "SYSCTL_NUMA_BALANCING_MEM_DISTRIBUTION_THRESHOLD    %s\n" "$(cat /proc/sys/kernel/numa_balancing_mem_distribution_threshold)" >> results.txt 
   printf "SYSCTL_NUMA_BALANCING_TASK_MIGRATE_INTERVAL         %s\n" "$(cat /proc/sys/kernel/numa_balancing_task_migrate_interval)" >> results.txt
   printf "SYSCTL_NUMA_BALANCING_SCAN_PERIOD_ADJUST_THRESHOLD  %s\n" "$(cat /proc/sys/kernel/numa_balancing_scan_period_adjust_threshold)" >> results.txt
}

# Randomly assign values to systemctl variables
configure_random() {
    echo $(shuf -e "${values[@]}" -n 1) > /proc/sys/kernel/numa_balancing_scan_period_min
    echo 60000 > /proc/sys/kernel/numa_balancing_scan_period_max
    echo $(shuf -e "${scan_size_value[@]}" -n 1)  > /proc/sys/kernel/numa_balancing_scan_size
    echo $(shuf -e "${msns_threshold[@]}" -n 1) > /proc/sys/kernel/numa_balancing_msns_threshold
    echo $(shuf -e "${active_node_fraction[@]}" -n 1) > /proc/sys/kernel/numa_balancing_active_node_fraction
    echo $(shuf -e "${mem_distribution_threshold[@]}" -n 1) > /proc/sys/kernel/numa_balancing_mem_distribution_threshold
    echo $(shuf -e "${task_migrate_interval[@]}" -n 1) > /proc/sys/kernel/numa_balancing_task_migrate_interval
    echo $(shuf -e "${period_adjust_threshold[@]}" -n 1) > /proc/sys/kernel/numa_balancing_scan_period_adjust_threshold
}

# Restore default NUMA default settings
restore_default() {
    echo 1000 > /proc/sys/kernel/numa_balancing_scan_period_min
    echo 60000 > /proc/sys/kernel/numa_balancing_scan_period_max
    echo 256 > /proc/sys/kernel/numa_balancing_scan_size
    echo 4 > /proc/sys/kernel/numa_balancing_msns_threshold
    echo 3 > /proc/sys/kernel/numa_balancing_active_node_fraction
    echo 3 > /proc/sys/kernel/numa_balancing_mem_distribution_threshold
    echo 1024 > /proc/sys/kernel/numa_balancing_task_migrate_interval
    echo 7 > /proc/sys/kernel/numa_balancing_scan_period_adjust_threshold
}

run_test() {
    # delete output.txt because it's too big
    # rm /users/taeminha/numaprof/build/output.txt
    # pipe mem access patterns to output.txt file
    # /users/taeminha/numaprof/build/bin/numaprof 
    # mpiexec --allow-run-as-root -n 16 /users/taeminha/numaprof/build/benchmarks/mg.C.x >> results.txt
    # mpiexec --allow-run-as-root -n 16 /users/taeminha/numaprof/build/benchmarks/mg.C.x >> /users/taeminha/numaprof/build/output.txt
    /users/taeminha/numaprof/build/bin/numaprof /users/taeminha/numaprof/build/benchmarks/mosaic/1-gem5-mosaic/apps/gups-app/gups >> /users/taeminha/numaprof/build/output.txt
    # count # of remote accesses and pipe to results.txt
    echo >> results.txt
    python3 /users/taeminha/numaprof/build/print_result.py >> results.txt
    # remove webview file created by numaprof
    rm /users/taeminha/numaprof/build/numaprof-*
}

# remove previous experiment's result
rm results.txt

for i in {1..5}; do
    echo ITERATION $i >> results.txt
    echo >> results.txt
    # rm /users/taeminha/numaprof/build/results.txt
    # Run the baseline test with default values for comparison
    restore_default
    echo TEST: BASELINE >> results.txt
    run_test
    echo >> results.txt

    # Modifying numa_balancing_scan_period_min 

    # Loop through each value and echo it into the file
    echo TEST: SYSCTL_NUMA_BALANCING_SCAN_PERIOD_MIN >> results.txt
    for value in "${values[@]}"; do
        echo $value > /proc/sys/kernel/numa_balancing_scan_period_min
        # print_proc_vals
        echo $value >> results.txt
        run_test
    done

    restore_default
    echo >> results.txt
    echo TEST: SYSCTL_NUMA_BALANCING_SCAN_PERIOD_MAX >> results.txt
    for value in "${scan_period_max_value[@]}"; do
        echo $value > /proc/sys/kernel/numa_balancing_scan_period_max
        # print_proc_vals
        run_test
    done

    restore_default
    echo >> results.txt
    echo TEST: SYSCTL_NUMA_BALANCING_SCAN_SIZE >> results.txt
    for value in "${scan_size_value[@]}"; do
        echo $value > /proc/sys/kernel/numa_balancing_scan_size
        # print_proc_vals
        run_test
    done

    restore_default
    echo >> results.txt
    echo TEST: SYSCTL_NUMA_BALANCING_MSNS_THRESHOLD >> results.txt
    for value in "${msns_threshold[@]}"; do
        echo $value > /proc/sys/kernel/numa_balancing_msns_threshold
        # print_proc_vals
        run_test
    done

    restore_default
    echo >> results.txt
    echo TEST: SYSCTL_NUMA_BALANCING_ACTIVE_NODE_FRACTION >> results.txt
    for value in "${active_node_fraction[@]}"; do
        echo $value > /proc/sys/kernel/numa_balancing_active_node_fraction
        # print_proc_vals
        run_test
    done

    restore_default
    echo >> results.txt
    echo TEST: SYSCTL_NUMA_BALANCING_MEM_DISTRIBUTION_THRESHOLD >> results.txt
    for value in "${mem_distribution_threshold[@]}"; do
        echo $value > /proc/sys/kernel/numa_balancing_mem_distribution_threshold
        # print_proc_vals
        run_test
    done

    restore_default
    echo >> results.txt
    echo TEST: SYSCTL_NUMA_BALANCING_TASK_MIGRATE_INTERVAL >> results.txt
    for value in "${task_migrate_interval[@]}"; do
        echo $value > /proc/sys/kernel/numa_balancing_task_migrate_interval
        # print_proc_vals
        run_test
    done

    restore_default
    echo >> results.txt
    echo TEST: SYSCTL_NUMA_BALANCING_SCAN_PERIOD_ADJUST_THRESHOLD >> results.txt
    for value in "${period_adjust_threshold[@]}"; do
        echo $value > /proc/sys/kernel/numa_balancing_scan_period_adjust_threshold
        # print_proc_vals
        run_test
    done
done

python3 postprocess.py >> stats.txt
# restore_default
# for i in {1..10}
# do
#    echo =========================================================== >> results.txt
#    echo TEST $i >> results.txt
#    configure_random
#    print_proc_vals
#    run_test
#    echo =========================================================== >> results.txt
#    echo >> results.txt
# done
