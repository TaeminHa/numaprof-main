#!/bin/bash

# Define the list of benchmarks
benchmarks=(
    # bad-altstack
    # bigheap
    # brk
    # dev-shm
    # env
    # madvise
    # malloc
    # mlock
    # mmap
    # mmapaddr
    # mmapfixed
    # mmapfork
    # mmaphuge
    # mmapmany
    # mremap
    # msync
    # munmap
    # pageswap
    # physpage
    # shm
    # shm-sysv
    # stack
    # stackmmap
    # swap
    # tmpfs
    # userfaultfd
    # vm
    # vm-addr
    # vm-rw
    # vm-segv
    # vm-splice
    
    # "500.perlbench_r"
    # "503.bwaves_r"
    # "505.mcf_r"
    # "507.cactuBSSN_r"
    # "508.namd_r"
    # "510.povray_r"
    # "511.povray_r"
    # "519.lbm_r"
    # "520.omnetpp_r"
    # "521.wrf_r"
    # "523.xalancbmk_r"
    # "525.x264_r"
    # "526.blender_r"
    # "527.cam4_r"
    # "531.deepsjeng_r"
    # "538.imagick_r"
    # "541.leela_r"
    # "544.nab_r"
    # "548.exchange2_r"
    # "549.fotonik3d_r"
    # "554.roms_r"
    # "557.xz_r"
    # "603.bwaves_s"
    # "605.mcf_s"
    # "619.lbm_s"
    # "620.omnetpp_s"
    # "621.wrf_s"
    # "623.xalancbmk_s"
    # "625.x264_s"
    # "631.deepsjeng_s"
    # "638.imagick_s"
    # "641.leela_s"
    "657.xz_s" # ~15GB
    "654.roms_s"
    "649.fotonik3d_s"
    "648.exchange2_s"
    "644.nab_s"
)

finished_benchs=0

start_time=$(date +"%Y-%m-%d %H:%M:%S")

# Iterate over the benchmarks and execute the command
for benchmark in "${benchmarks[@]}"; do    
    start_time_bench=$(date +"%Y-%m-%d %H:%M:%S")
    
    /users/taeminha/numaprof/run_test.sh "$benchmark"
    finished_benchs=$((finished_benchs + 1))
    
    end_time_bench=$(date +"%Y-%m-%d %H:%M:%S") 
    echo -e "Finished Running $benchmark\n$start_time_bench ~ $end_time_bench\n$finished_benchs of 37" | mail -s "Finished Running $benchmark" taemin.ha@utexas.edu
    python3 /users/taeminha/numaprof/print_result.py $benchmark
done

# python3 /users/taeminha/numaprof/process_overhead.py

end_time=$(date +"%Y-%m-%d %H:%M:%S")
echo -e "Start: $start_time \nEnd: $end_time" | mail -s "Finished Running All Iteration" taemin.ha@utexas.edu

