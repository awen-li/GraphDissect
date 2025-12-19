#pragma once
#include <string>
#include <optional>
#include <iostream>

struct RunResult
{
    bool finished = true;
    bool crash = false;
    std::string output;
    int exit_code = 0;
    std::string seed_path;
};

class FuzzerBackend
{
public:
    virtual ~FuzzerBackend() = default;

    virtual bool startRun(std::string bench_path, std::string& err)
    {
        (void)bench_path;
        return true;
    }

    virtual std::optional<RunResult> collectResult(int timeout_ms=3000)
    {
        (void)timeout_ms;
        return RunResult{};
    }

    virtual bool stopRun(int run_id, std::string& err)
    {
        (void)run_id;
        (void)err;
        return true;
    }

    virtual std::string getActiveDrvPath () = 0;
    virtual std::string getSessionPath () = 0;
    virtual std::string getFCovPath () = 0;
    virtual void shutdown() {}

    virtual bool init(std::string& err)
    {
        (void)err;
        return true;
    }

protected:
    //session
    std::string session_id;
    std::string session_path;

    //fcov and driver @ session
    std::string fcov_map_path;
    std::string active_driver_path;

    //benchmark
    std::string benchmark_path;
    
    //fuzzing
    std::string in_dir;
    std::string out_dir;

protected:
    virtual bool initSession(std::string& err)
    {
        (void)err;
        return true;
    }

    void deInitSession();
};


class HonggfuzzBackend : public FuzzerBackend
{
public:
    HonggfuzzBackend() {
        std::string err;
        if (!init(err)) {
            std::cerr << "[HonggfuzzBackend] init failed: " << err << "\n";
            exit(1);
        }
    }

    ~HonggfuzzBackend() {
        deInitSession();
    }

    inline std::string getActiveDrvPath ()
    {
        return active_driver_path;
    }

    inline std::string getSessionPath ()
    {
        return session_path;
    }

    inline std::string getFCovPath ()
    {
        return fcov_map_path;
    }

    bool startRun(std::string bench_path, std::string& err) override;
    std::optional<RunResult> collectResult(int timeout_ms=3000) override;

    bool stopRun(int run_id, std::string& err) override;
    void shutdown() override;

private:
    std::string honggfuzz_bin;

    // Process info
    pid_t child_pid = -1;

private:
    bool init(std::string& err) override;

    bool initSession(std::string& err) override;

    bool initFuzzDirectory(std::string& err);
};

