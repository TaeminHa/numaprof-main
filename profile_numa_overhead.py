from bcc import BPF
import sys
import subprocess
import time
import os

from bcc import BPF
import sys
import subprocess
import time
import os

# Define the BPF program
bpf_program = """
BPF_HASH(start_task_numa_work, u64, u64);
BPF_HASH(total_time_task_numa_work, u64, u64);
BPF_HASH(count_task_numa_work, u64, u64);

BPF_HASH(start_migrate_misplaced_folio, u64, u64);
BPF_HASH(total_time_migrate_misplaced_folio, u64, u64);
BPF_HASH(count_migrate_misplaced_folio, u64, u64);

BPF_HASH(start_task_numa_fault, u64, u64);
BPF_HASH(total_time_task_numa_fault, u64, u64);
BPF_HASH(count_task_numa_fault, u64, u64);

int trace_task_numa_work_enter(struct pt_regs *ctx) {
    u64 id = bpf_get_current_pid_tgid();
    u64 pid = id >> 32;
    u64 ts = bpf_ktime_get_ns();
    start_task_numa_work.update(&pid, &ts);
    return 0;
}

int trace_task_numa_work_exit(struct pt_regs *ctx) {
    u64 id = bpf_get_current_pid_tgid(); 
    u64 pid = id >> 32;
    u64 *tsp = start_task_numa_work.lookup(&pid);
    if (tsp != 0) {
        u64 delta = bpf_ktime_get_ns() - *tsp;
        
        // Update total time
        u64 *total = total_time_task_numa_work.lookup(&pid);
        if (total) {
            *total += delta;
        } else {
            total_time_task_numa_work.update(&pid, &delta);
        }

        // Update count
        u64 *cnt = count_task_numa_work.lookup(&pid);
        if (cnt) {
            *cnt += 1;
        } else {
            u64 initial = 1;
            count_task_numa_work.update(&pid, &initial);
        }

        start_task_numa_work.delete(&pid);
    }
    return 0;
}

int trace_task_numa_fault_enter(struct pt_regs *ctx) {
    u64 id = bpf_get_current_pid_tgid();
    u64 pid = id >> 32;
    u64 ts = bpf_ktime_get_ns();
    start_task_numa_fault.update(&pid, &ts);
    return 0;
}

int trace_task_numa_fault_exit(struct pt_regs *ctx) {
    u64 id = bpf_get_current_pid_tgid(); 
    u64 pid = id >> 32;
    u64 *tsp = start_task_numa_fault.lookup(&pid);
    if (tsp != 0) {
        u64 delta = bpf_ktime_get_ns() - *tsp;
        
        // Update total time
        u64 *total = total_time_task_numa_fault.lookup(&pid);
        if (total) {
            *total += delta;
        } else {
            total_time_task_numa_fault.update(&pid, &delta);
        }

        // Update count
        u64 *cnt = count_task_numa_fault.lookup(&pid);
        if (cnt) {
            *cnt += 1;
        } else {
            u64 initial = 1;
            count_task_numa_fault.update(&pid, &initial);
        }

        start_task_numa_fault.delete(&pid);
    }
    return 0;
}

int trace_migrate_misplaced_folio_enter(struct pt_regs *ctx) {
    u64 id = bpf_get_current_pid_tgid();
    u64 pid = id >> 32;
    u64 ts = bpf_ktime_get_ns();
    start_migrate_misplaced_folio.update(&pid, &ts);
    return 0;
}

int trace_migrate_misplaced_folio_exit(struct pt_regs *ctx) {
    u64 id = bpf_get_current_pid_tgid(); 
    u64 pid = id >> 32;
    u64 *tsp = start_migrate_misplaced_folio.lookup(&pid);
    if (tsp != 0) {
        u64 delta = bpf_ktime_get_ns() - *tsp;
        
        // Update total time
        u64 *total = total_time_migrate_misplaced_folio.lookup(&pid);
        if (total) {
            *total += delta;
        } else {
            total_time_migrate_misplaced_folio.update(&pid, &delta);
        }

        // Update count
        u64 *cnt = count_migrate_misplaced_folio.lookup(&pid);
        if (cnt) {
            *cnt += 1;
        } else {
            u64 initial = 1;
            count_migrate_misplaced_folio.update(&pid, &initial);
        }

        start_migrate_misplaced_folio.delete(&pid);
    }
    return 0;
}
"""

