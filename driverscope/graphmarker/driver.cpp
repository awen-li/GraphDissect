#include "driver.h"
#include <fstream>
#include <iostream>
#include <filesystem>
#include <cassert>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

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
