#include <chrono>
#include <csignal>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <string>
#include <thread>
#include <utility>
#include <vector>
#include <unistd.h> 
#include <sys/types.h>
#include <sys/wait.h>
#include "scheduler.h" 

namespace fs = std::filesystem;

class MFuzz 
{
public:
    MFuzz(const std::string& fuzzer)
        : fuzzer(fuzzer),
          max_time_budget(0.0),
          total_time(0.0) 
    {
        init_session();
    }

    ~MFuzz() 
    {
        stop_fuzzer();
    }

    void start_fuzzer(const std::string& benchmark, int driverId = 0);
    void stop_fuzzer();

private:
    double check_fcov(double driver_time_budget);
    double fuzz_by_average(double max_time_budget);
    void run_schedule_average(double max_time = 24 * 3600);

    inline void init_session() 
    {
        session_id = std::to_string(static_cast<long long>(getpid()));
        session_path = fs::path("/tmp") / ("hfuzz_" + session_id);

        if (fs::exists(session_path)) {
            std::error_code ec;
            fs::remove_all(session_path, ec);
        }
        fs::create_directories(session_path);
    }

    inline std::pair<fs::path, fs::path> init_fuzzDirectory() 
    {
        fs::path fuzz_dir = fs::absolute("./fuzz");
        if (!fs::exists(fuzz_dir)) {
            fs::create_directories(fuzz_dir);
        }

        fs::path fuzz_in  = fuzz_dir / "in";
        fs::path fuzz_out = fuzz_dir / "out";

        if (!fs::exists(fuzz_in)) {
            fs::create_directories(fuzz_in);
        }
        if (!fs::exists(fuzz_out)) {
            fs::create_directories(fuzz_out);
        }

        return {fuzz_in, fuzz_out};
    }

private:
    std::string fuzzer;
    pid_t fuzzer_pid;

    std::unique_ptr<Scheduler> scheduler;
    std::string   session_id;
    fs::path      session_path;

    int    active_driver;
    double max_time_budget;
    double total_time;
};
