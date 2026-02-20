#include "mfuzz.h"


// Utility: check if a process matching name exists (like pgrep -f)
inline bool process_exists(const std::string& name = "honggfuzz") 
{
    std::string cmd = "pgrep -f " + name + " > /dev/null 2>&1";
    return std::system(cmd.c_str()) == 0;
}

void MFuzz::start_fuzzer(double max_time_budget) 
{
    // Change directory to benchmark
    fs::path absPath = fs::absolute(bench_path);
    if (!fs::exists(absPath) || !fs::is_directory(absPath)) {
        std::cerr << "[MFuzz] Benchmark path does not exist or is not a directory: "
                  << absPath << "\n";
        return;
    }

    if (chdir(absPath.c_str()) != 0) {
        std::perror("[MFuzz] chdir failed");
        return;
    }

    // Init scheduler and set default driver
    scheduler = std::make_unique<Scheduler>(bench_path, session_path.string());
    unsigned default_driver = 1;
    scheduler->setActiveDriver(default_driver, true);

    // Fuzz in/out directories
    auto [in_dir, out_dir] = init_fuzzDirectory();

    // Build honggfuzz command
    std::vector<std::string> args = {
        fuzzer,
        "-n", "1",
        "-X", session_path.string(),
        "-b", absPath.string(),
        "-i", in_dir.string(),
        "-o", out_dir.string(),
        "--timeout", "10",
        "--rlimit_rss", "2048",
        "-F", "10485760",
        "--", "fuzzPilot",
        "___FILE___"
    };

    // Export exact command for debugging
    try {
        std::string cmd_str;
        for (size_t i = 0; i < args.size(); ++i) {
            if (i) cmd_str += " ";
            cmd_str += UTIL::shell_quote(args[i]);
        }

        fs::path cmd_file = session_path / "hfuzz_cmd.txt";
        fs::path cwd_file = session_path / "cwd.txt";

        std::ofstream ofs_cmd(cmd_file);
        ofs_cmd << cmd_str << "\n";

        std::ofstream ofs_cwd(cwd_file);
        ofs_cwd << absPath.string() << "\n";

        std::cout << "[MFuzz][debug] wrote honggfuzz command to "
                  << cmd_file << "\n";
        std::cout << "[MFuzz][debug] working dir: "
                  << absPath << "\n";
    } 
    catch (const std::exception& e) {
        std::cerr << "[MFuzz][debug] failed to export command: "
                << e.what() << "\n";
    }

    // FP_DEBUG gate: do NOT start fuzzer; just wait until honggfuzz shows up
    if (std::getenv("FP_DEBUG") != nullptr) {
        while (true) {
            if (process_exists()) {
                break;
            }
            std::cout << "[FP_DEBUG] waiting for honggfuzz setup....\n";
            std::this_thread::sleep_for(std::chrono::milliseconds(500));
        }
        std::cout << "[FP_DEBUG] honggfuzz has been setup....\n";
        return;
    } 
    else {
        // Fork+exec to start fuzzer
        pid_t pid = fork();
        if (pid == -1) {
            std::perror("[MFuzz] fork failed");
            return;
        }

        if (pid == 0) {
            // Child: new process group (like preexec_fn=os.setsid)
            if (setsid() == -1) {
                std::perror("[MFuzz] setsid failed");
            }

            // Build argv for execvp
            std::vector<char*> c_argv;
            c_argv.reserve(args.size() + 1);
            for (auto& s : args) {
                c_argv.push_back(const_cast<char*>(s.c_str()));
            }
            c_argv.push_back(nullptr);

            execvp(c_argv[0], c_argv.data());
            std::perror("[MFuzz] execvp failed");
            std::exit(1);
        } 
        else {
            fuzzer_pid = pid;
            std::cout << "[MFuzz] [session - " << session_id
                    << "] fuzzer started for fuzzing on "
                    << bench_path << "\n";
            run_schedule_average(max_time_budget);
        }
    }
}

void MFuzz::stop_fuzzer() 
{
    stopped = true;
    scheduler->dump();

    if (fuzzer_pid > 0) {
        // Send SIGINT and wait
        kill(fuzzer_pid, SIGINT);
        int status = 0;
        waitpid(fuzzer_pid, &status, 0);
        std::cout << "[MFuzz] fuzzer stopped.\n";
        fuzzer_pid = -1;
    }
    
    if (!session_path.empty() && fs::exists(session_path)) {
        std::error_code ec;
        fs::remove_all(session_path, ec);
        if (ec) {
            std::cerr << "[MFuzz] failed to remove session path: "
                        << ec.message() << "\n";
        }
    }
}

double MFuzz::fuzz_one_unit(const std::vector<unsigned>& driver_list, double time_budget)
{
    double escape = 0.0;
    size_t driver_index = 0;

    double switch_interval = time_budget / driver_list.size();
    if (switch_interval < 1.0) {
        switch_interval = 1.0;
    }

    unsigned interval = 0;
    while (!stopped && escape < time_budget) {
        std::this_thread::sleep_for(
            std::chrono::milliseconds(static_cast<int>(1 * 1000))
            );
        
        interval++;
        if (interval < switch_interval) {
            continue;
        }

        interval = 0;
        escape  += switch_interval;

        driver_index = (driver_index + 1) % driver_list.size();
        active_driver = driver_list[driver_index];

        double start_time = UTIL::getCurrentTimeSec();
        scheduler->setActiveDriver(active_driver);
        escape += UTIL::getCurrentTimeSec() - start_time;
    }

    // log the coverage of this fuzzing unit: timestammp + number of covered funcs
    std::set<unsigned> covered_funcs = scheduler->getCoveredFuncs();
    logCoverage(covered_funcs);

    return escape;
}

double MFuzz::fuzz_by_average(double max_time_budget, unsigned fuzzing_units) 
{
    if (!scheduler) return 0.0;

    auto driver_list = scheduler->getAllDrvIds();
    if (driver_list.empty()) {
        std::cout << "No drivers are loaded!\n";
        stop_fuzzer();
        return 0.0;
    }

    std::cout << "@fuzz_by_average -> drivers: [";
    for (size_t i = 0; i < driver_list.size(); ++i) {
        std::cout << driver_list[i];
        if (i + 1 < driver_list.size()) std::cout << ", ";
    }
    std::cout << "], driver_num:" << driver_list.size()<< "\n";

    double escape = 0.0;
    double time_budget_per_unit = max_time_budget / fuzzing_units;
    for (unsigned unit = 0; unit < fuzzing_units; ++unit) {
        std::cout << "[fuzz_by_average] fuzzing unit " << (unit + 1)
                    << "/" << fuzzing_units << " ...\n";
        
        escape += fuzz_one_unit(driver_list,time_budget_per_unit);
        if (escape >= max_time_budget || stopped) {
            break;
        }
    }

    return escape;
}

void MFuzz::run_schedule_average(double max_time_budget) 
{
    if (fuzz_by_average(max_time_budget) == 0.0) {
        return;
    }

    set<unsigned> coved_funcs = scheduler->getCoveredFuncs();
    std::cout << "[run_schedule_average][" << coved_funcs.size()
                << "]coved_funcs -> [";
    for (auto it = coved_funcs.begin(); it != coved_funcs.end(); ++it) {
        std::cout << *it;
        if (std::next(it) != coved_funcs.end()) std::cout << ", ";
    }
    std::cout << "]\n";

    stop_fuzzer();
}
