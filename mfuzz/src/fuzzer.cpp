#include <iostream>
#include <vector>
#include <fstream>
#include <sstream>
#include <cerrno>
#include <cstring>
#include <csignal>
#include <unistd.h>
#include <sys/wait.h>
#include "util.h"
#include "fuzzer.h"

#include <filesystem>
namespace fs = std::filesystem;

#include <nlohmann/json.hpp>
using nlohmann::json;


void FuzzerBackend::deInitSession()
{
    if (session_path.empty()) {
        return;
    }

    std::error_code ec;
    fs::path p = fs::path(session_path).lexically_normal();

    if (!fs::exists(p, ec)) {
        return;
    }

    //(void)fs::remove_all(p, ec);
    return;
}

bool HonggfuzzBackend::initFuzzDirectory(std::string& err)
{
    std::error_code ec;

    // fuzz
    std::string fuzz_dir = benchmark_path + "/" + "fuzz";
    if (!UTIL::createDir(fuzz_dir, err)) {
        return false;
    }
    
    //fuzz/in
    in_dir = fuzz_dir + "/" + "in";
    if (!UTIL::createDir(in_dir, err)) {
        return false;
    }

    //fuzz/out
    out_dir = fuzz_dir + "/" + "out";
    if (!UTIL::createDir(out_dir, err)) {
        return false;
    }
    
    return true;
}

bool HonggfuzzBackend::initSession(std::string& err)
{
    pid_t pid = getpid();
    session_id = std::to_string(pid);
    session_path = "/tmp/specdrive_" + session_id;

    std::error_code ec;
    if (fs::exists(session_path, ec)) {
        fs::remove_all(session_path, ec);
        if (ec) {
            err = "failed to remove existing session path: " + ec.message();
            return false;
        }
    }

    if (!fs::create_directories(session_path, ec)) {
        err = "failed to create session path: " + ec.message();
        return false;
    }

    // init fcov / active driver path
    fcov_map_path      = session_path + "/fcov.map";
    active_driver_path = session_path + "/active_driver.drv";

    std::cout<<"[HonggfuzzBackend] session initialized at: " << session_path << "\n";
    std::cout<<"[HonggfuzzBackend] fcov map path: " << fcov_map_path << "\n";
    std::cout<<"[HonggfuzzBackend] active driver path: " << active_driver_path << "\n";

    return true;
}

bool HonggfuzzBackend::init(std::string& err)
{
    // init fuzzing session
    if (!initSession(err)) {
        return false;
    }

    // get fuzzer bin
    if (!UTIL::findFuzzerBin("honggfuzz", honggfuzz_bin, err)){
        return false;
    }

    // init fuzzing dir
    if (!initFuzzDirectory(err)) {
        return false;
    }

    return true; 
}

