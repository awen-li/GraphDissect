#ifndef _FCOV_H_
#define _FCOV_H_

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>
#include <stddef.h>

#define MAX_FUNCTIONS (256UL * 1024UL)

typedef struct {
    volatile bool block_writes;
    unsigned count;                       // Number of functions hit at least once
    int      fcov_fd;
    unsigned visited[MAX_FUNCTIONS];      // Hit count per function
} func_coverage_t;

void fcov_setPath(const char* fcovMapPath);
void fcov_deinit();

unsigned fcov_getFuncHitNum(unsigned funcId);

void setCovBlock();
void setCovNonBlock();

#ifdef __cplusplus
}
#endif

#endif
