from bcc import BPF
import ctypes as ct
import subprocess
import sys

# Define the BPF program
bpf_program = """
#include <uapi/linux/ptrace.h>
#include <linux/sched.h>

struct data_t {
    u32 pid;
    u32 tgid;
    u32 ngid;
    int src_cpu;
    int src_nid;
    int dst_cpu;
    int dst_nid;
};

struct migrate_data_t {
    char comm[16];
    u32 pid;
    int prio;
    int orig_cpu;
    int dest_cpu;
};

struct page_migrate_data_t {
    unsigned long succeeded;
    unsigned long failed;
    unsigned long thp_succeeded;
    unsigned long thp_failed;
    unsigned long thp_split;
    int mode;
    int reason;
};

struct swap_numa_data_t {
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

BPF_PERF_OUTPUT(events);
BPF_PERF_OUTPUT(migrate_events);
BPF_PERF_OUTPUT(page_migrate_events);
BPF_PERF_OUTPUT(swap_numa_events);

TRACEPOINT_PROBE(sched, sched_move_numa) {
    struct data_t data = {};
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
    bpf_probe_read(&data.comm, sizeof(data.comm), args->comm);
    data.pid = args->pid;
    data.prio = args->prio;
    data.orig_cpu = args->orig_cpu;
    data.dest_cpu = args->dest_cpu;

    migrate_events.perf_submit(args, &data, sizeof(data));
    return 0;
}

TRACEPOINT_PROBE(mm, mm_migrate_pages) {
    struct page_migrate_data_t data = {};
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
"""

# Load BPF program
b = BPF(text=bpf_program)

# Define output data structure for sched_move_numa
class Data(ct.Structure):
    _fields_ = [
        ("pid", ct.c_uint),
        ("tgid", ct.c_uint),
        ("ngid", ct.c_uint),
        ("src_cpu", ct.c_int),
        ("src_nid", ct.c_int),
        ("dst_cpu", ct.c_int),
        ("dst_nid", ct.c_int)
    ]

# Define output data structure for sched_migrate_task
class MigrateData(ct.Structure):
    _fields_ = [
        ("comm", ct.c_char * 16),
        ("pid", ct.c_uint),
        ("prio", ct.c_int),
        ("orig_cpu", ct.c_int),
        ("dest_cpu", ct.c_int)
    ]

# Define output data structure for mm_migrate_pages
class PageMigrateData(ct.Structure):
    _fields_ = [
        ("succeeded", ct.c_ulong),
        ("failed", ct.c_ulong),
        ("thp_succeeded", ct.c_ulong),
        ("thp_failed", ct.c_ulong),
        ("thp_split", ct.c_ulong),
        ("mode", ct.c_int),
        ("reason", ct.c_int)
    ]

# Define output data structure for sched_swap_numa
class SwapNumaData(ct.Structure):
    _fields_ = [
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

# Print headers
# print(f"{'TRACEPOINT':<20} {'PID':<8} {'TGID':<8} {'NGID':<8} {'SRC_CPU':<8} {'SRC_NID':<8} {'DST_CPU':<8} {'DST_NID':<8}")
# print(f"{'TRACEPOINT':<20} {'COMM':<16} {'PID':<8} {'PRIO':<8} {'ORIG_CPU':<8} {'DEST_CPU':<8}")
# print(f"{'TRACEPOINT':<20} {'SUCCEEDED':<12} {'FAILED':<12} {'THP_SUCCEEDED':<15} {'THP_FAILED':<12} {'THP_SPLIT':<12} {'MODE':<8} {'REASON':<8}")
# print(f"{'TRACEPOINT':<20} {'SRC_PID':<8} {'SRC_TGID':<8} {'SRC_NGID':<8} {'SRC_CPU':<8} {'SRC_NID':<8} {'DST_PID':<8} {'DST_TGID':<8} {'DST_NGID':<8} {'DST_CPU':<8} {'DST_NID':<8}")

# Process sched_move_numa event
def print_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(Data)).contents
    print(f"{'sched_move_numa':<20} {event.pid:<8} {event.tgid:<8} {event.ngid:<8} {event.src_cpu:<8} {event.src_nid:<8} {event.dst_cpu:<8} {event.dst_nid:<8}")

# Process sched_migrate_task event
def print_migrate_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(MigrateData)).contents
    print(f"{'sched_migrate_task':<20} {event.comm.decode('utf-8'):<16} {event.pid:<8} {event.prio:<8} {event.orig_cpu:<8} {event.dest_cpu:<8}")

# Process mm_migrate_pages event
def print_page_migrate_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(PageMigrateData)).contents
    mode = ["MIGRATE_ASYNC", "MIGRATE_SYNC_LIGHT", "MIGRATE_SYNC"][event.mode]
    reason = ["compaction", "memory_failure", "memory_hotplug", "syscall_or_cpuset", "mempolicy_mbind", "numa_misplaced", "contig_range", "longterm_pin", "demotion"][event.reason]
    print(f"{'mm_migrate_pages':<20} {event.succeeded:<12} {event.failed:<12} {event.thp_succeeded:<15} {event.thp_failed:<12} {event.thp_split:<12} {mode:<8} {reason:<8}")

# Process sched_swap_numa event
def print_swap_numa_event(cpu, data, size):
    event = ct.cast(data, ct.POINTER(SwapNumaData)).contents
    print(f"{'sched_swap_numa':<20} {event.src_pid:<8} {event.src_tgid:<8} {event.src_ngid:<8} {event.src_cpu:<8} {event.src_nid:<8} {event.dst_pid:<8} {event.dst_tgid:<8} {event.dst_ngid:<8} {event.dst_cpu:<8} {event.dst_nid:<8}")

# Set up callbacks
b["events"].open_perf_buffer(print_event)
b["migrate_events"].open_perf_buffer(print_migrate_event)
b["page_migrate_events"].open_perf_buffer(print_page_migrate_event)
b["swap_numa_events"].open_perf_buffer(print_swap_numa_event)

# Function to execute the target executable with arguments
def run_executable(executable_path, args):
    process = subprocess.Popen([executable_path] + args)
    return process

# Main function
def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <executable_path> [args...]")
        sys.exit(1)

    executable_path = sys.argv[1]
    args = sys.argv[2:]

    # Start the executable with arguments
    process = run_executable(executable_path, args)

    try:
        # Poll for events while the executable is running
        while process.poll() is None:
            b.perf_buffer_poll()
    except KeyboardInterrupt:
        print("Interrupted, detaching BPF program...")
        process.terminate()

if __name__ == "__main__":
    main()

