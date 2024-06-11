#include <iostream>
#include <thread>
#include <vector>

// Size of the memory block each thread will work on
const size_t MEM_BLOCK_SIZE = 1024 * 1;

// Memory-intensive workload function
void memoryIntensiveWorkload(int thread_id) {
    // Allocate a large array
    std::vector<int> largeArray(MEM_BLOCK_SIZE);

    // Initialize the array
    for (size_t i = 0; i < MEM_BLOCK_SIZE; ++i) {
        largeArray[i] = i;
    }

    // Perform read/write operations on the array
    for (size_t i = 0; i < MEM_BLOCK_SIZE; ++i) {
        largeArray[i] = largeArray[i] * 2;
    }

    // Print a message indicating the thread has completed its work
    // std::cout << "Thread " << thread_id << " completed memory-intensive workload." << std::endl;
}

int main() {
    // Number of threads to spawn
    const int numThreads = 16;

    // Vector to hold the threads
    std::vector<std::thread> threads;
    // std::cout << "Starting workload" << std::endl;
    // Spawn the threads
    for (int i = 0; i < numThreads; ++i) {
        threads.emplace_back(memoryIntensiveWorkload, i);
    }

    // Wait for all threads to complete
    for (auto& thread : threads) {
        thread.join();
    }

    // Indicate that all threads have completed
    // std::cout << "All threads have completed their memory-intensive workloads." << std::endl;

    return 0;
}
