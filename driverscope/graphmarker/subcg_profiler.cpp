#include "driver.h"
#include "subcg_profiler.h"

using namespace std;

CGGraph* SubCgProfiler::getDrvSubgraph(Driver* drv, map<string, string>& symMap) {
    set<string> functionSet;

    string binPath = benchPath + "/" + "pg_" + drv->getDriver();
    if (!filesystem::exists(binPath)) {
        cerr<<"[!] Instrumented binary not found: "<<binPath<<"\n";
        return NULL;
    }

    string seedPath = benchPath + "/drivers/"+ drv->getName() + "/" + drv->getSeedDir();
    vector<string> seeds = getSeeds(seedPath);
    if (seeds.size() == 0) {
        cerr<<"Failed to load seeds @"<<seedPath<<"\n";
        return NULL;
    }

    CGGraph *drvCg = new CGGraph();
    assert(drvCg != NULL);
    drvId2Cg[drv->getId()] = drvCg;

    string tmpProfile = benchPath + "/tmp_profile.txt";
    for (const string &seed : seeds) {
        // Run the driver with seed
        int timeout_seconds = 2;
        std::string cmd = "timeout " + std::to_string(timeout_seconds) + " " + 
                        binPath + " " + formatArgs(drv->getArgv()) + " " + 
                        seed + " " + drv->getOutput() + " >/dev/null 2>&1";
        
        int ret = system(cmd.c_str());
        if (WIFEXITED(ret) && WEXITSTATUS(ret) == 124) {
            cerr<<"@getDrvSubgraph: Time out @"<<drv->getName()<<" failed --> cmd = " <<cmd<<"\n";
            continue;
        }

        // Run gprof
        string gprofCmd = "gprof " + binPath + " gmon.out " + ">" + tmpProfile + " 2>/dev/null";
        system(gprofCmd.c_str());

        // Parse gprof output
        if(!parseGprofToCGGraph(tmpProfile, drvCg, symMap)){
            cerr<<"parseGprofToCGGraph for driver @"<<drv->getName()<<" failed --> cmd = " <<cmd<<"\n";
            return NULL; 
        }

        cout<<"@["<<drv->getId()<<"]: "<<cmd<<" --> cg size = "<<drvCg->GetNodeNum()<<"\n";
    }
    filesystem::remove(tmpProfile);

    //CGViz gv (drv->getName()+"-callgraph", drvCg, drv->getName()+"-callgraph.dot");
    //gv.WiteGraph();

    return drvCg;
}

string SubCgProfiler::getRealSymbol(map<string, string>& symMap, string curSymb) {
    auto itr = symMap.find(curSymb);
    if (itr == symMap.end()){
        return curSymb;
    }
    else {
        return itr->second;
    }
}

bool SubCgProfiler::parseEdges(string lineInfo, 
                               vector<string>& cachedNodes, 
                               CGGraph *cg,
                               map<string, string>& symMap) {
    smatch match;
    
    static regex C_funcHeaderRegex(R"(\[\d+\].*\s+(\w+)\s+\[\d+\])");
    static regex CPP_funcHeaderRegex(R"(\[\d+\].*?\s+([a-zA-Z_:~][^\[]+?)\s+\[\d+\])");

    string curCallee = "";
    if (symMap.size() == 0) {
        // C program
        if (regex_search(lineInfo, match, C_funcHeaderRegex)) {
            curCallee = getRealSymbol(symMap, match[1]);
        }
    }
    else {
        // C++ program
        if (regex_search(lineInfo, match, CPP_funcHeaderRegex)) {
            curCallee = getRealSymbol(symMap, match[1]);
        }
    }

    if (curCallee == "") {
        return false;
    }

    CGNode* calleeNode = cg->AddNode(curCallee);
    for (const auto& caller : cachedNodes) {
        string curCaller = getRealSymbol(symMap, caller);
        CGNode* callerNode = cg->AddNode(curCaller);
        cg->AddEdge(callerNode, calleeNode);
        //cout<<"@@ add edge from " + curCaller + " to " + curCallee + "\n";
    }

    return true;
}


bool SubCgProfiler::parseNodes(string lineInfo, 
                               vector<string>& cachedNodes,
                               map<string, string>& symMap) {
    std::smatch match;

    string callerName = "";
    if (symMap.size() == 0) {
        // C program
        // For plain C-style functions: e.g.,   foo [123]
        static regex cFuncRegex(R"(\s+\d+/\d+\s+(\w+)\s+\[\d+\])");
        if (regex_search(lineInfo, match, cFuncRegex)) {
            callerName = match[1];
        }
    }
    else {
        // C++ program
        // For demangled C++ functions: e.g.,   Class::method(...) [123]
        static regex cppFuncRegex(R"(\d+/\d+\s+([a-zA-Z_:~][^\[]+?)\s+\[\d+\])");
        if (regex_search(lineInfo, match, cppFuncRegex)) {
            callerName = match[1];
        }
    }

    if (callerName == "") {
        return false; 
    }

    cachedNodes.push_back(callerName);
    //cout<<"@@ add node for: " + callerName + "\n";
    return true;
}


bool SubCgProfiler::parseGprofToCGGraph(const string &profileTxt, 
                                        CGGraph *cg,
                                        map<string, string>& symMap) {
    ifstream in(profileTxt);
    if (!in) {
        cerr << "[!] Cannot open gprof output: " << profileTxt << "\n";
        return false;
    }

    string line;
    string currentCallee;

    // reach to the call graph
    while (getline(in, line)) {
        if (line.find("Call graph") != string::npos) {
            break;
        }
    }

    vector<string> cachedCallers;
    while (getline(in, line)) {
        
        if (parseNodes(line, cachedCallers, symMap)){
            continue;
        }

        if (parseEdges(line, cachedCallers, cg, symMap)){
            cachedCallers.clear();
        }
    }

    in.close();
    return true;
}
