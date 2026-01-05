#ifndef _SCHEDULER_H_
#define _SCHEDULER_H_
#include <thread>
#include <atomic>
#include <chrono>
#include <cassert>
#include <filesystem>
#include "driver.h"
#include "util.h"
#include "cgmarker.h"
#include "fcov.h"
#include "faddr_id.h"

namespace fs = std::filesystem;


class Scheduler
{
public:
    Scheduler() = default;
    Scheduler(const string& benchPath, const string& sessionPath) 
    {
        this->benchPath   = benchPath;
        this->sessionPath = sessionPath;

        cgmk = new CgMarker (benchPath);
        assert(cgmk != NULL);

        string faddrMapPath = benchPath + "/faddr_id.map";
        if (!fs::exists(faddrMapPath)) {
            assert(getFAddrIdMap() == true && "Failed to get faddr_id.map"); 
        }
        fAddrToID = new FaddrID (benchPath + "/faddr_id.map");
        assert(fAddrToID != NULL);
        initEdgeKey();

        driverManger = new DriverMng(benchPath);
        assert(driverManger != NULL);

        fcovPath = sessionPath + "/fcov.map";
        fcov_setPath(fcovPath.c_str());

        activeDriver = 0;
    }

    ~Scheduler () 
    {
        cgmk->dump();
        delete cgmk;
        delete fAddrToID;
    }

    void setActiveDriver(unsigned driverId, bool init=false);
    void synchronizeGraphs();
    void switchDriver(unsigned drvId);
    set<unsigned> getCoveredFuncs();
    vector<unsigned> getAllDrvIds();

    inline void dump() 
    {
        cgmk->dump("final_marked_callgraph");
    }

private:
    unsigned activeDriver;

    string benchPath;
    string sessionPath;
    string fcovPath;
    CgMarker* cgmk;

    vector<unsigned> backupFcov;

    FaddrID *fAddrToID;
    map<uint64_t, CGEdge*> keyToEdge;

    DriverMng*  driverManger;

private:
    bool getFAddrIdMap();

    inline uint64_t hash64(uint64_t x) 
    {
        x ^= x >> 33;
        x *= 0xff51afd7ed558ccdULL;
        x ^= x >> 33;
        x *= 0xc4ceb9fe1a85ec53ULL;
        x ^= x >> 33;
        return x;
    }
    
    inline uint64_t getEdgeKey(unsigned srcId, unsigned dstId) 
    {
        uint64_t edgeId = srcId;
        return (edgeId<<32 | dstId);
    }

    inline void initEdgeKey() 
    {
        CGGraph* wCg = cgmk->getWholeCg();
        for (auto itr = wCg->begin(); itr != wCg->end(); itr++) {
            CGNode* srcNode = itr->second;
            for (auto itr = srcNode->OutEdgeBegin(); itr != srcNode->OutEdgeEnd(); itr++) {
                CGEdge* edge    = *itr;
                CGNode* dstNode = edge->GetDstNode();
                
                unsigned srcId = srcNode->GetId();
                unsigned dstId = dstNode->GetId();

                unsigned srcFAddr = fAddrToID->idToAddr(srcId);
                unsigned dstFAddr = fAddrToID->idToAddr(dstId);

                // edge key
                uint64_t edgeKey = getEdgeKey(srcFAddr, dstFAddr);
                //printf("[initEdgeKey][%x, %x] --> %lx [hash = %lx]\n", srcFAddr, dstFAddr, edgeKey, hash64(edgeKey)&FCOV_EDGE_TAB_MASK);
                keyToEdge[edgeKey] = edge;
                edge->Key = edgeKey;

                // node key
                dstNode->Key = dstFAddr;
                srcNode->Key = srcFAddr;
            }
        }
    }

    inline unsigned getNodeHitNum(unsigned nodeId) 
    {
        if (nodeId == 0) {
            return 0;
        }

        CGGraph* wCg = cgmk->getWholeCg();
        CGNode* node = wCg->GetGNode(nodeId);
        if (node == nullptr) {
            return 0;
        }

        uint32_t nodeKey = node->Key;
        return fcov_getNodeHitNum(nodeKey);
    }

    inline unsigned getEdgeHitNum(unsigned nodeId) 
    {
        if (nodeId == 0) {
            return 0;
        }

        CGGraph* wCg = cgmk->getWholeCg();
        CGNode* node = wCg->GetGNode(nodeId);
        if (node == nullptr) {
            return 0;
        }

        uint32_t nodeKey = node->Key;
        return fcov_getNodeHitNum(nodeKey);
    }

};


#endif