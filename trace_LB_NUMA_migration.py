from bcc import BPF
import time
from collections import defaultdict, OrderedDict
import ctypes as ct
import subprocess
import sys

# Define the BPF program
bpf_program = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

enum migrate_mode {
    MIGRATE_ASYNC,
    MIGRATE_SYNC_LIGHT,
    MIGRATE_SYNC
};

enum migrate_reason {
    COMPACTION,
    MEMORY_FAILURE,
    MEMORY_HOTPLUG,
    SYSCALL_OR_CPUSET,
    MEMPOLICY_MBIND,
    NUMA_MISPLACED,
    CONTIG_RANGE,
    LONGTERM_PIN,
    DEMOTION
};

struct data_t {
    u64 timestamp;
    u32 pid;
    u32 tgid;
    u32 ngid;
    int src_cpu;
    int src_nid;
    int dst_cpu;
    int dst_nid;
};

struct migrate_data_t {
    u64 timestamp;
    char comm[16];
    u32 pid;
    int prio;
    int orig_cpu;
    int dest_cpu;
};

struct page_migrate_data_t {
    u64 timestamp;
    u32 pid;
    unsigned long succeeded;
    unsigned long failed;
    unsigned long thp_succeeded;
    unsigned long thp_failed;
    unsigned long thp_split;
    enum migrate_mode mode;
    enum migrate_reason reason;
    int src_nid;
    int dst_nid;
};

struct swap_numa_data_t {
    u64 timestamp;
    u32 src_pid;
    u32 src_tgid;
    u32 src_ngid;
    int src_cpu;
    int src_nid;
    u32 dst_pid;
    u32 dst_tgid;
    u32 dst_ngid;
    int dst_cpu;
    int dst_nid;
};

struct migrate_pages_start_data_t {
    u32 pid;
    enum migrate_mode mode;
    int reason;
};

struct pte_migrate_data_t {
    u32 pid;
    unsigned long addr;
    unsigned long pte;
    int order;
};

struct alloc_vmap_area_data_t {
    u64 timestamp;
    u32 pid;
    unsigned long addr;
    unsigned long size;
    unsigned long align;
    unsigned long vstart;
    unsigned long vend;
    int failed;
};

struct free_vmap_area_noflush_data_t {
    u64 timestamp;
    u32 pid;
    unsigned long va_start;
    unsigned long nr_lazy;
    unsigned long nr_lazy_max;
};

struct fork_data_t {
    u64 timestamp;
    pid_t parent_pid;
    pid_t child_pid;
    int cpu_id;
};

struct exit_data_t {
    u64 timestamp;
    char comm[16];
    pid_t pid;
    int prio;
};


BPF_PERF_OUTPUT(events);
BPF_PERF_OUTPUT(migrate_events);
BPF_PERF_OUTPUT(page_migrate_events);
BPF_PERF_OUTPUT(swap_numa_events);
BPF_PERF_OUTPUT(migrate_pages_start_events);
BPF_PERF_OUTPUT(alloc_vmap_area_events);
BPF_PERF_OUTPUT(free_vmap_area_events);
BPF_PERF_OUTPUT(process_fork_events);
BPF_PERF_OUTPUT(process_exit_events);

TRACEPOINT_PROBE(sched, sched_move_numa) {
    struct data_t data = {};
    data.timestamp = bpf_ktime_get_ns();
    data.pid = args->pid;
    data.tgid = args->tgid;
    data.ngid = args->ngid;
    data.src_cpu = args->src_cpu;
    data.src_nid = args->src_nid;
    data.dst_cpu = args->dst_cpu;
    data.dst_nid = args->dst_nid;

    events.perf_submit(args, &data, sizeof(data));
    return 0;
}

TRACEPOINT_PROBE(sched, sched_migrate_task) {
    struct migrate_data_t data = {};
    data.timestamp = bpf_ktime_get_ns();
    bpf_probe_read(&data.comm, sizeof(data.comm), args->comm);
    data.pid = args->pid;
    data.prio = args->prio;
    data.orig_cpu = args->orig_cpu;
    data.dest_cpu = args->dest_cpu;

    migrate_events.perf_submit(args, &data, sizeof(data));
    return 0;
}

