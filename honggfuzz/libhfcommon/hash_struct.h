#ifndef _HASH_STRUCT_H_
#define _HASH_STRUCT_H_
#include <pthread.h>
#include "hash.h"

#define M_BASE_DATA_NUM (16UL * 1024UL)

#define mutex_lock_t           pthread_mutex_t
#define mutex_lock_init(x)     pthread_mutex_init(x, NULL)
#define mutex_lock(x)          pthread_mutex_lock(x);
#define mutex_unlock(x)        pthread_mutex_unlock(x);


/* Node structure */
typedef struct hashNode {
    struct hashNode *pail_next;
    struct hashNode *pail_prev;
    struct hashNode *data_next;
    struct hashNode *data_prev;

    uint32_t data_id : 24;
    uint32_t thread_no : 8;
    uint32_t pail_index;

#define KeyArea(node) ((uint8_t *)(node + 1))
#define DataArea(node, keylen) ((uint8_t *)(node + 1) + keylen)
} hashNode_t;

/* Hash bucket */
typedef struct {
    hashNode_t *head;
} hashPail_t;

/* List management */
typedef struct {
    hashNode_t *head;
    hashNode_t *tail;
    uint32_t count;
    uint32_t reserved;
} dataManage_t;

/* Memory chunk */
typedef struct memList {
    char *addr;
    struct memList *next;
} memList_t;

/* Memory unit tracking */
typedef struct {
    uint32_t unit_count;
    uint32_t node_count;
    memList_t *head;
} memUnit_t;

/* Core table structure */
typedef struct {
    dataManage_t busy;
    dataManage_t idle;

    mutex_lock_t idle_lock;
    mutex_lock_t busy_lock;

    hashPail_t *buckets;

    uint32_t type;
    uint32_t data_len;
    uint32_t bucket_count;
    uint32_t max_nodes;
    uint32_t init_nodes;
    uint32_t key_len;
    uint32_t create_count;
    uint32_t delete_count;

    memUnit_t mem_unit;
} hashTable_t;

/* Table manager */
typedef struct {
    hashTable_t tables[HF_HASH_TYPE_END];
    uint32_t count;
} hashTableManager_t;

#endif
