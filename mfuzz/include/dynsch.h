#ifndef _DYNSCH_H_
#define _DYNSCH_H_
#include "fcov.h"
#include "driver.h"
#include "scheduler.h"

struct DrvRTStat
{
    unsigned edges         = 0;
    unsigned delta_edges   = 0;
    unsigned crashes       = 0;
    unsigned delta_crashes = 0;
};


void dynsch_initSession(const char *sessionPath, unsigned sessionId);
void dynsch_deinitSession(void);
bool dynsch_initScheduler(const char *benchPath);
std::vector<unsigned> dynsch_getCoveredFuncs();
unsigned dynsch_getDriverNum();
vector<unsigned> dynsch_getAllDrivers();
bool dynsch_setActiveDriver(unsigned driverId);
bool dynsch_setInitDriver(unsigned driverId);
unsigned dynsch_getWGraphSize();


DrvRTStat dynsch_getDriverRTStat(unsigned driverId);
bool dynsch_sliceMarkedGraph(unsigned maxDepth);
bool dynsch_getDriverStatistic(const char* bench_path, const char* drv_ids);

#endif

