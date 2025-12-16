#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <sys/mman.h>
#include <fcntl.h>
#include <unistd.h>
#include "honggfuzz.h"
#include "libhfcommon/log.h"
#include "libhfuzz/func_coverage.h"

static func_coverage_t *g_fcov = NULL;

bool fcov_initBitmap(const char* session_path, unsigned target_bm_fd) {

    char bitmap_file[128];
    snprintf(bitmap_file, sizeof(bitmap_file), "%s/fcov.map", session_path);

    unlink(bitmap_file);
    PLOG_W("bitmap_file: %s", bitmap_file);

    int fd = open(bitmap_file, O_RDWR | O_CREAT | O_TRUNC, 0600);
    if (fd < 0) {
        perror("open");
        return false;
    }

    if (ftruncate(fd, sizeof(func_coverage_t)) != 0) {
        perror("ftruncate");
        close(fd);
        return NULL;
    }

    void *map = mmap(NULL, sizeof(func_coverage_t), PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    if (map == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return false;
    }

    g_fcov = (func_coverage_t*)map;
    g_fcov->fcov_fd      = fd;
    g_fcov->edge_count   = 0;
    g_fcov->func_count   = 0;
    g_fcov->block_writes = false;

    /* let taget bitmap fd (_HF_FCOV_MAP_FD) points to the shared file */
    if (dup2(g_fcov->fcov_fd, target_bm_fd) == -1) {
        PLOG_E("dup2(%d, target_bm_fd=%d) failed", g_fcov->fcov_fd, target_bm_fd);
        return false;
    }

    return true;
}