bool HonggfuzzBackend::startRun(std::string bench_path, std::string& err)
{
    if (bench_path.empty()) {
        err = "benchmark path is not specified";
        return false;
    }

    this->benchmark_path = UTIL::getAbsPath(bench_path, err);
    if (this->benchmark_path == ""){
        return false;
    }

    // Build honggfuzz command (mirrors Python)
    // Example:
    // honggfuzz -n 1 -X <session_path> -b <benchmark_path> -i <in_dir> -o <out_dir>
    //           --timeout 10 --rlimit_rss 2048 -F 1048576 -- fuzzPilot ___FILE___
    std::vector<std::string> args_vec;
    args_vec.push_back(honggfuzz_bin);
    args_vec.push_back("-n"); args_vec.push_back("1");
    args_vec.push_back("-X"); args_vec.push_back(session_path);
    args_vec.push_back("-b"); args_vec.push_back(benchmark_path);
    args_vec.push_back("-i"); args_vec.push_back(in_dir);
    args_vec.push_back("-o"); args_vec.push_back(out_dir);

    // hard coding here
    args_vec.push_back("--timeout");    args_vec.push_back(std::to_string(10));
    args_vec.push_back("--rlimit_rss"); args_vec.push_back(std::to_string(2048));
    args_vec.push_back("-F"); args_vec.push_back("1048576");

    // Separator then target
    args_vec.push_back("--");
    args_vec.push_back("fuzzPilot");
    args_vec.push_back("___FILE___");

    // Persist full command for debugging
    std::ostringstream oss_cmd;
    for (size_t i = 0; i < args_vec.size(); ++i) {
        oss_cmd << args_vec[i];
        if (i + 1 != args_vec.size()) oss_cmd << ' ';
    }

    std::string cmd_file = (fs::path(session_path) / "hfuzz_cmd.txt").string();
    std::string cmd_str = oss_cmd.str() + "\n";
    if (!UTIL::writeTextFile(cmd_file, cmd_str, err)) {
        return false;
    }

    // chdir to benchmark directory
    if (chdir(benchmark_path.c_str()) != 0) {
        err = std::string("chdir failed: ") + std::strerror(errno);
        return false;
    }

    // Build argv** for execvp
    std::vector<char*> argv_exec;
    for (size_t i = 0; i < args_vec.size(); ++i) {
        argv_exec.push_back(const_cast<char*>(args_vec[i].c_str()));
    }
    argv_exec.push_back(nullptr);

    // Fork & exec; child will call setsid() (own process group)
    pid_t pid = fork();
    if (pid < 0) {
        err = std::string("fork failed: ") + std::strerror(errno);
        return false;
    }

    if (pid == 0) {
        setsid();
        execvp(argv_exec[0], &argv_exec[0]);
        _exit(127);
    }
    else {
        // Parent
        child_pid = pid;
        return true;
    }
}

std::optional<RunResult> HonggfuzzBackend::collectResult(int timeout_ms)
{
    RunResult rr;
    rr.finished = false;
    rr.crash = false;
    rr.output.clear();
    rr.exit_code = 0;
    rr.seed_path.clear();

    if (child_pid <= 0) {
        // Nothing running; consider it finished successfully
        rr.finished = true;
        return rr;
    }

    int elapsed_ms = 0;
    const int step_ms = 50;

    for (;;) {

        int status = 0;
        pid_t res = waitpid(child_pid, &status, WNOHANG);
        if (res == child_pid) {
            rr.finished = true;
            if (WIFEXITED(status)) {
                rr.exit_code = WEXITSTATUS(status);
            }
            else if (WIFSIGNALED(status)) {
                rr.exit_code = 128 + WTERMSIG(status);
                // Treat signal exits as crashes (heuristic)
                rr.crash = true;
            }
            child_pid = -1;
            return rr;
        }
        else if (res == 0) {
            // Still running
            if (elapsed_ms >= timeout_ms)
            {
                return std::nullopt;
            }
            usleep(step_ms * 1000);
            elapsed_ms += step_ms;
        }
        else {
            // waitpid error; treat as finished with error code
            rr.finished = true;
            rr.exit_code = 1;
            child_pid = -1;
            return rr;
        }
    }
}

bool HonggfuzzBackend::stopRun(int run_id, std::string& err)
{
    (void)run_id;

    if (child_pid <= 0) {
        return true;
    }

    // Send SIGTERM to the process group
    if (kill(-child_pid, SIGTERM) != 0) {
        // Fallback to the child itself
        if (kill(child_pid, SIGTERM) != 0) {
            err = std::string("failed to signal process: ") + std::strerror(errno);
            return false;
        }
    }

    // Give it a short grace period
    int elapsed_ms = 0;
    const int timeout_ms = 1000;
    const int step_ms = 50;

    for (;;) {

        int status = 0;
        pid_t res = waitpid(child_pid, &status, WNOHANG);
        if (res == child_pid) {
            child_pid = -1;
            return true;
        }

        if (elapsed_ms >= timeout_ms) {
            break;
        }

        usleep(step_ms * 1000);
        elapsed_ms += step_ms;
    }

    // Force kill
    kill(-child_pid, SIGKILL);
    kill(child_pid, SIGKILL);
    child_pid = -1;

    return true;
}

void HonggfuzzBackend::shutdown()
{
    std::string err;
    (void)stopRun(0, err);
}
