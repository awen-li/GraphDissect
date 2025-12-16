#include "driver.h"
#include <fstream>
#include <iostream>
#include <filesystem>
#include <cassert>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <thread>
#include <chrono>

using json = nlohmann::json;
using namespace std;

bool Driver::load(string drvPath) {
    json root;
    try {
        ifstream file(drvPath);
        if (!file.is_open()) {
            cerr << "Failed to open file: " + drvPath << "\n";
            return false;
        }
        file >> root;
    } catch (const exception& e) {
        cerr << "Failed to parse JSON: " + drvPath << e.what() << "\n";
        return false;
    }

    try {
        id       = root["id"].get<int>();
        name     = root["name"].get<string>();
        driver   = root["driver"].get<string>();
        seed_dir = root["seed_dir"].get<string>();
        output   = root["output"].get<string>();
        priority = root["priority"].get<float>();
        description = root["description"].get<string>();

        if (!parseArgs(root["args"])) return false;

        if (root.find("in_place_editing") != root.end()) {
            in_place_edit = root["in_place_editing"].get<int>();
        }

        return true;

    } catch (const exception& e) {
        cerr << "Exception while extracting driver fields: " << e.what() << "\n";
        return false;
    }
}

bool Driver::parseArgs(const json& jargs) {
    if (!jargs.is_array()) return false;
    for (const auto& arg : jargs) {
        if (arg.is_string()) argv.push_back(arg.get<string>());
    }
    return true;
}

bool Driver::dump (string drvPath) {
    std::ofstream out(drvPath);
    if (!out.is_open()) {
        std::cerr << "[!] Failed to open " << drvPath << " for writing.\n";
        return false;
    }

    out << toJson() << std::endl;
    out.close();

    //std::cout << "[+] Dumped " << drvPath + "\n";
    return true;
}


bool Driver::loadRuntimeStat() {
    string statPath = "driver_runtimes/" + to_string(id);
    ifstream ifs(statPath);
    if (!ifs) {
        cerr << "Failed to open runtime stat file: " << statPath << "\n";
        return false;
    }

    string line;
    while (getline(ifs, line)) {
        istringstream iss(line);
        string key;
        if (getline(iss, key, ':')) {
            string value_part;
            if (getline(iss, value_part)) {
                size_t delta_pos = value_part.find("(+");
                string val_str = value_part.substr(0, delta_pos);
                uint64_t value = stoull(val_str);

                if (key == "edges") {
                    edges = value;
                    if (delta_pos != string::npos) {
                        edges_delta = stoul(value_part.substr(delta_pos + 2));
                    }
                } else if (key == "crashes") {
                    crashes = value;
                    if (delta_pos != string::npos) {
                        crashes_delta = stoul(value_part.substr(delta_pos + 2));
                    }
                } else if (key == "time") {
                    time_elapsed = value;
                } else if (key == "exes") {
                    execs = value;
                }
            }
        }
    }

    return true;
}


bool DriverMng::loadDriverList(const string& path) {
    json root;
    try {
        ifstream file(path);
        if (!file.is_open()) {
            throw runtime_error("Could not open file");
        }
        file >> root;
    } catch (const exception& e) {
        cerr << "Failed to parse JSON: " << e.what() << "\n";
        return false;
    }

    if (root.find("drivers") == root.end() || !root["drivers"].is_array()) return false;

    for (const auto& entry : root["drivers"]) {
        if (!entry.is_object() || entry.size() != 1) continue;

        // Extract id and name
        auto it = entry.begin();
        unsigned driverId = std::stoul(it.key());
        std::string name = it.value();

        std::string drvPath = "drivers/" + name + "/" + name + ".json";

        Driver drv;
        drv.load(drvPath);
        allDrivers[driverId] = drv;

        // insert to heap
        driverHeap.push({drv.getPriority(), driverId});
    }

    //printDrivers();
    return true;
}


