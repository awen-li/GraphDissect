#include <cmath>
#include <unordered_map>
#include "cgmarker.h"

CGGraph* CgMarker::getWholeCg() {
    return &wholeCg;
}

unsigned CgMarker::countPrivateNodes(unsigned driverId) {
    unsigned count = 0;
    for (auto itr = wholeCg.begin(); itr != wholeCg.end(); ++itr) {
        CGNode* node = itr->second;
        if (node->HasDriverId(driverId) && node->GetDriverIdMask().count() == 1) {
            count++;
        }
    }
    return count;
}


void CgMarker::getDriverGraph(unsigned driverId, set<CGNode*>& drvNodes) {
    ;
    for (auto itr = wholeCg.begin(); itr != wholeCg.end(); ++itr) {
        CGNode* node = itr->second;
        if (node->HasDriverId(driverId)) {
            drvNodes.insert(node);
        }
    }
    return;
}


float CgMarker::computeDriverScore(CGGraph* drvCg, unsigned drvId) {

    // Scoring weights
    const float alpha = 0.1;  // total node count
    const float beta  = 0.6;  // private node count
    const float gamma = 0.3;  // graph depth

    // Total subgraph size
    unsigned totalNodes = drvCg->GetNodeNum();

    // Private node count
    unsigned privateNodes = countPrivateNodes(drvId);

    // Max call depth from any entry
    unsigned graphDepth   = drvCg->ComputeNodeDepths();

    // Compute weighted score
    float score = alpha * totalNodes + beta * privateNodes + gamma * graphDepth;
    return score;
}


void CgMarker::dump(string markGraph) {
    // dump the masked graph
    string markedGraph = benchPath + "/" + markGraph;
    CGViz gv ("driver-marked-callgraph", &wholeCg, markedGraph);
    gv.WiteGraph();
    return;
}


void CgMarker::markGraph(CGGraph* drvCg, unsigned drvId) {
    std::lock_guard<std::mutex> lock(cg_mutex); 
    
    for (auto itr = drvCg->begin(); itr != drvCg->end(); ++itr) {
        CGNode* drvNode = itr->second;
        const string& fname = drvNode->GetFName();

        // Also label corresponding node in wholeCg
        CGNode* wholeNode = wholeCg.GetNode(fname);
        if (!wholeNode) {
            //std::cerr << "[!] Missing node in wholeCg: " << fname << "\n";
            continue;
        }
        wholeNode->SetDriverIdMask(drvId);
    }
    return;
}

void CgMarker::reportGlobalStats(std::ostream& os) {
    size_t totalNodes = 0;
    size_t labeledNodes = 0;
    std::map<size_t, size_t> overlapHistogram;
    size_t driverSum = 0;
    size_t maxDrivers = 0;

    std::vector<size_t> driverCounts;

    for (auto itr = wholeCg.begin(); itr != wholeCg.end(); ++itr) {
        CGNode* node = itr->second;
        totalNodes++;

        size_t count = node->GetDriverIdMask().count();
        if (count > 0) {
            labeledNodes++;
            driverSum += count;
            driverCounts.push_back(count);
            overlapHistogram[count]++;
            maxDrivers = std::max(maxDrivers, count);
        }
    }

    double mean = labeledNodes > 0 ? static_cast<double>(driverSum) / labeledNodes : 0.0;

    double variance = 0.0;
    for (size_t count : driverCounts) {
        variance += (count - mean) * (count - mean);
    }
    double stddev = labeledNodes > 0 ? std::sqrt(variance / labeledNodes) : 0.0;

    os << "\n============ Global Driver Statistics ============\n";
    os << "Total nodes in wholeCg: " << totalNodes << "\n";
    os << "Total labeled nodes:    " << labeledNodes << " (" << labeledNodes*100.0/totalNodes << "%)\n";
    os << "Max drivers per node:   " << maxDrivers << "\n";
    os << "Mean drivers per node:  " << mean << "\n";
    os << "Stddev drivers per node:" << stddev << "\n";

    os << "\n[Driver count per node histogram]\n";
    for (auto itr = overlapHistogram.begin(); itr != overlapHistogram.end(); itr++) {
        size_t count = itr->first;
        size_t freq  = itr->second;
        os << "  Nodes shared by " << count << " driver(s): " << freq << "/" << totalNodes << " -> "<<freq*100.0/totalNodes <<"%\n";
    }
}


static std::set<unsigned> parseDriverIdSet(const std::string& drvIDs) {
    std::set<unsigned> idSet;

    // Replace commas with spaces to unify separators
    std::string normalized = drvIDs;
    std::replace(normalized.begin(), normalized.end(), ',', ' ');

    std::stringstream ss(normalized);
    std::string token;

    while (ss >> token) {  // automatically skips repeated spaces
        try {
            unsigned id = std::stoul(token);
            idSet.insert(id);
        } catch (...) {
            // ignore non-numeric tokens if any malformed input
        }
    }

    return idSet;
}


