#ifndef _FADDR_ID_H_
#define _FADDR_ID_H_

/*
 * Parsing faddr_id.map
 * Lines like:
 *   0x436060 1
 *   0x436f90 2
 *   0x437000 3
 *   ...
 * First column: function address in hex (0x...).
 * Second column: integer ID (1-based).
 */

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>
#include <fstream>
#include <sstream>
#include <iostream>

class FaddrID 
{
public:
    FaddrID() = default;

    explicit FaddrID(const std::string& path) {
        load(path);
    }

    // Return the ID for this address (0 if not found)
    unsigned addrToId(uintptr_t addr) const {
        if (addr2id_.empty()) {
            return 0;
        }
        uint32_t a32 = packAddr(addr);
        auto it = addr2id_.find(a32);
        if (it == addr2id_.end()) {
            return 0;
        }
        return it->second;
    }

    // Return the address (as uintptr_t) for this ID (0 if not found)
    uintptr_t idToAddr(unsigned id) const {
        if (id == 0 || id >= id2addr_.size()) {
            return 0;
        }
        return static_cast<uintptr_t>(id2addr_[id]);
    }

    // Number of entries (max valid ID)
    std::size_t size() const {
        return id2addr_.size() > 0 ? (id2addr_.size() - 1) : 0;
    }

private:
    // low-32-bit address -> ID
    std::unordered_map<uint32_t, unsigned> addr2id_;
    // ID -> low-32-bit address; id2addr_[0] is unused
    std::vector<uint32_t> id2addr_;

private:
    static inline uint32_t packAddr(uintptr_t addr) {
        // Your addresses currently fit into low 32 bits.
        return static_cast<uint32_t>(addr & 0xffffffffu);
    }

    // Parse a faddr_id.map file.
    // Returns true on success (file opened), even if some lines are skipped.
    bool load(const std::string& path) {
        addr2id_.clear();
        id2addr_.clear();
        id2addr_.push_back(0); // index 0 unused so that index == ID

        std::ifstream in(path);
        if (!in) {
            std::cerr << "[FaddrID] Failed to open " << path << "\n";
            exit(1);
        }

        std::string line;
        unsigned lineNo = 0;
        while (std::getline(in, line)) {
            ++lineNo;
            if (line.empty()) {
                continue;
            }

            std::istringstream iss(line);
            std::string addrStr;
            unsigned id = 0;

            if (!(iss >> addrStr >> id)) {
                std::cerr << "[FaddrID] Parse error at line " << lineNo
                          << " in " << path << ": " << line << "\n";
                continue;
            }

            // Parse hex address string like "0x436060"
            uintptr_t addr = 0;
            try {
                addr = static_cast<uintptr_t>(
                    std::stoull(addrStr, nullptr, 16)
                );
            } catch (...) {
                std::cerr << "[FaddrID] Invalid address at line " << lineNo
                          << ": " << addrStr << "\n";
                continue;
            }

            uint32_t a32 = packAddr(addr);

            // addr -> id
            addr2id_[a32] = id;

            // id -> addr (ensure vector large enough)
            if (id >= id2addr_.size()) {
                id2addr_.resize(id + 1, 0);
            }
            id2addr_[id] = a32;
        }

        return true;
    }
};

#endif // _FADDR_ID_H_
