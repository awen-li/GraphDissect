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
static const char *g_fcovMapPath = NULL;


static func_coverage_t* fcov_loadEdgecov(const char* fcovMapPath) 
{
    if (fcovMapPath == NULL) {
        //fprintf(stderr, "[fcov_loadEdgecov] fcovMapPath is NULL\n");
        return NULL;
    }

    int fd = open(fcovMapPath, O_RDWR);
    if (fd < 0) {
        perror("[fcov] open");
        fprintf(stderr, "[fcov_loadEdgecov] Open %s failed\n", fcovMapPath);
        return NULL;
    }

    func_coverage_t *fcov = (func_coverage_t*)mmap(
        NULL,
        sizeof(func_coverage_t),
        PROT_READ | PROT_WRITE,
        MAP_SHARED,
        fd,
        0
    );
    close(fd);

    if (fcov == MAP_FAILED) {
        perror("[fcov_loadEdgecov] mmap");
        fprintf(stderr, "[fcov_loadEdgecov] mmap %s failed\n", fcovMapPath);
        exit(EXIT_FAILURE);
    }

    fprintf(stderr, "[fcov_loadEdgecov] mmap %s success!\n", fcovMapPath);
    return fcov;
}


inline uint64_t fcov_hash64(uint64_t x) 
{
    x ^= x >> 33;
    x *= HASH_SEED_FCOV_1;
    x ^= x >> 33;
    x *= HASH_SEED_FCOV_2;
    x ^= x >> 33;
    return x;
}


static inline unsigned fcov_isEdgeVisited(func_coverage_t *fcov, uint64_t edgeKey) 
{
    if (!fcov || edgeKey == 0) {
        return 0;
    }

    uint64_t h   = fcov_hash64(edgeKey);
    uint32_t idx = (uint32_t)(h & FCOV_EDGE_TAB_MASK);

    const uint32_t max_probe = HASH_PROBE_MAX;

    for (uint32_t i = 0; i < max_probe; ++i) {
        uint32_t pos = (idx + i) & FCOV_EDGE_TAB_MASK;
        fcov_edge_slot_t* slot = &fcov->edge_hits[pos];

        uint64_t key = __atomic_load_n(&slot->key, __ATOMIC_RELAXED);
        if (key == 0) {
            // empty slot ? key was never inserted in this probe chain
            //printf("[fcov_isEdgeVisited]%lx [hash: %lx] - [pos: %u] ---> %u @0\n", edgeKey, h, pos, 0);
            return 0;
        }

        if (key == edgeKey) {
            uint64_t cnt = __atomic_load_n(&slot->count, __ATOMIC_RELAXED);
            //printf("[fcov_isEdgeVisited]%lx [hash: %lx] - [pos: %u] ---> %u\n", edgeKey, h, pos, (unsigned)cnt);
            return (unsigned)cnt;
        }
    }

    //printf("[fcov_isEdgeVisited]%lx [hash: %lx] ---> %u @end\n", edgeKey, h, 0);
    return 0;
}

static inline unsigned fcov_isNodeVisited(func_coverage_t *fcov, uint32_t nodeKey) 
{
    if (!fcov || nodeKey == 0) {
        return 0;
    }

    uint64_t h   = fcov_hash64((uint64_t)nodeKey);
    uint32_t idx = (uint32_t)(h & FCOV_FUNC_TAB_MASK);

    const uint32_t max_probe = HASH_PROBE_MAX;

    for (uint32_t i = 0; i < max_probe; ++i) {
        uint32_t pos = (idx + i) & FCOV_FUNC_TAB_MASK;
        fcov_func_slot_t* slot = &fcov->func_hits[pos];

        uint32_t key = __atomic_load_n(&slot->key, __ATOMIC_RELAXED);
        if (key == 0) {
            // empty slot ? key was never inserted in this probe chain
            //printf("[fcov_isNodeVisited]%x [hash: %lx] ---> %u @ 0 with probe:%u \n", nodeKey, h, 0, i);
            return 0;
        }

        if (key == nodeKey) {
            uint32_t cnt = __atomic_load_n(&slot->count, __ATOMIC_RELAXED);
            //printf("[fcov_isNodeVisited]%x [hash: %lx] ---> %u\n", nodeKey, h, cnt);
            return cnt;
        }
    }

    //printf("[fcov_isNodeVisited]%x [hash: %lx] ---> %u @end\n", nodeKey, h, 0);
    return 0; 
}

/* Set the path to the shared fcov mmap file */
void fcov_setPath(const char* fcovMapPath) 
{
    g_fcovMapPath = fcovMapPath;
}

/* Lazy initialization of g_fcov */
void fcov_init() 
{
    if (!g_fcov) {
        g_fcov = fcov_loadEdgecov(g_fcovMapPath);
    }
}

/* Unmap and reset global pointer */
void fcov_deinit() 
{
    if (g_fcov != NULL) {
        munmap(g_fcov, sizeof(func_coverage_t));
        g_fcov = NULL;
    }
}


unsigned fcov_getEdgeHitNum(uint64_t edgeKey) 
{
    if (!g_fcov) {
        fcov_init();
    }
    if (!g_fcov) {
        return 0;
    }

    return fcov_isEdgeVisited(g_fcov, edgeKey);
}

unsigned fcov_getNodeHitNum(uint32_t nodeKey)
{
    if (!g_fcov) {
        fcov_init();
    }
    if (!g_fcov) {
        return 0;
    }

    return fcov_isNodeVisited(g_fcov, nodeKey);
}

/* Block writes from the instrumented process */
void setCovBlock() 
{
    if (!g_fcov) {
        fcov_init();
    }
    if (!g_fcov) {
        return;
    }

    __atomic_store_n(&g_fcov->block_writes, true, __ATOMIC_RELAXED);
}

/* Allow writes from the instrumented process */
void setCovNonBlock() 
{
    if (!g_fcov) {
        fcov_init();
    }
    if (!g_fcov) {
        return;
    }

    __atomic_store_n(&g_fcov->block_writes, false, __ATOMIC_RELAXED);
}

#ifdef __cplusplus
}
#endif
