#!/bin/bash

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
    local bench=$1
    local iteration=$2

    echo "Executing $bench Iteration $iteration"

    base_command="sudo numactl --cpunodebind 0 --membind 0 python3 /users/taeminha/numaprof/profile_numa_overhead.py $bench /users/taeminha/pin-3.30/pin -t /users/taeminha/pin-3.30/source/tools/ManualExamples/obj-intel64/pinatrace.so -- "
    base_dir="/users/taeminha/spec/benchspec/CPU"

    if [ "$bench" = "500.perlbench_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/perlbench_r_base.taemin_numa-m64
    elif [ "$bench" = "503.bwaves_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/bwaves_r_base.taemin_numa-m64 bwaves_1 < bwaves_1.in
    elif [ "$bench" = "505.mcf_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000 
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/mcf_r_base.taemin_numa-m64 inp.in
    elif [ "$bench" = "507.cactusBSSN_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/cactusBSSN_r_base.taemin_numa-m64 spec_test.par
    elif [ "$bench" = "508.namd_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/namd_r_base.taemin_numa-m64 --input apoa1.input --iterations 1 --output apoa1.test.output
    elif [ "$bench" = "511.povray_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/povray_r_base.taemin_numa-m64 SPEC-benchmark-test.ini
    elif [ "$bench" = "519.lbm_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/lbm_r_base.taemin_numa-m64 20 reference.dat 0 1 100_100_130_cf_a.o
    elif [ "$bench" = "520.omnetpp_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/omnetpp_r_base.taemin_numa-m64 -c General -r 0
    elif [ "$bench" = "523.xalancbmk_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/cpuxalan_r_base.taemin_numa-m64 -v test.xml xalanc.xsl
    elif [ "$bench" = "525.x264_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/x264_r_base.taemin_numa-m64 --dumpyuv 50 --frames 156 -o BuckBunny_New.264 BuckBunny.yuv 1280x720
    elif [ "$bench" = "531.deepsjeng_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/deepsjeng_r_base.taemin_numa-m64 test.txt
    elif [ "$bench" = "538.imagick_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/imagick_r_base.taemin_numa-m64 -limit disk 0 test_input.tga -shear 25 -resize 640x480 -negate -alpha Off test_output.tga
    elif [ "$bench" = "541.leela_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/leela_r_base.taemin_numa-m64 test.sgf
    elif [ "$bench" = "544.nab_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/nab_r_base.taemin_numa-m64 hkrdenq 1930344093 1000
    elif [ "$bench" = "548.exchange2_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/exchange2_r_base.taemin_numa-m64 0
    elif [ "$bench" = "549.fotonik3d_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/fotonik3d_r_base.taemin_numa-m64
    elif [ "$bench" = "554.roms_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/roms_r_base.taemin_numa-m64 < ocean_benchmark0.in.x
    elif [ "$bench" = "557.xz_r" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/xz_r_base.taemin_numa-m64 cpu2006docs.tar.xz 4 055ce243071129412e9dd0b3b69a21654033a9b723d874b2015c774fac1553d9713be561ca86f74e4f16f22e664fc17a79f30caa5ad2c04fbc447549c2810fae 1548636 1555348 0
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/xz_r_base.taemin_numa-m64 cpu2006docs.tar.xz 4 055ce243071129412e9dd0b3b69a21654033a9b723d874b2015c774fac1553d9713be561ca86f74e4f16f22e664fc17a79f30caa5ad2c04fbc447549c2810fae 1462248 -1 1
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/xz_r_base.taemin_numa-m64 cpu2006docs.tar.xz 4 055ce243071129412e9dd0b3b69a21654033a9b723d874b2015c774fac1553d9713be561ca86f74e4f16f22e664fc17a79f30caa5ad2c04fbc447549c2810fae 1428548 -1 2
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/xz_r_base.taemin_numa-m64 cpu2006docs.tar.xz 4 055ce243071129412e9dd0b3b69a21654033a9b723d874b2015c774fac1553d9713be561ca86f74e4f16f22e664fc17a79f30caa5ad2c04fbc447549c2810fae 1034828 -1 3e
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/xz_r_base.taemin_numa-m64 cpu2006docs.tar.xz 4 055ce243071129412e9dd0b3b69a21654033a9b723d874b2015c774fac1553d9713be561ca86f74e4f16f22e664fc17a79f30caa5ad2c04fbc447549c2810fae 1061968 -1 4
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/xz_r_base.taemin_numa-m64 cpu2006docs.tar.xz 4 055ce243071129412e9dd0b3b69a21654033a9b723d874b2015c774fac1553d9713be561ca86f74e4f16f22e664fc17a79f30caa5ad2c04fbc447549c2810fae 1034588 -1 4e
    elif [ "$bench" = "600.perlbench_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/perlbench_s_base.taemin_numa-m64 -I. -I./lib makerand.pl
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/perlbench_s_base.taemin_numa-m64 -I. -I./lib test.pl
    elif [ "$bench" = "603.bwaves_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/speed_bwaves_base.taemin_numa-m64 bwaves_1 < bwaves_1.in
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/speed_bwaves_base.taemin_numa-m64 bwaves_2 < bwaves_2.in
    elif [ "$bench" = "605.mcf_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/mcf_s_base.taemin_numa-m64 inp.in
    elif [ "$bench" = "607.cactuBSSN_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/cactuBSSN_s_base.taemin_numa-m64 spec_test.par
    elif [ "$bench" = "619.lbm_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/lbm_s_base.taemin_numa-m64 20 reference.dat 0 1 200_200_260_ldc.of
    elif [ "$bench" = "620.omnetpp_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/omnetpp_s_base.taemin_numa-m64 -c General -r 0
    elif [ "$bench" = "623.xalancbmk_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/xalancbmk_s_base.taemin_numa-m64 -v test.xml xalanc.xsl
    elif [ "$bench" = "625.x264_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/x264_s_base.taemin_numa-m64 --dumpyuv 50 --frames 156 -o BuckBunny_New.264 BuckBunny.yuv 1280x720
    elif [ "$bench" = "631.deepsjeng_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/deepsjeng_s_base.taemin_numa-m64 test.txt
    elif [ "$bench" = "638.imagick_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/imagick_s_base.taemin_numa-m64 -limit disk 0 test_input.tga -shear 25 -resize 640x480 -negate -alpha Off test_output.tga
    elif [ "$bench" = "641.leela_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/leela_s_base.taemin_numa-m64 test.sgf
    elif [ "$bench" = "644.nab_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/nab_s_base.taemin_numa-m64 hkrdenq 1930344093 1000
    elif [ "$bench" = "648.exchange2_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/exchange2_s_base.taemin_numa-m64 0
    elif [ "$bench" = "649.foronik3d_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/fotonik3d_s_base.taemin_numa-m64
    elif [ "$bench" = "654.roms_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/sroms_base.taemin_numa-m64 < ocean_benchmark0.in
    elif [ "$bench" = "657.xz_s" ]; then
        cd $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000 
        $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/xz_s_base.taemin_numa-m64 cpu2006docs.tar.xz 4 055ce243071129412e9dd0b3b69a21654033a9b723d874b2015c774fac1553d9713be561ca86f74e4f16f22e664fc17a79f30caa5ad2c04fbc447549c2810fae 1548636 1555348 0
        # echo $base_command $base_dir/$bench/run/run_base_test_taemin_numa-m64.0000/xz_s_base.taemin_numa-m64 cpu2006docs.tar.xz 4 055ce243071129412e9dd0b3b69a21654033a9b723d874b2015c774fac1553d9713be561ca86f74e4f16f22e664fc17a79f30caa5ad2c04fbc447549c2810fae 1548636 1555348 0
    else
        cd /users/taeminha/numaprof
        python3 profile_numa_overhead.py $bench stress-ng --$bench 1 -t 60 
    fi
}

move_output() {
    local i=$1
    local version=$2
    local bench=$3
    # mv /mydata/results/$bench/overhead.txt /mydata/results/$bench/iteration_$i/
    mv /mydata/results/pinatrace/* /mydata/results/$bench/iteration_$i/
    
    # mv /mydata/results/$bench/iteration_$i/traces.txt /mydata/results/$bench/iteration_$i/$version
    # mv /mydata/results/output_* /mydata/results/$bench/iteration_$i/$version
    # mv /mydata/results/$bench/iteration_$i/post_process.txt /mydata/results/$bench/iteration_$i/$version
}


# get start time
# start_time=$(date +"%Y-%m-%d %H:%M:%S")


mkdir /mydata/results
benchmark=$1
rm -rf /mydata/results/$benchmark
mkdir /mydata/results/$benchmark
for i in {1..10}; do
    mkdir /mydata/results/$benchmark/iteration_$i
    cd /mydata/results/$benchmark/iteration_$i
    rm /mydata/results/$benchmark/iteration_$i/numaprof-*
    
    echo ITERATION $i FOR $benchmark
    # rm /users/taeminha/numaprof/build/results.txt
    # Run the baseline test with default values for comparison
    restore_default

    echo TEST: BASELINE
    mkdir baseline
    run_test $benchmark $i
    move_output $i baseline $benchmark

    # This is where we process the traces.py file but I need to see the output first

    # Modifying numa_balancing_scan_period_min 

    # Loop through each value and echo it into the file
    # echo TEST: SYSCTL_NUMA_BALANCING_SCAN_PERIOD_MIN - Iteration $i
    # for value in "${values[@]}"; do
    #     echo PERIOD_MIN_$value
    #     echo $value > /proc/sys/kernel/numa_balancing_scan_period_min
    #     # print_proc_vals
    #     mkdir /mydata/results/$benchmark/iteration_$i/numa_balancing_scan_period_min_$value
    #     run_test $benchmark $i
    #     move_output $i numa_balancing_scan_period_min_$value $benchmark
    # done
    #
    # restore_default
    #
    # echo TEST: SYSCTL_NUMA_BALANCING_SCAN_PERIOD_MAX - Iteration $i
    # for value in "${scan_period_max_value[@]}"; do
    #     echo $value > /proc/sys/kernel/numa_balancing_scan_period_max
    #     # print_proc_vals
    #     mkdir /mydata/results/$benchmark/iteration_$i/numa_balancing_scan_period_max_$value
    #     run_test $benchmark $i
    #     move_output $i numa_balancing_scan_period_max_$value $benchmark
    # done
    #
    # restore_default
    #
    # echo TEST: SYSCTL_NUMA_BALANCING_SCAN_SIZE - Iteration $i
    # for value in "${scan_size_value[@]}"; do
    #     echo $value
    #     echo $value > /proc/sys/kernel/numa_balancing_scan_size
    #     mkdir /mydata/results/$benchmark/iteration_$i/numa_balancing_scan_size_$value
    #     run_test $benchmark $i
    #     move_output $i numa_balancing_scan_size_$value $benchmark
    #     # print_proc_vals
    # done
    #
    # restore_default
    #
    # echo TEST: SYSCTL_NUMA_BALANCING_MSNS_THRESHOLD - Iteration $i
    # for value in "${msns_threshold[@]}"; do
    #     echo $value > /proc/sys/kernel/numa_balancing_msns_threshold
    #     mkdir /mydata/results/$benchmark/iteration_$i/numa_balancing_msns_threshold_$value
    #     run_test $benchmark $i
    #     move_output $i numa_balancing_msns_threshold_$value $benchmark
    #     # print_proc_vals
    # done
    #
    # restore_default
    # echo TEST: SYSCTL_NUMA_BALANCING_ACTIVE_NODE_FRACTION - Iteration $i 
    # for value in "${active_node_fraction[@]}"; do
    #     echo $value > /proc/sys/kernel/numa_balancing_active_node_fraction    
    #     mkdir /mydata/results/$benchmark/iteration_$i/numa_balancing_active_node_fraction_$value
    #     run_test $benchmark $i
    #     move_output $i numa_balancing_active_node_fraction_$value $benchmark
    # done
    #
    # restore_default
    #
    # echo TEST: SYSCTL_NUMA_BALANCING_MEM_DISTRIBUTION_THRESHOLD - Iteration $i
    # for value in "${mem_distribution_threshold[@]}"; do
    #     echo $value > /proc/sys/kernel/numa_balancing_mem_distribution_threshold
    #     mkdir /mydata/results/$benchmark/iteration_$i/numa_balancing_mem_distribution_threshold_$value
    #     run_test $benchmark $i
    #     move_output $i numa_balancing_mem_distribution_threshold_$value $benchmark
    # done
    #
    # restore_default
    #
    # echo TEST: SYSCTL_NUMA_BALANCING_TASK_MIGRATE_INTERVAL - Iteration $i
    # for value in "${task_migrate_interval[@]}"; do
    #     echo $value > /proc/sys/kernel/numa_balancing_task_migrate_interval
    #     mkdir /mydata/results/$benchmark/iteration_$i/numa_balancing_task_migrate_interval_$value
    #     run_test $benchmark $i
    #     move_output $i numa_balancing_task_migrate_interval_$value $benchmark
    # done
    #
    # restore_default
    #
    # echo TEST: SYSCTL_NUMA_BALANCING_SCAN_PERIOD_ADJUST_THRESHOLD - Iteration $i
    # for value in "${period_adjust_threshold[@]}"; do
    #     echo $value > /proc/sys/kernel/numa_balancing_scan_period_adjust_threshold
    #     mkdir /mydata/results/$benchmark/iteration_$i/numa_balancing_scan_period_adjust_threshold_$value
    #     run_test $benchmark $i
    #     move_output $i numa_balancing_scan_period_adjust_threshold_$value $benchmark
    # done
done

rm /mydata/resutls/$benchmark/df.txt
rm /mydata/results/$benchmark/results.txt
# sudo python3 /users/taeminha/numaprof/print_result $benchmark
# sudo python3 /users/taeminha/numaprof/post_process.py $benchmark
#notify completion of job through email
# end_time=$(date +"%Y-%m-%d %H:%M:%S")
# echo -e "Bench: $benchmark \nStart: $start_time \nEnd: $end_time" | mail -s "Finished NUMAprof" taemin.ha@utexas.edu

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
