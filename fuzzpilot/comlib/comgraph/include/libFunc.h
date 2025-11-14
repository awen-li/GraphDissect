#ifndef _LIBFUNC_H_
#define _LIBFUNC_H_
#include <string>
#include <unordered_set>

using namespace std;

class LibFuncs
{
public:
    static unordered_set<string> libFunctions;

    static bool isLibFunc(const std::string& funcName);

};


#endif
