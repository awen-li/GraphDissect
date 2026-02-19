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
        dump();
        delete cgmk;
        delete fAddrToID;
        delete driverManger;
    }

    void setActiveDriver(unsigned driverId, bool init=false);
    void synchronizeGraphs();
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

    FaddrID *fAddrToID;
    DriverMng*  driverManger;

private:
    bool getFAddrIdMap();

    inline unsigned getGraphSize() {
        CGGraph* wCg = cgmk->getWholeCg();
        return wCg->GetNodeNum();
    }
    
    inline uint64_t getEdgeKey(unsigned srcADDR, unsigned dstADDR) 
    {
        uint64_t edgeKey = srcADDR;
        return (edgeKey<<32 | dstADDR);
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
                //printf("[initEdgeKey][%x, %x] --> %lx [hash = %lx]\n", srcFAddr, dstFAddr, edgeKey, fcov_hash64(edgeKey)&FCOV_EDGE_TAB_MASK);
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

    inline vector<unsigned> UpdateNodesHitNum(unsigned drvId, 
                                              unsigned& updatedNodes, 
                                              unsigned& totalHitNodes) 
    {
        vector<unsigned> newHitNodes;

        CGGraph* wCg = cgmk->getWholeCg();
        for (auto itr = wCg->begin(); itr != wCg->end(); itr++) {
            CGNode* node = itr->second;

            unsigned nodeId = node->GetId();
            unsigned hitNum = getNodeHitNum(nodeId);

            if (hitNum != 0) {
                totalHitNodes++;
            }
    
            if (hitNum == 0 || node->HitNum == hitNum) {
                continue;
            }
    
            if (node->HitNum == 0) {
                newHitNodes.push_back(nodeId);
            }

            node->HitNum = hitNum;
            node->SetDriverIdMask(drvId);
            updatedNodes++;
        }
    
        return newHitNodes;
    }

    inline unsigned getEdgeHitNum(unsigned srcId, unsigned dstId) 
    {
        CGGraph* wCg = cgmk->getWholeCg();
        CGNode* srcNode = wCg->GetGNode(srcId);
        CGNode* dstNode = wCg->GetGNode(dstId);
        if (srcNode == nullptr || dstNode == nullptr) {
            return 0;
        }

        uint64_t edgeKey = getEdgeKey(srcNode->Key, dstNode->Key);
        return fcov_getEdgeHitNum(edgeKey);
    }

    inline unsigned getEdgeHitNum(CGEdge* edge) 
    {
        return fcov_getEdgeHitNum(edge->Key);
    }

    inline unsigned UpdateEdgesHitNum(vector<unsigned>& newHitNodes, unsigned drvId) 
    {
        // for each newly hit node, update its outgoing edges' hit num
        unsigned newHitEdges = 0;

        CGGraph* wCg = cgmk->getWholeCg();
        for (auto it = newHitNodes.begin(); it != newHitNodes.end(); ++it) {
            unsigned nodeId = *it;       
            CGNode* node = wCg->GetGNode(nodeId);
            if (node == nullptr) {
                continue;
            }

            // outgoing edges
            for (auto eItr = node->OutEdgeBegin(); eItr != node->OutEdgeEnd(); eItr++) {
                CGEdge* edge = *eItr;

                unsigned hitNum = getEdgeHitNum(edge);
                std::cout << "[OutEdge][UpdateEdgesHitNum] Edge (" 
                          << edge->GetSrcNode()->GetFName() << " -> " 
                          << edge->GetDstNode()->GetFName() 
                          << ") Key = " << edge->Key
                          << ", Hit num: " << hitNum << "\n";

                if (hitNum == 0 || edge->HitNum == hitNum) {
                    continue;
                }

                edge->HitNum = hitNum;
                newHitEdges++;

                edge->SetDriverIdMask(drvId);
            }

            // incoming edges
            for (auto eItr = node->InEdgeBegin(); eItr != node->InEdgeEnd(); eItr++) {
                CGEdge* edge = *eItr;

                unsigned hitNum = getEdgeHitNum(edge);
                std::cout << "[InEdge][UpdateEdgesHitNum] Edge (" 
                          << edge->GetSrcNode()->GetFName() << " -> " 
                          << edge->GetDstNode()->GetFName() 
                          << ") Key = " << edge->Key
                          << ", Hit num: " << hitNum << "\n";

                if (hitNum == 0 || edge->HitNum == hitNum) {
                    continue;
                }

                edge->HitNum = hitNum;
                newHitEdges++;

                edge->SetDriverIdMask(drvId);
            }
        }
   
        return newHitEdges;
    }

};


#endif