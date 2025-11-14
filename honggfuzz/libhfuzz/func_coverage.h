#ifndef _HF_FUNC_COVERAGE_H_
#define _HF_FUNC_COVERAGE_H_

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdatomic.h>

#define _HF_MAX_FUNCTIONS    (256UL * 1024UL)
#define _HF_MAX_DRIVER_COUNT (4UL * 1024UL)

typedef struct {
    volatile bool block_writes;
    unsigned count;                       // Number of functions hit at least once
    int      fcov_fd;
    unsigned visited[_HF_MAX_FUNCTIONS];  // Hit count per function
} func_coverage_t;

bool fcov_initBitmap(const char* session_path, unsigned target_bm_fd);

static inline void fcov_setVisited(func_coverage_t* fcov, uint32_t id) {
    if (id == 0 || id > _HF_MAX_FUNCTIONS) return;

    if (__atomic_load_n(&fcov->block_writes, __ATOMIC_RELAXED)) return;

    if (atomic_fetch_add(&fcov->visited[id - 1], 1) == 0) {
        atomic_fetch_add(&fcov->count, 1);
    }
}

static inline bool fcov_isVisited(func_coverage_t* fcov, uint32_t id) {
    if (id == 0 || id > _HF_MAX_FUNCTIONS) return false;
    return atomic_load(&fcov->visited[id - 1]) > 0;
}

typedef struct {
    uint32_t edge_counts[_HF_MAX_DRIVER_COUNT];
    unsigned count;
}driver_edgecov_t;

#endif // _HF_FUNC_COVERAGE_H_
