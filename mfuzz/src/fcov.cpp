#ifdef __cplusplus
extern "C" {
#endif

#include <stdio.h>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdbool.h>
#include "fcov.h"

func_coverage_t *g_fcov = NULL;
static const char *g_fcovMapPath = "";


static inline unsigned fcov_isVisited(func_coverage_t *fcov, uint32_t id) {
    if (!fcov || id == 0 || id > MAX_FUNCTIONS)
        return 0;
    return __atomic_load_n(&fcov->visited[id-1], __ATOMIC_RELAXED);
}


static func_coverage_t* fcov_loadFcov(const char* fcovMapPath) {
    if (fcovMapPath == NULL) {
        return NULL;
    }

    int fd = open(fcovMapPath, O_RDWR);
    if (fd < 0) {
        fprintf(stderr, "Open %s failed", fcovMapPath);
        return NULL;
    }

    func_coverage_t *fcov = (func_coverage_t*)mmap(NULL, sizeof(func_coverage_t), 
                                                   PROT_READ | PROT_WRITE, 
                                                   MAP_SHARED, fd, 0);
    close(fd);

    if (fcov == MAP_FAILED) {
        fprintf(stderr, "mmap %s failed", fcovMapPath);
        exit(0);
    }

    printf("@@@fcov_loadFcov -> mmap %s success!", fcovMapPath);
    return fcov;
}

void fcov_setPath(const char* fcovMapPath) {
    g_fcovMapPath = fcovMapPath;
    return;
}


void fcov_init() {
    if (!g_fcov) {
        g_fcov = fcov_loadFcov(g_fcovMapPath);
    }
    return;
}


void fcov_deinit() {
    if (g_fcov != NULL) {
        munmap(g_fcov, sizeof(func_coverage_t));
        g_fcov = NULL;
    }
}


unsigned fcov_getFuncHitNum(unsigned funcId) {
    if (!g_fcov) {
        fcov_init();
    }

    unsigned hitNum = fcov_isVisited(g_fcov, funcId);
    return hitNum;
}

void setCovBlock() {
    if (!g_fcov) {
        return;
    }

    __atomic_store_n(&g_fcov->block_writes, true, __ATOMIC_RELAXED);
}


void setCovNonBlock() {
    if (!g_fcov) {
        return;
    }

    __atomic_store_n(&g_fcov->block_writes, false, __ATOMIC_RELAXED);
}


#ifdef __cplusplus
}
#endif

