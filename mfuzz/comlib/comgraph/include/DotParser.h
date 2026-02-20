#ifndef _DOTPARSER_H_
#define _DOTPARSER_H_
#include <algorithm>
#include <vector>
#include <set>
#include <fstream>
#include <sstream>
#include <regex>
#include <cassert>
#include "CallGraph.h"
#include "libFunc.h"

#if 0
#define DEBUG_PRINT(format, ...) fprintf(stderr, "@@@ [DOT] -> " format, ##__VA_ARGS__)
#else
#define DEBUG_PRINT(format, ...)
#endif

using namespace std;

typedef enum
{
    DOT_SVF = 1,
    DOT_AIF = 2,
}DOT_TYPE;

template<class NodeTy,class EdgeTy, class GraphType> class DotParser
{
public:
    DotParser (string DotF)
    {
        DotFile = DotF;
        DotType = CalDotType ();
    }

    ~DotParser ()
    {

    }
    
    // currently only handle call graph & sem graph
    void Dot2Graph (GraphType& graph)
    {
        switch (DotType)
        {
            case DOT_SVF:
            {
                ParseDotSvf (graph);
                break;
            }
            case DOT_AIF:
            {
                ParseDotAif (graph);
                break;
            }
            default:
            {
                fprintf (stderr, "Dot2Graph: unsupported type: %u\r\n", DotType);
                return;
            }
        }

        printf ("@@Dot2Graph: Load Dot Type -> %s, NodeNum -> %u\r\n", (DotType==DOT_SVF)?"DOT_SVF":"DOT_AIF", graph.GetNodeNum());
    }

    DOT_TYPE GetDotType ()
    {
        return DotType;
    }

protected:
    string DotFile;
    DOT_TYPE DotType;

    set<string> libFunctions;
    set<string> libIndexs;

protected:
    vector<string> splitString(string& str, char delimiter) 
    {
        vector<string> tokens;
        string token;
        istringstream tokenStream(str);

        while (getline(tokenStream, token, delimiter)) 
        {
            tokens.push_back(token);
        }

        return tokens;
    }

    inline DOT_TYPE CalDotType ()
    {
        ifstream Df(DotFile);
        string Line;

        unsigned MaxLine = 10;
        while (getline(Df, Line)) 
        {
            size_t Pos = Line.find("Node0x");
            if (Pos != string::npos)
            {
                return DOT_SVF;
            }

            MaxLine--;
            if (MaxLine == 0)
            {
                break;
            }
        }

        return DOT_AIF;
    }

    void ParseDotSvf(GraphType& graph) 
    {
        ifstream Df(DotFile);
        string Line;

        map<string, NodeTy*> NodeMap;

        // Parse nodes
        /*
        Node0x55558860cb50 [shape=record,shape=box,label="{CallGraphNode ID: 20 \{fun: strtoul\}}"];
        Node0x5555886b1ef0 [shape=record,shape=box,label="{CallGraphNode ID: 2346 \{fun: xmlListWalk\}|{<s0>17862|<s1>17863|<s2>17864|<s3>17865}}"];
        */
        while (getline(Df, Line)) 
        {
            size_t Pos = Line.find("Node0x");
            if (Pos == string::npos)
            {
                continue;
            }
            string NodeIndex = Line.substr(Pos, 18 /* string("Node0x55558860cb50").size()-1 */);
            
            Pos = Line.find(" \\{fun: ", 18);
            if (Pos == string::npos)
            {
                continue;
            }
            size_t fPos = Line.find("\\}|{<s", Pos);
            if (fPos == string::npos)
            {
                fPos = Line.find("\\}}\"];", Pos);
                if (fPos == string::npos)
                {
                    continue;
                }
            }

            string FuncInfo = Line.substr(Pos+8, fPos-Pos-8);
            DEBUG_PRINT("--> Parse Node: %s - %s \r\n", NodeIndex.c_str(), FuncInfo.c_str());
            vector<string> tokens = splitString (FuncInfo, ':');
            if (tokens.size () < 3)
            {
                fprintf (stderr, "Incorrect format while parsing SVF callgraph: %s\r\n", FuncInfo.c_str());
                continue;
            }

            unsigned blockNum = (unsigned)stoi(tokens[2]);
            if (blockNum == 0)
            {
                continue;
            }

            if (LibFuncs::isLibFunc (tokens[0]))
            {
                libIndexs.insert (NodeIndex);
                continue;
            }

            NodeTy *Node = graph.AddNode(tokens[0]);
            Node->BlockNum = blockNum;
            //std::cout << "Added Node: " << tokens[0] << " with BlockNum: " << blockNum << std::endl;
            //Node->SetFuncAttr ((unsigned)stoi(tokens[1]), blockNum);
            NodeMap[NodeIndex] = Node;
        }

        // Reset file stream to beginning for parsing edges
        Df.clear();
        Df.seekg(0, ios::beg);

        // Parse edges
        /*
        Node0x555588625de0:s0 -> Node0x5555886b23f0[color=black];
        */
        while (getline(Df, Line)) 
        {
            size_t Pos = Line.find("Node0x");
            if (Pos == string::npos)
            {
                continue;
            }
            string SrcIndex = Line.substr(Pos, 18 /* string("Node0x555588625de0").size()-1 */);

            Pos = Line.find(" -> Node0x");
            if (Pos == string::npos)
            {
                continue;
            }
            size_t nPos = Line.find("[color=", Pos+10);
            if (nPos == string::npos)
            {
                continue;
            }
            string DstIndex = Line.substr(Pos+4, nPos-Pos-4);

            DEBUG_PRINT("--> Parse Edge: SRC-%s -> DST-%s \r\n", SrcIndex.c_str(), DstIndex.c_str());

            NodeTy* SrcNode = NodeMap[SrcIndex];
            NodeTy* DstNode = NodeMap[DstIndex];
            if (SrcNode && DstNode) 
            {
                graph.AddEdge(SrcNode, DstNode);
            }
            else
            {
                #if 0
                if (SrcNode == NULL && libIndexs.find (SrcIndex) == libIndexs.end())
                {
                    fprintf (stderr, "Node: %p (%s) and Node: %p (%s) not exist!\r\n", 
                             SrcNode, SrcIndex.c_str(), DstNode, DstIndex.c_str());
                }

                if (DstNode == NULL && libIndexs.find (DstIndex) == libIndexs.end())
                {
                    fprintf (stderr, "Node: %p (%s) and Node: %p (%s) not exist!\r\n", 
                             SrcNode, SrcIndex.c_str(), DstNode, DstIndex.c_str());
                }
                #endif
            }
        }
    }

    void ParseDotAifRegex(GraphType& graph) 
    {
        ifstream Df(DotFile);
        string Line;

        regex NodeRegex(R"((\w+)\s+\[.*label=\"(\w+)\s+\(mask=([01]+)\)\".*\])");
        regex EdgeRegex (R"((\w+)\s+->\s+(\w+)\[.*\])");  
        smatch Matches;

        map<string, NodeTy*> NodeMap;

        // Parse nodes
        while (getline(Df, Line)) 
        {
            if (!regex_search(Line, Matches, NodeRegex)) 
            {
                continue;
            }
            
            string FuncName = Matches[1];
            NodeTy *Node = graph.AddNode(FuncName);
            assert(Node != nullptr);

            std::string maskStr = Matches[3];
            boost::dynamic_bitset<> bitmask(maskStr.size(), 0);

            // Convert string to bitset (bitset constructor treats string as LSB first, so reverse it)
            for (size_t i = 0; i < maskStr.size(); ++i) 
            {
                if (maskStr[maskStr.size() - 1 - i] == '1') 
                {
                    bitmask.set(i);
                }
            }

            Node->SetDriverIdMask(bitmask);
        }

        // Reset file stream to beginning for parsing edges
        Df.clear();
        Df.seekg(0, ios::beg);

        // Parse edges
        while (std::getline(Df, Line)) 
        {
            if (!regex_search(Line, Matches, EdgeRegex)) 
            {
                continue;
            }
                
            string SrcName = Matches[1];
            string DstName = Matches[2];

            NodeTy* SrcNode = graph.GetNode (SrcName);
            NodeTy* DstNode = graph.GetNode (DstName);
            if (SrcNode && DstNode) 
            {
                graph.AddEdge(SrcNode, DstNode);
            }
            else
            {
                fprintf (stderr, "Node: %p (%s) and Node: %p (%s) not exist!\r\n", 
                        SrcNode, SrcName.c_str(), DstNode, DstName.c_str());
            }
        }
    }

    void trim(std::string& s) 
    {
        while (!s.empty() && std::isspace((unsigned char)s.front()))
            s.erase(s.begin());
        while (!s.empty() && std::isspace((unsigned char)s.back()))
            s.pop_back();
    }

    inline boost::dynamic_bitset<> GetBitMask(std::string& dataContent) 
    {
        auto maskPos = dataContent.find("(mask=");
        assert (maskPos != string::npos);

        auto start = maskPos + 6;
        auto end = dataContent.find(')', start);
        assert (end != string::npos);

        // Convert mask string to dynamic_bitset (MSB-left)      
        string maskStr = dataContent.substr(start, end - start);
        boost::dynamic_bitset<> bitmask(maskStr.size(), 0);
        for (size_t i = 0; i < maskStr.size(); ++i) 
        {
            if (maskStr[maskStr.size() - 1 - i] == '1') 
            {
                bitmask.set(i);
            }
        }
        return bitmask;
    }

    inline unsigned GetBlockNum(string& dataContent) 
    {
        auto blockPos = dataContent.find("(blocks=");
        assert (blockPos != string::npos);

        auto start = blockPos + 8;
        auto end = dataContent.find(')', start);
        assert (end != string::npos);

        return (unsigned)stoi(dataContent.substr(start, end - start));
    }


    inline std::vector<uint64_t> GetKeys(const std::string& s) {
        std::vector<uint64_t> keys;

        auto p = s.find("(Key=");
        if (p == std::string::npos) return keys;

        p += 5; // after "(Key="
        auto q = s.find(')', p);
        if (q == std::string::npos) return keys;

        std::string inside = s.substr(p, q - p);
        if (inside.empty()) return keys;

        std::stringstream ss(inside);
        std::string token;
        while (std::getline(ss, token, ',')) {
            if (token.empty()) continue;
            uint64_t value = std::stoull(token, nullptr, 16);
            keys.push_back(value);
        }

        return keys;
    }

    inline unsigned getHitNum(const std::string& s) 
    {
        auto p = s.find("(HitNum=");
        if (p == std::string::npos) return 0;

        p += 8; // after "(HitNum="
        auto q = s.find(')', p);
        if (q == std::string::npos) return 0;

        std::string numStr = s.substr(p, q - p);
        if (numStr.empty()) return 0;

        return (unsigned)stoi(numStr);
    }

    void ParseDotAif(GraphType& graph) 
    {
        ifstream Df(DotFile);
        if (!Df.is_open()) 
        {
            fprintf(stderr, "Error: Could not open file %s\n", DotFile.c_str());
            return;
        }

        string line;

        /* c14n_c_xmlC14NExecute [color=black,label="internalSubsetDebug (mask=11101011000)"]; */
        while (getline(Df, line)) 
        {
            trim(line);
            if (line.find("->") != string::npos) 
            {
                continue;
            }

            auto bracketPos = line.find(" [");
            if (bracketPos == string::npos) 
            {
                continue;
            }
            string nodeName = line.substr(0, bracketPos);
            trim(nodeName);

            NodeTy* node = graph.AddNode(nodeName);
            node->HitNum = 0;

            boost::dynamic_bitset<> bitmask = GetBitMask(line);
            node->SetDriverIdMask(bitmask);

            node->BlockNum = GetBlockNum(line);

            vector<uint64_t> Keys = GetKeys(line);
            if (!Keys.empty()) {
                node->Key = Keys[0];
            }

            node->HitNum = getHitNum(line);
        }
  
        Df.clear();
        Df.seekg(0, ios::beg);

        /* c14n_c_xmlC14NExecute -> c14n_c_xmlC14NProcessNodeList[color=black,label=""]; */
        while (getline(Df, line)) 
        {
            trim(line);
            auto arrowPos = line.find(" -> ");
            if (arrowPos == string::npos) 
            {
                continue;
            }

            string srcName = line.substr(0, arrowPos);
            trim(srcName);

            auto bracketPos = line.find("[", arrowPos + 4);
            string dstName = line.substr(arrowPos + 4, bracketPos - (arrowPos + 4));
            trim(dstName);

            NodeTy* srcNode = graph.GetNode(srcName);
            NodeTy* dstNode = graph.GetNode(dstName);

            if (srcNode && dstNode) 
            {
                // parse edge label for driver id mask
                // stubHashScannerFull -> xmlCtxtDumpEntityCallback[color=black,label="(mask=10000000000)"];
                boost::dynamic_bitset<> bitmask = GetBitMask(line);
                graph.AddEdge(srcNode, dstNode, bitmask);

                vector<uint64_t> Keys = GetKeys(line);
                if (!Keys.empty()) {
                    for (auto eItr = srcNode->OutEdgeBegin(); eItr != srcNode->OutEdgeEnd(); eItr++) {
                        EdgeTy* edge = *eItr;
                        if (edge->GetDstNode() == dstNode) {
                            edge->Keys = Keys;
                            edge->HitNum = getHitNum(line);
                            break;
                        }
                    }
                }   
            } 
            else 
            {
                fprintf(stderr, 
                    "Warning: Could not find node(s): '%s' or '%s'\n",
                    srcName.c_str(), dstName.c_str());
            }
        }
    }
};

#endif