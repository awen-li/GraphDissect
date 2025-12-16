#ifndef _DRIVER_H_
#define _DRIVER_H_

#include <string>
#include <map>
#include <queue>
#include <vector>
#include <functional>
#include <utility>
#include <nlohmann/json.hpp>

using namespace std;
using json = nlohmann::json;

class Driver {
public:
    Driver() {}
    ~Driver() {}

    bool load(string drvPath);
    bool dump(string drvPath);

    // Getters (optional, for access outside the class)
    inline int getId() const { return id; }
    inline const string& getName() const { return name; }
    inline const string& getDriver() const { return driver; }
    inline const string& getSeedDir() const { return seed_dir; }
    inline float getPriority() const { return priority; }
    inline const vector<string>& getArgv() const { return argv; }
    inline const string getOption() const { return argv[0]; }

    inline void setArgv(const vector<string>& args) { argv = args; }
    inline void setPriority(float priority) { this->priority = priority; }
    inline void setPhase(const int phase) { this->phase = phase; }

    inline string toJson() const {
        json j = {
            {"id", id},
            {"name", name},
            {"driver", driver},
            {"args", argv},
            {"output", output},
            {"seed_dir", seed_dir},
            {"priority", priority},
            {"description", description}
        };
        return j.dump(4);
    }

    bool loadRuntimeStat();

    inline uint32_t getEdges() const { return edges; }
    inline uint32_t getEdgeDelta() const { return edges_delta; }
    inline uint32_t getCrashes() const { return crashes; }
    inline uint32_t getCrashDelta() const { return crashes_delta; }
    inline uint64_t getExecs() const { return execs; }
    inline time_t getTimeElapsed() const { return time_elapsed; }

private:
    int id;
    string name;
    string driver;
    string seed_dir;
    string output;
    float priority;
    string description;
    vector<string> argv;

    int phase = 0;  // 0: pilot, 1: dynamic, 2: fallback
    int in_place_edit = 0; // 0: disable, 1: enable

private:
    // runtime stat
    uint32_t edges = 0;
    uint32_t edges_delta = 0;
    uint32_t crashes = 0;
    uint32_t crashes_delta = 0;
    uint64_t execs = 0;
    time_t time_elapsed = 0;

private:
    bool parseArgs(const nlohmann::json& jargs);
};

using DriverHeapEntry = std::pair<float, int>;  // (priority, driverId)

struct DriverCmp {
    bool operator()(const DriverHeapEntry& a, const DriverHeapEntry& b) const {
        return a.first < b.first;  // max-heap: higher priority first
    }
};


class DriverMng {
public:
    DriverMng() = default;
    ~DriverMng() = default;

    DriverMng(string bench, unsigned sessionId)
        : benchmark(std::move(bench)), sessionId(sessionId) {
            activeDrvId = 0;
        }
public: 
    bool loadDrivers();

    Driver& getDriver(unsigned drvId);

    unsigned getPriorDriver();
    unsigned getDriverNum();
    vector<unsigned> getAllDrvIds();

    bool setActiveDriver(string activeDrvPath, unsigned driverId, int phase=0);
    bool setDriverPriority(unsigned driverId, float priority);

private:
    bool waitForDriverLoad(const string& activeDrvPath, int timeout_sec = 15);
    bool loadDriverList(const string& path = "drivers/driver_list.json");
    void printDrivers() const;

private:
    unsigned drvFailedNum = 0;
    string benchmark;
    unsigned sessionId;
    unsigned activeDrvId;
    map<int, Driver> allDrivers;

    priority_queue<DriverHeapEntry, vector<DriverHeapEntry>, DriverCmp> driverHeap;

};

#endif // _DRIVER_H_