// mask: driver bitmask (e.g., std::bitset<N>)
// idSet: optional filter; if empty => count all, else only count IDs in the set.
static unsigned getDriverCount(const boost::dynamic_bitset<>& mask, const std::set<unsigned>& idSet) {
    // No filter: just count all bits
    if (idSet.empty()) {
        return static_cast<unsigned>(mask.count());
    }

    // With filter: count only driver IDs in idSet
    unsigned cnt = 0;
    for (size_t i = 0; i < mask.size(); ++i) {
        if (!mask.test(i)) continue;
        unsigned driverId = static_cast<unsigned>(i + 1);
        if (idSet.find(driverId) != idSet.end()) {
            ++cnt;
        }
    }
    return cnt;
}

void CgMarker::reportPerDriverStats(std::ostream& os, std::string drvIDs) {
    std::map<unsigned, size_t> totalCount;
    std::map<unsigned, size_t> privateCount;
    std::map<unsigned, size_t> sharedCount;
    std::set<CGNode*> uncovered;

    std::set<unsigned> idSet = parseDriverIdSet(drvIDs);

    for (auto itr = wholeCg.begin(); itr != wholeCg.end(); ++itr) {
        CGNode* node = itr->second;
        const auto& mask = node->GetDriverIdMask();

        size_t driverCount = getDriverCount (mask, idSet);
        if (driverCount == 0) {
            uncovered.insert(node);
            continue;
        }

        for (size_t i = 0; i < mask.size(); ++i) {
            if (!mask.test(i)) continue;

            unsigned driverId = i + 1;
            if (idSet.size() != 0) {
                if (idSet.find (driverId) == idSet.end()) {
                    continue;
                }
            }
            
            totalCount[driverId]++;
            if (driverCount == 1)
                privateCount[driverId]++;
            else
                sharedCount[driverId]++;
        }
    }

    os << "\n============ Per-Driver Subgraph Statistics ============\n";
    os << "DriverID  #Nodes  #Private  #Shared  Private%  Shared%\n";

    for (auto itr = totalCount.begin(); itr != totalCount.end(); itr++) {
        size_t driverId = itr->first;
        size_t total    = itr->second;

        size_t priv = privateCount[driverId];
        size_t shared = sharedCount[driverId];
        double privPct = static_cast<double>(priv) / total;
        double sharedPct = static_cast<double>(shared) / total;

        os << std::setw(8) << driverId << "  "
           << std::setw(7) << total << "  "
           << std::setw(8) << priv << "  "
           << std::setw(7) << shared << "  "
           << std::fixed << std::setprecision(2)
           << std::setw(9) << privPct << "  "
           << std::setw(8) << sharedPct << "\n";
    }

    //os << "\n============ Uncovered Nodes ============\n";
    //for (auto itr = uncovered.begin(); itr != uncovered.end(); itr++) {
    //    CGNode* node = *itr;
    //    cout<<node->GetFName()<<", Incoming Node Number: "<<node->GetIncomingEdgeNum()<<"\n";
    //}
}

// In cgmarker.cpp

void CgMarker::reportDriverGraph(std::ostream& os,
                                 const std::string& outDir /* = "." */) 
{
    // Per-driver node lists
    std::map<unsigned, std::vector<CGNode*> > driverNodes;

    for (auto itr = wholeCg.begin(); itr != wholeCg.end(); ++itr) {
        CGNode* node = itr->second;
        const auto& mask = node->GetDriverIdMask();
        size_t driverCount = mask.count();

        if (driverCount == 0) {
            continue;
        }

        // For each driver that covers this node
        for (size_t i = 0; i < mask.size(); ++i) {
            if (!mask.test(i)) continue;

            unsigned driverId = static_cast<unsigned>(i + 1);

            // --- record node for this driver ---
            driverNodes[driverId].push_back(node);
        }
    }

    // (Optional) print stats summary to 'os' here using totalCount/privateCount/sharedCount

    // --- dump function lists per driver ---
    if (!outDir.empty()) {
        for (std::map<unsigned, std::vector<CGNode*> >::const_iterator it = driverNodes.begin();
             it != driverNodes.end(); ++it) {
            unsigned driverId = it->first;
            const std::vector<CGNode*>& nodes = it->second;

            std::ostringstream fn;
            fn << outDir << "/driver_" << driverId << ".funcs";

            std::ofstream ofs(fn.str().c_str());
            if (!ofs) {
                os << "WARN: failed to open " << fn.str() << " for writing.\n";
                continue;
            }

            for (std::vector<CGNode*>::const_iterator nit = nodes.begin();
                 nit != nodes.end(); ++nit) {
                 CGNode* n = *nit;

                // TODO: replace GetFuncName() with your actual accessor
                ofs << n->GetFName() << '\n';
            }
        }
    }
}

void CgMarker::dumpFunctoIdMap(const string& outPath)
{
    std::ofstream ofs(outPath);
    if (!ofs) {
        std::cerr << "WARN: failed to open " << outPath << " for writing.\n";
        return;
    }

    for (auto itr = wholeCg.begin(); itr != wholeCg.end(); ++itr) {
        CGNode* node = itr->second;
        unsigned nodeId = node->GetId();
        const string& fname = node->GetFName();

        ofs << fname << ":" << nodeId << "\n";
    }
}