# Initialize BPF
b = BPF(text=bpf_program)
b.attach_kprobe(event="task_numa_work", fn_name="trace_task_numa_work_enter")
b.attach_kretprobe(event="task_numa_work", fn_name="trace_task_numa_work_exit")
b.attach_kprobe(event="migrate_pages", fn_name="trace_migrate_misplaced_folio_enter")
b.attach_kretprobe(event="migrate_pages", fn_name="trace_migrate_misplaced_folio_exit")
b.attach_kprobe(event="task_numa_fault", fn_name="trace_task_numa_fault_enter")
b.attach_kretprobe(event="task_numa_fault", fn_name="trace_task_numa_fault_exit")

# Function to execute the target executable with arguments
def run_executable(executable_path, args):
    process = subprocess.Popen([executable_path] + args)
    return process, process.pid

# Main function
def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <executable_path> [args...]")
        sys.exit(1)
    
    bench = sys.argv[1]
    executable_path = sys.argv[2]
    args = sys.argv[3:]

    start_time = time.perf_counter()
    # Start the executable with arguments
    process, main_pid = run_executable(executable_path, args)
    try:
        # Poll for events while the executable is running
        while process.poll() is None:
            b.perf_buffer_poll(timeout=1000)
    except KeyboardInterrupt:
        print("Interrupted, detaching BPF program...")
        process.terminate()
    end_time = time.perf_counter()

    elapsed_time = end_time - start_time

    with open(f'/mydata/results/{bench}/overhead.txt', 'a') as file:
        file.write("task_numa_work Statistics\n")
        file.write("PID\tTotal Time (ns)\tInvocation Count\n")
        real_total_time_task_numa_work = 0
        for k, v in b.get_table("total_time_task_numa_work").items():
            total_time = v.value
            real_total_time_task_numa_work += total_time
            count = b.get_table("count_task_numa_work")[k].value
            file.write(f"{k.value}\t{total_time}\t{count}\n")
        file.write(f"Time Spent in task_numa_work: {real_total_time_task_numa_work}\n")

        file.write("migrate_misplaced_folio Statistics\n")
        file.write("PID\tTotal Time (ns)\tInvocation Count\n")
        real_total_time_migrate_misplaced_folio = 0
        for k, v in b.get_table("total_time_migrate_misplaced_folio").items():
            total_time = v.value
            real_total_time_migrate_misplaced_folio += total_time
            count = b.get_table("count_migrate_misplaced_folio")[k].value
            file.write(f"{k.value}\t{total_time}\t{count}\n")
        file.write(f"Time Spent in migrate_misplaced_folio: {real_total_time_migrate_misplaced_folio}\n")

        file.write("task_numa_fault Statistics\n")
        file.write("PID\tTotal Time (ns)\tInvocation Count\n")
        real_total_time_task_numa_fault = 0
        for k, v in b.get_table("total_time_task_numa_fault").items():
            total_time = v.value
            real_total_time_task_numa_fault += total_time
            count = b.get_table("count_task_numa_fault")[k].value
            file.write(f"{k.value}\t{total_time}\t{count}\n")
        file.write(f"Time Spent in task_numa_fault: {real_total_time_task_numa_fault}\n")
        # Actual overhead data that I want to extract; which I probably will need to run multiple iterations
        overhead = (real_total_time_task_numa_fault + real_total_time_migrate_misplaced_folio + real_total_time_task_numa_work) / 1e9
        file.write(f"FINAL TOTAL OVERHEAD OF NUMA BALANCING: {overhead}s Out of {elapsed_time}s {overhead * 100 / elapsed_time}%\n")

    b.detach_kprobe(event="task_numa_work")
    b.detach_kretprobe(event="task_numa_work")
    b.detach_kprobe(event="migrate_pages")
    b.detach_kretprobe(event="migrate_pages")
    b.detach_kprobe(event="task_numa_fault")
    b.detach_kretprobe(event="task_numa_fault")

if __name__ == "__main__":
    main()