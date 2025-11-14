#ifndef _DRIVER_H_
#define _DRIVER_H_

#include <string>
#include <vector>
#include <map>
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
    inline const string& getOutput() const { return output; }
    inline float getPriority() const { return priority; }
    inline const vector<string>& getArgv() const { return argv; }
    inline const string getOption() const { return argv[0]; }

    inline void setArgv(const vector<string>& args) { argv = args; }
    inline void setPriority(float priority) { this->priority = priority; }

    inline string toJson() const {
        json j = {
            {"id", id},
            {"name", name},
            {"driver", driver},
            {"args", argv},
            {"seed_dir", seed_dir},
            {"output", output},
            {"priority", priority},
            {"description", description}
        };
        return j.dump(4);
    }

private:
    int id;
    string name;
    string driver;
    string seed_dir;
    string output;
    float priority;
    string description;
    vector<string> argv;

private:
    bool parseArgs(const nlohmann::json& jargs);
    
};

#endif // _DRIVER_H_