TRACEPOINT_PROBE(migrate, mm_migrate_pages) {
    struct page_migrate_data_t data = {};
    data.timestamp = bpf_ktime_get_ns();
    data.pid = bpf_get_current_pid_tgid() >> 32;
    data.succeeded = args->succeeded;
    data.failed = args->failed;
    data.thp_succeeded = args->thp_succeeded;
    data.thp_failed = args->thp_failed;
    data.thp_split = args->thp_split;
    data.mode = args->mode;
    data.reason = args->reason;

    page_migrate_events.perf_submit(args, &data, sizeof(data));
    return 0;
}

TRACEPOINT_PROBE(sched, sched_swap_numa) {
    struct swap_numa_data_t data = {};
    data.timestamp = bpf_ktime_get_ns();
    data.src_pid = args->src_pid;
    data.src_tgid = args->src_tgid;
    data.src_ngid = args->src_ngid;
    data.src_cpu = args->src_cpu;
    data.src_nid = args->src_nid;
    data.dst_pid = args->dst_pid;
    data.dst_tgid = args->dst_tgid;
    data.dst_ngid = args->dst_ngid;
    data.dst_cpu = args->dst_cpu;
    data.dst_nid = args->dst_nid;

    swap_numa_events.perf_submit(args, &data, sizeof(data));
    return 0;
}

TRACEPOINT_PROBE(migrate, mm_migrate_pages_start) {
    struct migrate_pages_start_data_t data = {};
    data.pid = bpf_get_current_pid_tgid() >> 32;
    data.mode = args->mode;
    data.reason = args->reason;

    migrate_pages_start_events.perf_submit(args, &data, sizeof(data));
    return 0;
}

TRACEPOINT_PROBE(vmalloc, alloc_vmap_area) {
    struct alloc_vmap_area_data_t data = {};
    data.timestamp = bpf_ktime_get_ns();
    data.pid = bpf_get_current_pid_tgid() >> 32; 
    data.addr = args->addr;
    data.size = args->size;
    data.align = args->align;
    data.vstart = args->vstart;
    data.vend = args->vend;
    data.failed = args->failed;

    alloc_vmap_area_events.perf_submit(args, &data, sizeof(data));
    return 0;
}

TRACEPOINT_PROBE(vmalloc, free_vmap_area_noflush) {
    struct free_vmap_area_noflush_data_t data = {};
    data.timestamp = bpf_ktime_get_ns();
    data.pid = bpf_get_current_pid_tgid() >> 32;
    data.va_start = args->va_start;
    data.nr_lazy = args->nr_lazy;
    data.nr_lazy_max = args->nr_lazy_max;

    free_vmap_area_events.perf_submit(args, &data, sizeof(data));
    return 0;
}

TRACEPOINT_PROBE(sched, sched_process_fork) {
    struct fork_data_t data = {};
    data.timestamp = bpf_ktime_get_ns();
    data.parent_pid = args->parent_pid;
    data.child_pid = args->child_pid;
    data.cpu_id = bpf_get_smp_processor_id();

    process_fork_events.perf_submit(args, &data, sizeof(data));
    return 0;
}

TRACEPOINT_PROBE(sched, sched_process_exit) {
    struct exit_data_t data = {};
    data.timestamp = bpf_ktime_get_ns();
    data.pid = args->pid;
    data.prio = args->prio;

    process_exit_events.perf_submit(args, &data, sizeof(data));
    return 0;
}

