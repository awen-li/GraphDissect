#ifndef _DYNSCH_H_
#define _DYNSCH_H_
#include "fcov.h"
#include "driver.h"
#include "scheduler.h"

struct DynSch {
    unsigned sessionId;
    string   sessionPath;
    string   fcovMapPath;
    string   activeDrvPath;

    string   benchPath;
    DriverMng *driverManger;
    Scheduler *sch;
};

#endif

