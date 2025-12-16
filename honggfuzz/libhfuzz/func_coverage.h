#ifndef _HF_FUNC_COVERAGE_H_
#define _HF_FUNC_COVERAGE_H_

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdatomic.h>


#define _HF_MAX_DRIVER_COUNT (4UL * 1024UL)

#define HASH_PROBE_MAX 64

#define HASH_SEED_FCOV_1 0xff51afd7ed558ccdULL
#define HASH_SEED_FCOV_2 0xc4ceb9fe1a85ec53ULL

#define FCOV_EDGE_TAB_SIZE  (1u << 20)
#define FCOV_EDGE_TAB_MASK  (FCOV_EDGE_TAB_SIZE - 1)

#define FCOV_FUNC_TAB_SIZE  (1u << 16)
#define FCOV_FUNC_TAB_MASK  (FCOV_FUNC_TAB_SIZE - 1)

/* Edge: keep 16-byte slot for nice alignment */
typedef struct {
    uint64_t key;        /* packed (caller32 << 32 | callee32), 0 = empty */
    uint32_t count;      /* hit count (32-bit) */
    uint32_t _pad;       /* padding / reserved */
} fcov_edge_slot_t;

/* Func: smaller slot, addr32 + count32 */
typedef struct {
    uint32_t key;        /* low 32 bits of function address, 0 = empty */
    uint32_t count;      /* hit count (32-bit) */
} fcov_func_slot_t;

typedef struct {
    volatile bool block_writes;

    int           fcov_fd;
    unsigned      edge_count;   /* total edges */
    unsigned      func_count;   /* total funcs */
    

    fcov_edge_slot_t edge_hits[FCOV_EDGE_TAB_SIZE];
    fcov_func_slot_t func_hits[FCOV_FUNC_TAB_SIZE];
} func_coverage_t;


bool fcov_initBitmap(const char* session_path, unsigned target_bm_fd);

#endif // _HF_FUNC_COVERAGE_H_
