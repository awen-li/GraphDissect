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
    std::string schedule = "fixed";
    std::string queue_policy = "shared";
    unsigned window_seconds = 0;
    unsigned random_seed = 1;

    std::signal(SIGINT, on_sigint);

    int opt;
    while ((opt = getopt(argc, argv, "b:t:s:q:w:r:h")) != -1) {
        switch (opt) {
            case 'b': bench_path = optarg; break;
            case 't': time_budget = std::atoi(optarg); break;
            case 's': schedule = optarg; break;
            case 'q': queue_policy = optarg; break;
            case 'w': window_seconds = static_cast<unsigned>(std::stoul(optarg)); break;
            case 'r': random_seed = static_cast<unsigned>(std::stoul(optarg)); break;
            case 'h':
                std::printf("Usage: mfuzz -b BENCH -t SECONDS [-s fixed|random|progress] "
                            "[-q shared|independent] [-w WINDOW_SECONDS] [-r RANDOM_SEED]\n");
                return 0;
            default:
                std::printf("Unknown option\n");
                return 1;
        }
    }

    if (!bench_path || time_budget <= 0) {
        std::printf("Missing -b <bench_path>\n");
        return 1;
    }
    if ((schedule != "fixed" && schedule != "random" && schedule != "progress") ||
        (queue_policy != "shared" && queue_policy != "independent")) {
        std::printf("Invalid scheduler or queue policy\n");
        return 1;
    }

    MFuzz mfuzz(bench_path, "honggfuzz", schedule, queue_policy, window_seconds, random_seed);
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
