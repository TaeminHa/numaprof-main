remote_mem_access, local_mem_access = 0, 0
start_collecting = True

with open('output.txt') as output_file:
    for line in output_file:
        # if "Starting" in line:
            # start_collecting = True

        # if not start_collecting:
            # continue
        # 11 = Remote Write 12 = Remote Read
        if line.startswith("1"):
            remote_mem_access += 1
        # 21 = Local Write 22 = Local Read
        else:
            local_mem_access += 1

print(f"# of remote mem accesses : {remote_mem_access}  || {100 * remote_mem_access / (local_mem_access + remote_mem_access)}")
print(f"# of local mem accesses : {local_mem_access}   || {100 * local_mem_access / (local_mem_access + remote_mem_access)}")
print(f"# of total mem access : {remote_mem_access + local_mem_access}")
