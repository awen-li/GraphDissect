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
#include "util.h"
#include "scheduler.h" 

namespace fs = std::filesystem;

class MFuzz 
{
public:
    MFuzz(std::string bench, const std::string& fuzzer)
        : bench_path(bench),
          fuzzer(fuzzer),
          stopped(false)
    {
        bench_path = UTIL::abs_path(bench_path);
        std::cout << "[MFuzz] benchmark path: " << bench_path << "\n";
        init_session();

        mfuzz_logfile = bench_path + "/mfuzz_f_coverage.log";
        std::error_code ec;
        fs::remove(mfuzz_logfile, ec);
    }

    ~MFuzz() 
    {
        
    }

    void start_fuzzer(double max_time_budget = 24 * 3600);
    void stop_fuzzer();

private:
    double check_fcov(double driver_time_budget);
    double fuzz_one_unit(const std::vector<unsigned>& driver_list, double time_budget);
    double fuzz_by_average(double max_time_budget, unsigned fuzzing_units = 12);
    void run_schedule_average(double max_time_budget);

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
        std::string fuzz_path = bench_path + "/fuzz";
        
        fs::path fuzz_dir = fs::absolute(fuzz_path);
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
    std::string bench_path;

    std::string fuzzer;
    pid_t fuzzer_pid;
    int    active_driver;

    std::unique_ptr<Scheduler> scheduler;
    std::string   session_id;
    fs::path      session_path;

    bool stopped;
    std::string mfuzz_logfile;

private:
    void logCoverage(const std::set<unsigned>& covered_funcs)
    {
        // get current timestamp (seconds since epoch)
        auto now = std::chrono::system_clock::now();
        auto ts  = std::chrono::duration_cast<std::chrono::seconds>(
                    now.time_since_epoch()).count();

        std::ofstream ofs(mfuzz_logfile, std::ios::out | std::ios::app);
        if (!ofs.is_open()) {
            // optional: handle error
            return;
        }

        ofs << ts << "," << covered_funcs.size() << "\n";
    }
};
