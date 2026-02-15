#ifndef __SGMARKER_H__
#define __SGMARKER_H__
#include <unordered_set>
#include <stack>
#include <iomanip>
#include "cgmarker.h"

class SubCgMarker {
private:
    string benchPath;
    CgMarker *cgmk;
    vector<unsigned> drvIDs;

public:
    SubCgMarker() = default;
    SubCgMarker(string benchPath) {
        this->benchPath = benchPath;

        cgmk = new CgMarker (benchPath);
        assert(cgmk != NULL);
    }

    ~SubCgMarker() {
        delete cgmk;
    }

    void dump();
    void reportGlobalStats();
    void reportPerDriverStats();

};

#endif

