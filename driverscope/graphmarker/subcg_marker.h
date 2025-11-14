#ifndef __SUBCG_MARKER_H__
#define __SUBCG_MARKER_H__
#include <unordered_set>
#include <stack>
#include <iomanip>
#include "cgmarker.h"
#include "subcg_profiler.h"

class SubCgMarker {
private:
    string benchPath;
    CgMarker *cgmk;
    SubCgProfiler *profiler;
    map<unsigned, Driver*> id2Driver;

public:
    SubCgMarker() = default;
    SubCgMarker(string benchPath) {
        this->benchPath = benchPath;

        cgmk = new CgMarker (benchPath);
        assert(cgmk != NULL);

        profiler = new SubCgProfiler(benchPath);
        assert(profiler != NULL);
    }

    ~SubCgMarker() {
        delete profiler;
        delete cgmk;
        for (auto itr = id2Driver.begin(); itr != id2Driver.end(); itr++) {
            delete itr->second;
        }
    }

    void markSugraph(string drvName, map<string, string>& symMap);
    void computeScore();
    void dump();

    void reportGlobalStats();
    void reportPerDriverStats();

private:
    void dumpFidMap(const string FID = "function_id.map");

};

#endif

