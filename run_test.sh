#!/bin/bash

values=(20000 30000 40000 50000 60000)
scan_period_max_value=(50000 40000 30000 20000 1000)
scan_size_value=(64 128 256 512 1024)
msns_threshold=(1 2 3 5 6 7 8 9 10)
active_node_fraction=(1 2 4 5 6 7 8 9 10)
mem_distribution_threshold=(1 2 4)
task_migrate_interval=(128 256 512 2048)
period_adjust_threshold=(1 2 3 4 5 6 8 9 10)

nsa_bench=(bt.D.x cg.D.x dt.D.x ep.D.x ft.D.x is.D.x lu.D.x mg.D.x sp.D.x)

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
    local i=$1
    local version=$2
    local bench=$3

    mpiexec --allow-run-as-root -np 16 /users/taeminha/NPB3.4.3/NPB3.4-MPI/bin/$bench >> /mydata/results/$bench/$version/iteration_$i/out.txt
}

move_output() {
    local i=$1
    local version=$2
    local bench=$3

    mv /mydata/results/output_* /mydata/results/$bench/iteration_$i/$version
}

rm -rf /mydata/results
mkdir /mydata/results

for benchmark in "${nsa_bench[@]}"; do
    mkdir /mydata/results/$benchmark
    mkdir /mydata/results/$benchmark/baseline

    for i in {1..5}; do
        
        echo ITERATION $i FOR $benchmark
        restore_default

        echo TEST: BASELINE
        mkdir /mydata/results/$benchmark/baseline/iteration_$i
        run_test $i baseline $benchmark


        # Loop through each value and echo it into the file
        echo TEST: SYSCTL_NUMA_BALANCING_SCAN_PERIOD_MIN
        for value in "${values[@]}"; do
            echo PERIOD_MIN_$value
            echo $value > /proc/sys/kernel/numa_balancing_scan_period_min
            # print_proc_vals
            mkdir /mydata/results/$benchmark/numa_balancing_scan_period_min_$value
            mkdir /mydata/results/$benchmark/numa_balancing_scan_period_min_$value/iteration_$i

            run_test $i numa_balancing_scan_period_min_$value $benchmark
        done

        restore_default
        
        echo TEST: SYSCTL_NUMA_BALANCING_SCAN_PERIOD_MAX
        for value in "${scan_period_max_value[@]}"; do
            echo $value > /proc/sys/kernel/numa_balancing_scan_period_max
            # print_proc_vals
            mkdir /mydata/results/$benchmark/numa_balancing_scan_period_max_$value
            mkdir /mydata/results/$benchmark/numa_balancing_scan_period_max_$value/iteration_$i
            run_test $i numa_balancing_scan_period_max_$value $benchmark
        done

        restore_default
        
        echo TEST: SYSCTL_NUMA_BALANCING_SCAN_SIZE
        for value in "${scan_size_value[@]}"; do
            echo $value > /proc/sys/kernel/numa_balancing_scan_size
            mkdir /mydata/results/$benchmark/numa_balancing_scan_size_$value
            mkdir /mydata/results/$benchmark/numa_balancing_scan_size_$value/iteration_$i
            run_test $i numa_balancing_scan_size_$value $benchmark
            # print_proc_vals
        done

        restore_default

        echo TEST: SYSCTL_NUMA_BALANCING_MSNS_THRESHOLD
        for value in "${msns_threshold[@]}"; do
            echo $value > /proc/sys/kernel/numa_balancing_msns_threshold
            mkdir /mydata/results/$benchmark/numa_balancing_msns_threshold_$value
            mkdir /mydata/results/$benchmark/numa_balancing_msns_threshold_$value/iteration_$i
            run_test $i numa_balancing_msns_threshold_$value $benchmark
            # print_proc_vals
        done

        restore_default
        echo TEST: SYSCTL_NUMA_BALANCING_ACTIVE_NODE_FRACTION
        for value in "${active_node_fraction[@]}"; do
            echo $value > /proc/sys/kernel/numa_balancing_active_node_fraction    
            mkdir /mydata/results/$benchmark/numa_balancing_active_node_fraction_$value
            mkdir /mydata/results/$benchmark/numa_balancing_active_node_fraction_$value/iteration_$i
            run_test $i numa_balancing_active_node_fraction_$value $benchmark
        done

        restore_default

        echo TEST: SYSCTL_NUMA_BALANCING_MEM_DISTRIBUTION_THRESHOLD
        for value in "${mem_distribution_threshold[@]}"; do
            echo $value > /proc/sys/kernel/numa_balancing_mem_distribution_threshold
            mkdir /mydata/results/$benchmark/numa_balancing_mem_distribution_threshold_$value 
            mkdir /mydata/results/$benchmark/numa_balancing_mem_distribution_threshold_$value/iteration_$i
            run_test $benchmark
        done

        restore_default

        echo TEST: SYSCTL_NUMA_BALANCING_TASK_MIGRATE_INTERVAL
        for value in "${task_migrate_interval[@]}"; do
            echo $value > /proc/sys/kernel/numa_balancing_task_migrate_interval
            mkdir /mydata/results/$benchmark/numa_balancing_task_migrate_interval_$value
            mkdir /mydata/results/$benchmark/numa_balancing_task_migrate_interval_$value/iteration_$i
            run_test $i numa_balancing_task_migrate_interval_$value $benchmark
        done

        restore_default

        echo TEST: SYSCTL_NUMA_BALANCING_SCAN_PERIOD_ADJUST_THRESHOLD
        for value in "${period_adjust_threshold[@]}"; do
            echo $value > /proc/sys/kernel/numa_balancing_scan_period_adjust_threshold
            mkdir /mydata/results/$benchmark/numa_balancing_scan_period_adjust_threshold_$value
            mkdir /mydata/results/$benchmark/numa_balancing_scan_period_adjust_threshold_$value/iteration_$i
            run_test $i numa_balancing_scan_period_adjust_threshold_$value $benchmark
        done
    done
done
