#pragma once
#include <string>
#include <fstream>
#include <filesystem>

namespace UTIL {

bool ensureDir(const std::string& p, std::string& err);

bool writeTextFile(const std::string& path, const std::string& txt, std::string& err);

std::string getAbsPath(const std::string& path, std::string& err);

bool createDir(const std::string& path, std::string& err);

bool findFuzzerBin(std::string fuzzName, std::string& out_path, std::string& err);

}