bool DriverMng::loadDrivers() {
    string drvListPath = "drivers/driver_list.json";
    return loadDriverList (drvListPath);
}

void DriverMng::printDrivers() const {
    for (const auto& [id, item] : allDrivers) {
        cout << "Driver[" << item.getId() << "]: name=" << item.getName()
             << ", bin=" << item.getDriver() << ", seed=" << item.getSeedDir()
             << ", priority=" << item.getPriority() << "\n";
    }
}


bool DriverMng::waitForDriverLoad(const string& activeDrvPath, int timeout_sec) {
    int waited = 0;
    const int interval_ms = 50;

    while (waited < timeout_sec * 1000) {
        if (access(activeDrvPath.c_str(), F_OK) == -1) {
            // File no longer exists → driver is loaded
            drvFailedNum = 0;
            return true;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(interval_ms));
        waited += interval_ms;
    }

    std::cerr << "[Scheduler] Timeout waiting for driver to be loaded.\n";
    drvFailedNum++;
    if (drvFailedNum > 3) {
        std::cerr << "[Scheduler] Timeout times for " <<drvFailedNum<< " times, exit abnormally\n";
        exit(1);
    }
    return false;
}


bool DriverMng::setActiveDriver(string activeDrvPath, 
                                unsigned driverId,
                                int phase) {
    auto it = allDrivers.find(driverId);
    if (it == allDrivers.end()) {
        std::cerr << "Driver ID " << driverId << " not found in driver map.\n";
        return false;
    }
    Driver& drv = it->second;
    drv.setPhase(phase);
    string activeDrv = drv.toJson();

    int fd = open(activeDrvPath.c_str(), O_WRONLY | O_NONBLOCK| O_CREAT | O_TRUNC, 0644);
    if (fd == -1) {
        cerr << "Failed to open "<< activeDrvPath <<"\n";
        return false;
    }

    ssize_t written = write(fd, activeDrv.c_str(), activeDrv.size());
    if (written == -1) {
        cerr << "Write to "<< activeDrvPath <<" failed \n";
        close(fd);
        return false;
    }
    close(fd);

    if (activeDrvId != 0) {
        waitForDriverLoad(activeDrvPath);
    }   
    activeDrvId = driverId;

    // debug
    //fd = open("current_active_driver.json", O_WRONLY | O_NONBLOCK| O_CREAT | O_TRUNC, 0644);
    //write(fd, activeDrv.c_str(), activeDrv.size());
    //close(fd);
    
    return true;
}


unsigned DriverMng::getPriorDriver() {
    auto [priority, drvId] = driverHeap.top();
    driverHeap.pop();

    return drvId;
}

bool DriverMng::setDriverPriority(unsigned driverId, float priority) {
    auto itr = allDrivers.find(driverId);
    if (itr == allDrivers.end()) {
        cerr << "Fail to get driver: "<< driverId <<"\n";
        return false;
    }

    Driver& drv = itr->second;
    drv.setPriority(priority);

    driverHeap.push({priority,driverId});
    return true;
}

unsigned DriverMng::getDriverNum() {
    return allDrivers.size();
}


vector<unsigned> DriverMng::getAllDrvIds() {
    vector<std::pair<unsigned, Driver>> sortedDrivers(allDrivers.begin(), allDrivers.end());

    // Sort by priority in descending order
    std::sort(sortedDrivers.begin(), sortedDrivers.end(),
              [](const auto& a, const auto& b) {
                  return a.second.getPriority() > b.second.getPriority();
              });

    // Collect sorted IDs
    vector<unsigned> allDrvIds;
    for (const auto& pair : sortedDrivers) {
        allDrvIds.push_back(pair.first);
    }

    return allDrvIds;
}


Driver& DriverMng::getDriver(unsigned drvId) {
    auto itr = allDrivers.find(drvId);
    assert(itr != allDrivers.end());

    return itr->second;
}