#include "util.h"

namespace UTIL {

namespace fs = std::filesystem;
bool ensureDir(const std::string& p, std::string& err)
{
    std::error_code ec;

    if (p.empty()) {
        err = "empty directory path";
        return false;
    }

    if (fs::exists(p, ec)) {
        if (!fs::is_directory(p, ec)) {
            err = "path exists but is not a directory: " + p;
            return false;
        }
        return true;
    }

    if (!fs::create_directories(p, ec)) {
        err = "failed to create directory: " + p + " (" + ec.message() + ")";
        return false;
    }

    return true;
}

bool writeTextFile(const std::string& path, const std::string& txt, std::string& err)
{
    std::ofstream ofs(path.c_str(), std::ios::binary | std::ios::trunc);
    if (!ofs) {
        err = "cannot open file for write: " + path;
        return false;
    }

    ofs.write(txt.data(), static_cast<std::streamsize>(txt.size()));
    if (!ofs) {
        err = "failed to write file: " + path;
        return false;
    }
    return true;
}

std::string getAbsPath(const std::string& path, std::string& err)
{
    std::error_code ec;

    fs::path base = fs::path(path);
    fs::path abs_base = fs::absolute(base, ec);
    if (ec) {
        err = "failed to get absolute path for: "+ path + " " + ec.message();
        return "";
    }
    abs_base = abs_base.lexically_normal(); 

    return abs_base.string();
}

bool createDir(const std::string& path, std::string& err)
{
    std::error_code ec;

    fs::path base = fs::path(path);
    fs::path abs_base = fs::absolute(base, ec);
    if (ec) {
        err = "failed to get absolute path for: "+ path + " " + ec.message();
        return false;
    }

    if (fs::exists(abs_base)) {
        return true;
    }

    if (!fs::create_directories(abs_base, ec)) {
        err = "failed to create fuzz dir at " + abs_base.string() + ": " + ec.message();
        return false;
    }

    return true;
}

bool findFuzzerBin(std::string fuzzName, std::string& out_path, std::string& err)
{
    const char* env_path = std::getenv("PATH");
    if (!env_path)
    {
        err = "PATH not set";
        return false;
    }

    std::string path_env(env_path);

    size_t start = 0;
    while (true)
    {
        size_t end = path_env.find(':', start);
        std::string dir = (end == std::string::npos)
                            ? path_env.substr(start)
                            : path_env.substr(start, end - start);

        std::filesystem::path candidate = fs::path(dir) / fuzzName;
        std::error_code ec;
        if (fs::exists(candidate, ec) && fs::is_regular_file(candidate, ec))
        {
            out_path = candidate.string();
            return true;
        }

        if (end == std::string::npos)
        {
            break;
        }
        start = end + 1;
    }

    err = "honggfuzz not found in PATH";
    return false;
}


std::string shell_quote(const std::string& s) 
{
    std::string out = "'";
    for (char c : s) {
        if (c == '\'') {
            out += "'\"'\"'";
        } else {
            out += c;
        }
    }
    out += "'";
    return out;
}

}