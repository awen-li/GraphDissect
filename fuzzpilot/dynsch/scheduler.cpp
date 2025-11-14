#include "scheduler.h"
#include "fcov.h"

vector<NodeFeature> Scheduler::getNodeFeatures(unsigned driverId) {
    vector<NodeFeature> features;

    if (subg.driverId != driverId) {
        subg.subgraph.clear();
         cgmk->getDriverGraph(driverId, subg.subgraph);
         subg.driverId = driverId;
    }
    const set<CGNode*>& subgraph = subg.subgraph;

    for (const auto& node : subgraph) {
        NodeFeature nf;

        nf.funcId      = node->GetId();

        nf.coverCount  = node->HitNum;
        nf.callDepth   = node->Depth;

        nf.inDegree    = node->GetIncomingEdgeNum();
        nf.outDegree   = node->GetOutgoingEdgeNum();

        nf.isExclusive = (node->GetDriverIdMask().count() == 1 && node->HasDriverId(driverId)) ? 1 : 0;

        
        unsigned frontierCount = 0;
        if (firstRun == false) {
            for (auto itr = node->OutEdgeBegin(); itr != node->OutEdgeEnd(); itr++) {
                CGNode* dstNode = (*itr)->GetDstNode();

                if (fcov_getFuncHitNum(dstNode->GetId()) == 0) {
                    ++frontierCount;
                }
            }
        }
        nf.isFrontier = frontierCount;

        features.push_back(nf);
    }

    return features;
}


vector<pair<unsigned, unsigned>> Scheduler::getSubgraphEdges(unsigned driverId) {
    vector<pair<unsigned, unsigned>> edges;

    // Refresh subgraph if needed
    if (subg.driverId != driverId) {
        cgmk->getDriverGraph(driverId, subg.subgraph);
        subg.driverId = driverId;
    }
    set<CGNode*>& subgraph = subg.subgraph;

    // Traverse subgraph edges
    for (auto* srcNode : subgraph) {
        unsigned srcId = srcNode->GetId();

        for (auto itr = srcNode->OutEdgeBegin(); itr != srcNode->OutEdgeEnd(); itr++) {
            CGNode* dstNode = (*itr)->GetDstNode();
            unsigned dstId  = dstNode->GetId();

            edges.emplace_back(srcId, dstId);
        }
    }

    return edges;
}


void Scheduler::switchDriver(unsigned drvId) {
    // 1: Compute coverage diff between current state and last backup
    //  : Label the call graph with the newly covered set
    // 2: Backup the current fcov state and switch active driver

    if (activeDriver == 0 ) {
        activeDriver = drvId;
        return;
    }

    // 1
    unsigned updatedNodes = 0;
    unsigned newNodes = 0;
    unsigned totalHitNodes = 0;
    for (unsigned i = 0; i < backupFcov.size(); ++i) {
        unsigned hitNum = fcov_getFuncHitNum(i);

        if (hitNum != 0) {
            totalHitNodes++;
        }

        if (hitNum == 0 || backupFcov[i] == hitNum) {
            continue;
        }

        if (backupFcov[i] == 0) {
            newNodes++;
        }

        // save it
        backupFcov[i] = hitNum;

        cgmk->markNode(i, activeDriver);
        updatedNodes++;
    }

    // switch to new driver
    activeDriver = drvId;
    firstRun     = false;

    std::cout << "[Scheduler] Switched to driver " << drvId
              << "[" <<totalHitNodes<<" / "<<backupFcov.size()<<"]"
              << " (updated " << updatedNodes << " nodes with newly discovered "<<newNodes<<")\n";
    return;
}


void Scheduler::synchronizeGraphs()
{
    if (activeDriver == 0 ) {
        return;
    }

    CGGraph* wCg = cgmk->getWholeCg();
    unsigned cgNodeNum = wCg->GetNodeNum() + 32;
    for (unsigned i = 1; i < cgNodeNum; ++i) {

        unsigned nodeId = i;
        CGNode* node = wCg->GetGNode(nodeId);
        if (node == NULL) {
            continue;
        }

        node->HitNum = fcov_getFuncHitNum(nodeId);
        //if (node->HitNum != 0)
        //    printf("[synchronizeGraphs]node:[%u]%s, covered:%u\r\n", nodeId, node->GetFName().c_str(), node->HitNum);
    }
}

