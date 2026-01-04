#include <atomic>
#include <csignal>
#include <cstdlib>
#include <thread>
#include <chrono>
#include "mfuzz.h"

static std::atomic<bool> g_done{false};
static std::atomic<bool> g_stop{false};
extern "C" void on_sigint(int) 
{
    g_stop.store(true, std::memory_order_relaxed);
}

int main(int argc, char** argv) 
{
    char* bench_path = nullptr;
    int time_budget  = 3600 * 24;

    std::signal(SIGINT, on_sigint);

    int opt;
    while ((opt = getopt(argc, argv, "b:t:")) != -1) {
        switch (opt) {
            case 'b': bench_path = optarg; break;
            case 't': time_budget = std::atoi(optarg); break;
            default:
                std::printf("Unknown option\n");
                return 1;
        }
    }

    if (!bench_path) {
        std::printf("Missing -b <bench_path>\n");
        return 1;
    }

    MFuzz mfuzz(bench_path, "honggfuzz");
    std::thread worker([&]() {
        mfuzz.start_fuzzer(time_budget);
        g_done.store(true, std::memory_order_relaxed);
    });

    while (!g_stop.load(std::memory_order_relaxed) &&
        !g_done.load(std::memory_order_relaxed)) {
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }

    mfuzz.stop_fuzzer();
    worker.join();
    return 0;
}