"""

# Load BPF program
b = BPF(text=bpf_program)

# Define output data structures
class Data(ct.Structure):
    _fields_ = [
        ("timestamp", ct.c_uint64),
        ("pid", ct.c_uint),
        ("tgid", ct.c_uint),
        ("ngid", ct.c_uint),
        ("src_cpu", ct.c_int),
        ("src_nid", ct.c_int),
        ("dst_cpu", ct.c_int),
        ("dst_nid", ct.c_int)
    ]

class MigrateData(ct.Structure):
    _fields_ = [
        ("timestamp", ct.c_uint64),
        ("comm", ct.c_char * 16),
        ("pid", ct.c_uint),
        ("prio", ct.c_int),
        ("orig_cpu", ct.c_int),
        ("dest_cpu", ct.c_int)
    ]

class PageMigrateData(ct.Structure):
    _fields_ = [
        ("timestamp", ct.c_uint64),
        ("pid", ct.c_uint),
        ("succeeded", ct.c_ulong),
        ("failed", ct.c_ulong),
        ("thp_succeeded", ct.c_ulong),
        ("thp_failed", ct.c_ulong),
        ("thp_split", ct.c_ulong),
        ("mode", ct.c_int),
        ("reason", ct.c_int),
    ]

class SwapNumaData(ct.Structure):
    _fields_ = [
        ("timestamp", ct.c_uint64),
        ("src_pid", ct.c_uint),
        ("src_tgid", ct.c_uint),
        ("src_ngid", ct.c_uint),
        ("src_cpu", ct.c_int),
        ("src_nid", ct.c_int),
        ("dst_pid", ct.c_uint),
        ("dst_tgid", ct.c_uint),
        ("dst_ngid", ct.c_uint),
        ("dst_cpu", ct.c_int),
        ("dst_nid", ct.c_int)
    ]

class MigratePagesStartData(ct.Structure):
    _fields_ = [
        ("pid", ct.c_uint),
        ("mode", ct.c_int),
        ("reason", ct.c_int)
    ]

class PTEMigrateData(ct.Structure):
    _fields_ = [
        ("pid", ct.c_uint),
        ("addr", ct.c_ulong),
        ("pte", ct.c_ulong),
        ("order", ct.c_int)
    ]

class AllocVmapAreaData(ct.Structure):
    _fields_ = [
        ("timestamp", ct.c_uint64),
        ("pid", ct.c_int),
        ("addr", ct.c_ulong),
        ("size", ct.c_ulong),
        ("align", ct.c_ulong),
        ("vstart", ct.c_ulong),
        ("vend", ct.c_ulong),
        ("failed", ct.c_int)
    ]

class FreeVmapAreaNoflushData(ct.Structure):
    _fields_ = [
        ("timestamp", ct.c_uint64),
        ("pid", ct.c_int),
        ("va_start", ct.c_ulong),
        ("nr_lazy", ct.c_ulong),
        ("nr_lazy_max", ct.c_ulong)
    ]

class ForkData(ct.Structure):
    _fields_ = [
        ("timestamp", ct.c_uint64),
        ("parent_pid", ct.c_int),
        ("child_pid", ct.c_int),
        ("cpu_id", ct.c_int)
    ]

class ExitData(ct.Structure):
    _fields_ = [
        ("timestamp", ct.c_uint64),
        ("comm", ct.c_char * 16),
        ("pid", ct.c_int),
        ("prio", ct.c_int)
    ]

# Print headers
# print(f"{'TRACEPOINT':<20} {'PID':<8} {'TGID':<8} {'NGID':<8} {'SRC_CPU':<8} {'SRC_NID':<8} {'DST_CPU':<8} {'DST_NID':<8}")
# print(f"{'TRACEPOINT':<20} {'COMM':<16} {'PID':<8} {'PRIO':<8} {'ORIG_CPU':<8} {'DEST_CPU':<8}")
# print(f"{'TRACEPOINT':<20} {'PID':<8} {'SUCCEEDED':<12} {'FAILED':<12} {'THP_SUCCEEDED':<15} {'THP_FAILED':<12} {'THP_SPLIT':<12} {'MODE':<8} {'REASON':<8} {'SRC_NID':<8} {'DST_NID':<8}")
# print(f"{'TRACEPOINT':<20} {'SRC_PID':<8} {'SRC_TGID':<8} {'SRC_NGID':<8} {'SRC_CPU':<8} {'SRC_NID':<8} {'DST_PID':<8} {'DST_TGID':<8} {'DST_NGID':<8} {'DST_CPU':<8} {'DST_NID':<8}")
# print(f"{'TRACEPOINT':<20} {'PID':<8} {'MODE':<20} {'REASON':<20}")
# print(f"{'TRACEPOINT':<20} {'PID':<8} {'ADDR':<18} {'PTE':<18} {'ORDER':<6}")

# create nid to cpuid map
cpuid_nid = {0:0, 1:0, 2:0, 3:0, 4:0, 5:0, 6:0, 7:0, 16:0, 17:0, 18:0, 19:0, 20:0, 21:0, 22:0,
             8:1, 9:1, 10:1, 11:1, 12:1, 13:1, 14:1, 15:1, 23:1, 24:1, 25:1, 26:1, 27:1, 28:1, 29:1, 30:1, 31:1}

sched_move_numa_map = defaultdict(lambda: defaultdict(int))
sched_migrate_task_map = defaultdict(lambda: defaultdict(int))
mm_migrate_pages_map = defaultdict(lambda: defaultdict(int))
sched_swap_numa_map = defaultdict(lambda: defaultdict(int))
mm_migrate_pages_start_map = defaultdict(lambda: defaultdict(int))
mm_set_migration_pte_map = defaultdict(lambda: defaultdict(int))
# Crossing fingers that this is somehow isn't susceptible to race conditions
thread_lifecycle_map = defaultdict(list)
program_lifecycle_map = []
thread_fork_count_map = defaultdict(int)
lb_numa_conflict_counter = defaultdict(lambda: defaultdict(list))

# Process events
def print_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(Data)).contents
    # ATTEMPTED # of intra node NUMA task migration
    # there are lost events, so we log inter-node migrations only
    if event.src_nid != event.dst_nid and event.pid >= 1000:
        sched_move_numa_map[event.pid][(event.src_nid, event.dst_nid)] += 1
        if len(thread_lifecycle_map[event.pid]) > 0 and thread_lifecycle_map[event.pid][-1][1] == event.src_nid and thread_lifecycle_map[event.pid][-1][0] == 'LB_MIGRATE':
            thread_lifecycle_map[event.pid].pop() 
        thread_lifecycle_map[event.pid].append(['NUMA_MIGRATE', event.src_nid, event.dst_nid, event.timestamp])
        program_lifecycle_map.append([event.pid, 'NUMA_MIGRATE', event.src_nid, event.dst_nid, event.timestamp])
    # print(f"{'sched_move_numa':<20} {event.pid:<8} {event.tgid:<8} {event.ngid:<8} {event.src_cpu:<8} {event.src_nid:<8} {event.dst_cpu:<8} {event.dst_nid:<8}")

def print_migrate_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(MigrateData)).contents
    # for same reason, we want to prevent losing too many events
    if cpuid_nid[event.orig_cpu] != cpuid_nid[event.dest_cpu] and event.pid >= 1000:
        sched_migrate_task_map[event.pid][(cpuid_nid[event.orig_cpu], cpuid_nid[event.dest_cpu])] += 1
        program_lifecycle_map.append([event.pid, 'LB_MIGRATE', cpuid_nid[event.orig_cpu], cpuid_nid[event.dest_cpu], event.timestamp])
        if len(thread_lifecycle_map[event.pid]) > 0 and thread_lifecycle_map[event.pid][-1][1] == cpuid_nid[event.orig_cpu]: 
            return
        thread_lifecycle_map[event.pid].append(['LB_MIGRATE', cpuid_nid[event.orig_cpu], cpuid_nid[event.dest_cpu], event.timestamp])
    # sched_migrate_task_map[event.pid].append((event.orig_cpu, cpuid_nid[event.orig_cpu], event.dest_cpu, cpuid_nid[event.dest_cpu]))
    # print(f"{'sched_migrate_task':<20} {event.comm.decode('utf-8'):<16} {event.pid:<8} {event.prio:<8} {event.orig_cpu:<8} {event.dest_cpu:<8}")

def print_page_migrate_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(PageMigrateData)).contents
    mode = ["MIGRATE_ASYNC", "MIGRATE_SYNC_LIGHT", "MIGRATE_SYNC"][event.mode]
    reason = ["compaction", "memory_failure", "memory_hotplug", "syscall_or_cpuset", "mempolicy_mbind", "numa_misplaced", "contig_range", "longterm_pin", "demotion"][event.reason]
    # also, only log numa_misplaced events
    if event.reason == 5 and event.pid >= 1000:
        mm_migrate_pages_map[event.pid][reason] += event.succeeded
        # if len(thread_lifecycle_map[event.pid]) > 0 and thread_lifecycle_map[event.pid][-1][0] == 'PAGE_MIGRATE':
        #     thread_lifecycle_map[event.pid][-1][1] += event.succeeded
        #     thread_lifecycle_map[event.pid][-1][2] += event.failed
        #     thread_lifecycle_map[event.pid][-1][-1] = event.timestamp
        # else:
        #     thread_lifecycle_map[event.pid].append(['PAGE_MIGRATE', event.succeeded, event.failed, event.timestamp])
        if len(program_lifecycle_map) > 0 and program_lifecycle_map[-1][0] == event.pid:
            program_lifecycle_map[-1][2] += event.succeeded
            program_lifecycle_map[-1][3] += event.failed
            program_lifecycle_map[-1][-1] = event.timestamp
        else:
            program_lifecycle_map.append([event.pid, 'PAGE_MIGRATE', event.succeeded, event.failed, event.timestamp])   
    # print(f"{'mm_migrate_pages':<20} {event.pid:<8} {event.succeeded:<12} {event.failed:<12} {event.thp_succeeded:<15} {event.thp_failed:<12} {event.thp_split:<12} {mode:<8} {reason:<8} {event.src_nid:<8} {event.dst_nid:<8}")

def print_swap_numa_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(SwapNumaData)).contents
    sched_swap_numa_map[(event.src_pid, event.dst_pid)][(event.src_nid, event.dst_nid)] += 1
    if len(thread_lifecycle_map[event.src_pid]) > 0 and thread_lifecycle_map[event.src_pid][-1][1] == event.src_nid and thread_lifecycle_map[event.src_pid][0] == 'LB_MIGRATE':
        thread_lifecycle_map[event.src_pid].pop()
    thread_lifecycle_map[event.src_pid].append(['NUMA_SWAP', event.src_nid, event.dst_nid, event.timestamp])
    program_lifecycle_map.append([event.src_pid, 'NUMA_SWAP', event.src_nid, event.dst_nid, event.timestamp])
    # print(f"{'sched_swap_numa':<20} {event.src_pid:<8} {event.src_tgid:<8} {event.src_ngid:<8} {event.src_cpu:<8} {event.src_nid:<8} {event.dst_pid:<8} {event.dst_tgid:<8} {event.dst_ngid:<8} {event.dst_cpu:<8} {event.dst_nid:<8}")

def print_migrate_pages_start_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(MigratePagesStartData)).contents
    mode = ["MIGRATE_ASYNC", "MIGRATE_SYNC_LIGHT", "MIGRATE_SYNC"][event.mode]
    reason = ["compaction", "memory_failure", "memory_hotplug", "syscall_or_cpuset", "mempolicy_mbind", "numa_misplaced", "contig_range", "longterm_pin", "demotion"][event.reason]
    if event.reason == 5 and event.pid >= 1000:
        mm_migrate_pages_start_map[event.pid][reason] += 1
    # print(f"{'mm_migrate_pages_start':<20} {event.pid:<8} {mode:<20} {reason:<20}")

def print_alloc_vmap_area_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(AllocVmapAreaData)).contents
    # thread_lifecycle_map[event.pid].append(['VM_ALLOC', event.addr, event.size, event.vstart, event.vend, event.timestamp])
    program_lifecycle_map.append([event.pid, 'VM_ALLOC', event.addr, event.size, event.vstart, event.vend, event.timestamp])

def print_free_vmap_area_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(FreeVmapAreaNoflushData)).contents
    # thread_lifecycle_map[event.pid].append(['VM_FREE', event.va_start, event.timestamp])
    program_lifecycle_map.append([event.pid, 'VM_FREE', event.va_start, event.timestamp])

def print_process_fork_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(ForkData)).contents
    # thread_lifecycle_map[event.parent_pid].append(['FORK', event.child_pid, cpuid_nid[event.cpu_id], event.timestamp])
    program_lifecycle_map.append([event.parent_pid, 'FORK', event.child_pid, cpuid_nid[event.cpu_id], event.timestamp])
    thread_fork_count_map[event.parent_pid] += 1
    

def print_process_exit_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(ExitData)).contents
    # thread_lifecycle_map[event.pid].append(['EXIT', event.timestamp])
    program_lifecycle_map.append([event.pid, 'EXIT', event.timestamp])
# def print_pte_migrate_event(cpu, data, size):
#     event = ct.cast(data, ct.POINTER(PTEMigrateData)).contents
#     mm_set_migration_pte_map[event.pid][event.addr] += event.order
    # print(f"{'set_migration_pte':<20} {event.pid:<8} {event.addr:<18x} {event.pte:<18x} {event.order:<6}")

# Set up callbacks
b["events"].open_perf_buffer(print_event, page_cnt=128)
b["migrate_events"].open_perf_buffer(print_migrate_event, page_cnt=128)
b["page_migrate_events"].open_perf_buffer(print_page_migrate_event, page_cnt=128)
b["swap_numa_events"].open_perf_buffer(print_swap_numa_event, page_cnt=128)
b["migrate_pages_start_events"].open_perf_buffer(print_migrate_pages_start_event, page_cnt=128)
b["alloc_vmap_area_events"].open_perf_buffer(print_alloc_vmap_area_event, page_cnt=128)
b["free_vmap_area_events"].open_perf_buffer(print_free_vmap_area_event, page_cnt=128)
b["process_fork_events"].open_perf_buffer(print_process_fork_event, page_cnt=128)
b["process_exit_events"].open_perf_buffer(print_process_exit_event, page_cnt=128)

# b["pte_migrate_events"].open_perf_buffer(print_pte_migrate_event)

def calc_time_diff(event1_timestamp_ns, event2_timestamp_ns):
    difference_ns = event2_timestamp_ns - event1_timestamp_ns
    # Convert nanoseconds to seconds
    difference_seconds = difference_ns / 1_000_000_000
    return difference_seconds

# Function to execute the target executable with arguments
def run_executable(executable_path, args):
    process = subprocess.Popen([executable_path] + args)
    return process, process.pid

# Main function
def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <executable_path> [args...]")
        sys.exit(1)
    
    iteration = sys.argv[1]
    executable_path = sys.argv[2]
    args = sys.argv[3:]

    start_time = time.perf_counter()
    # Start the executable with arguments
    process, main_pid = run_executable(executable_path, args)
    try:
        # Poll for events while the executable is running
        while process.poll() is None:
            b.perf_buffer_poll()
    except KeyboardInterrupt:
        print("Interrupted, detaching BPF program...")
        process.terminate()
    end_time = time.perf_counter()

    elapsed_time = end_time - start_time
    total_page_migration = 0 
    with open(f'/mydata/results/657.xz_s/iteration_{iteration}/traces.txt', 'a') as file:
        file.write(f"Elapsed Time: {elapsed_time}\n")
        file.write(f"MAIN PID: {main_pid}\n")

        for pid, migration_count in sched_move_numa_map.items():
            if pid < main_pid:
                continue
            for numaset, count in migration_count.items():
                file.write(f"sched_move_numa({pid}): {numaset} : {count}\n")
        for pid, migration_count in sched_migrate_task_map.items():
            if pid < main_pid:
                continue
            for numaset, count in migration_count.items():
                file.write(f"sched_migrate_task({pid}): {numaset} : {count}\n")
        for pid, reason_count in mm_migrate_pages_map.items():
            if pid < main_pid:
                continue
            for reason, count in reason_count.items():
                file.write(f"mm_migrate_pages({pid}): {reason} : {count}\n")
                total_page_migration += count
        for pid_pair, nid_pair in sched_swap_numa_map.items():
            for src_nid, dest_nid in nid_pair.items():
                file.write(f"sched_swap_numa({pid_pair}): {src_nid} : {dest_nid}\n")
        for pid, lifecycle in thread_lifecycle_map.items():
            if pid < main_pid:
                continue
            file.write(f"PID: {pid}\n")
            sorted_lifecycle = sorted(lifecycle, key=lambda x: x[-1])
            initial_decision = "" 
            for i in range(len(sorted_lifecycle)):
                file.write(f"{sorted_lifecycle[i]}\n")
                if i == 0:
                    initial_decision = sorted_lifecycle[i][0]
                elif (sorted_lifecycle[i - 1][0] == 'LB_MIGRATE' or sorted_lifecycle[i][0] == 'LB_MIGRATE') and sorted_lifecycle[i - 1][0] != sorted_lifecycle[i][0]:
                    time_diff = calc_time_diff(sorted_lifecycle[i - 1][-1], sorted_lifecycle[i][-1]) 
                    if sorted_lifecycle[i][0] == 'LB_MIGRATE':
                        # LB disagrees with the latest NUMA Balancer's migration decision
                        lb_numa_conflict_counter[pid][0].append(time_diff)
                    else:
                        # NUMA Balancer disagrees with the LB's decision to migrate; i.e. LB migrated a task to wrong NUMA Node
                        lb_numa_conflict_counter[pid][1].append(time_diff)
                else:
                    continue
                        
            lb_numa_conflict_counter[pid][2].append(initial_decision)
        file.write("\nEvent Timeline\n")
        sorted_program_lifecycle = sorted(program_lifecycle_map, key=lambda x: x[-1])
        for event in sorted_program_lifecycle:
            file.write(f"{event}\n")
        for pid, fork_count in thread_fork_count_map.items():
            if pid < main_pid:
                continue
            file.write(f"{pid}: {fork_count}\n")

    with open(f'/mydata/results/657.xz_s/iteration_{iteration}/post_process.txt', 'a') as f:
        f.write(f"TIME: {elapsed_time}\n")
        f.write(f"PAGE MIGRATION COUNT: {total_page_migration}\n")
        for pid, disagree_map in lb_numa_conflict_counter.items():
            for lb_numa, times in disagree_map.items():
                f.write(f"{pid} {lb_numa}: {times}\n")
            f.write(f"\n")
    print(f"Finished Processing Iteration_{iteration}\n")
if __name__ == "__main__":
    main()
