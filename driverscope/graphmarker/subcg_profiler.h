#ifndef __SUBCG_PROFILER_H__
#define __SUBCG_PROFILER_H__

#include <string>
#include <iostream>
#include <set>
#include <fstream>
#include <filesystem>
#include "comgraph/CallGraph.h"

using namespace std;

class SubCgProfiler {
public:
    typedef map<unsigned, CGGraph*>::iterator subcg_iterator;

public:
    SubCgProfiler(const string bPath, unsigned maxRuns=3): benchPath(bPath), maxRuns(maxRuns) {

    }
    ~SubCgProfiler() {
        for (auto itr = drvId2Cg.begin(); itr != drvId2Cg.end();itr++){
            delete itr->second;
        }
    }

    CGGraph* getDrvSubgraph(Driver* drv, map<string, string>& symMap);

    subcg_iterator begin() { return drvId2Cg.begin(); }
    subcg_iterator end() { return drvId2Cg.end(); }

private:
    string benchPath;
    unsigned maxRuns;
    map<unsigned, CGGraph*> drvId2Cg;

private:
    string getRealSymbol(map<string, string>& symMap, string curSymb);
    bool parseEdges(string lineInfo, vector<string>& cachedNodes, CGGraph *cg, map<string, string>& symMap);
    bool parseNodes(string lineInfo, vector<string>& cachedNodes, map<string, string>& symMap);
    bool parseGprofToCGGraph(const string &profileTxt, CGGraph *cg, map<string, string>& symMap);

    inline vector<string> getSeeds(string& seedDir) {
        vector<string> seeds;
        unsigned count = 0;

        for (const auto &entry : filesystem::directory_iterator(seedDir)) {
            if (!entry.is_regular_file()) 
                continue;

            seeds.push_back(entry.path().string());
            if (++count >= maxRuns) 
                break;
        }

        return seeds;
    }

    inline string formatArgs(const vector<string>& args) {
        string result;
        for (size_t i = 0; i < args.size(); ++i) {
            result += args[i];
            if (i < args.size() - 1) result += " ";
        }
        return result;
    }
};

#endif // __SRC_RETRIEVER_H__
