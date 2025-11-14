#include "hash_struct.h"

static hashTableManager_t *g_hash_mgr = NULL;

static inline void *hash_malloc(size_t size) {
    void *mem = malloc(size);
    assert(mem);
    memset(mem, 0, size);
    return mem;
}

static inline uint32_t hash_calcBuckets(uint32_t nodes) {
    uint32_t buckets = nodes << 3;
    for (;;) {
        uint32_t i;
        for (i = 2; i < 1000; i++) {
            if (buckets % i == 0) break;
        }
        if (i == 1000) break;
        buckets++;
    }
    return buckets;
}

static inline hashTable_t *hash_getTable(uint32_t type) {
    if (type >= HF_HASH_TYPE_END) return NULL;
    return &g_hash_mgr->tables[type];
}

static inline uint8_t *hash_getMemAddr(hashTable_t *tbl) {
    assert(tbl->mem_unit.head);
    return (uint8_t *)tbl->mem_unit.head->addr;
}

static inline uint32_t hash_newDataID(hashTable_t *tbl) {
    assert(tbl->mem_unit.head);

    tbl->init_nodes++;
    return (tbl->mem_unit.unit_count - 1) * tbl->max_nodes + tbl->init_nodes;
}

static inline hashNode_t *hash_newNode(hashTable_t *tbl) {
    if (tbl->init_nodes >= tbl->max_nodes) return NULL;

    size_t node_sz = sizeof(hashNode_t) + tbl->key_len + tbl->data_len;
    uint8_t *base = hash_getMemAddr(tbl);
    hashNode_t *node = (hashNode_t *)(base + node_sz * tbl->init_nodes);
    node->data_id = hash_newDataID(tbl);

    return node;
}

static inline uint32_t hash_hashKey(uint8_t *key, uint32_t len) {
    uint32_t hash = 5381;
    for (uint32_t i = 0; i < len; i++) {
        hash = ((hash << 5) + hash) + key[i];
    }
    return hash;
}

bool hash_createTable(uint32_t type, uint32_t data_len, uint32_t key_len) {
    if (type >= HF_HASH_TYPE_END) return false;

    hashTable_t *tbl = &g_hash_mgr->tables[type];
    tbl->type = type;
    tbl->data_len = data_len;
    tbl->key_len = key_len;
    tbl->max_nodes = M_BASE_DATA_NUM;
    tbl->buckets = (hashPail_t *)hash_malloc(sizeof(hashPail_t) * hash_calcBuckets(tbl->max_nodes));
    tbl->bucket_count = hash_calcBuckets(tbl->max_nodes);
    mutex_lock_init(&tbl->idle_lock);
    mutex_lock_init(&tbl->busy_lock);

    size_t unit_sz = (sizeof(hashNode_t) + tbl->key_len + tbl->data_len) * (tbl->max_nodes + 1);
    memList_t *ml = (memList_t *)hash_malloc(unit_sz + sizeof(memList_t));
    ml->addr = (char *)(ml + 1);
    ml->next = NULL;

    tbl->mem_unit.head = ml;
    tbl->mem_unit.unit_count = 1;
    tbl->mem_unit.node_count = tbl->max_nodes;
    tbl->init_nodes = 0;
    tbl->create_count = 0;
    tbl->delete_count = 0;

    return true;
}

bool hash_createByKey(hashReq_t *req, hashAck_t *ack) {
    hashTable_t *tbl = hash_getTable(req->type);
    if (!tbl || tbl->key_len != req->key_len) return false;

    hashNode_t *node = hash_newNode(tbl);
    if (!node) return false;

    memcpy(KeyArea(node), req->key, req->key_len);
    node->pail_index = hash_hashKey((uint8_t *)req->key, req->key_len) % tbl->bucket_count;

    hashPail_t *pail = &tbl->buckets[node->pail_index];
    node->pail_next = pail->head;
    if (pail->head) pail->head->pail_prev = node;
    node->pail_prev = NULL;
    pail->head = node;

    ack->id = node->data_id;
    ack->data = DataArea(node, tbl->key_len);
    return true;
}

bool hash_createByID(hashReq_t *req, hashAck_t *ack) {
    hashTable_t *tbl = hash_getTable(req->type);
    if (!tbl) return false;

    hashNode_t *node = hash_newNode(tbl);
    if (!node) return false;

    ack->id = node->data_id;
    ack->data = DataArea(node, tbl->key_len);
    return true;
}

bool hash_queryByKey(hashReq_t *req, hashAck_t *ack) {
    hashTable_t *tbl = hash_getTable(req->type);
    if (!tbl || tbl->key_len != req->key_len) return false;

    uint32_t idx = hash_hashKey((uint8_t *)req->key, req->key_len) % tbl->bucket_count;
    hashNode_t *cur = tbl->buckets[idx].head;
    while (cur) {
        if (memcmp(KeyArea(cur), req->key, req->key_len) == 0) {
            ack->id = cur->data_id;
            ack->data = DataArea(cur, tbl->key_len);
            return true;
        }
        cur = cur->pail_next;
    }
    return false;
}

bool hash_queryByID(hashReq_t *req, hashAck_t *ack) {
    hashTable_t *tbl = hash_getTable(req->type);
    if (!tbl || req->id == 0 || req->id > tbl->max_nodes) return false;

    uint32_t unit = req->id / tbl->mem_unit.node_count;
    memList_t *ml = tbl->mem_unit.head;
    while (unit-- && ml) ml = ml->next;
    if (!ml) return false;

    size_t node_sz = sizeof(hashNode_t) + tbl->key_len + tbl->data_len;
    uint32_t offset = (req->id % tbl->mem_unit.node_count) - 1;
    hashNode_t *node = (hashNode_t *)(ml->addr + offset * node_sz);
    ack->id = node->data_id;
    ack->data = DataArea(node, tbl->key_len);
    return true;
}

bool hash_deleteByID(hashReq_t *req) {
    hashTable_t *tbl = hash_getTable(req->type);
    if (!tbl || req->id == 0 || req->id > tbl->max_nodes) return false;

    uint32_t unit = req->id / tbl->mem_unit.node_count;
    memList_t *ml = tbl->mem_unit.head;
    while (unit-- && ml) ml = ml->next;
    if (!ml) return false;

    size_t node_sz = sizeof(hashNode_t) + tbl->key_len + tbl->data_len;
    uint32_t offset = (req->id % tbl->mem_unit.node_count) - 1;
    hashNode_t *node = (hashNode_t *)(ml->addr + offset * node_sz);

    if (tbl->key_len > 0) {
        hashPail_t *pail = &tbl->buckets[node->pail_index];
        if (pail->head == node) {
            pail->head = node->pail_next;
            if (pail->head) pail->head->pail_prev = NULL;
        } else {
            if (node->pail_prev) node->pail_prev->pail_next = node->pail_next;
            if (node->pail_next) node->pail_next->pail_prev = node->pail_prev;
        }
    }
    return true;
}

void hash_init(void *addr) {
    if (addr) {
        g_hash_mgr = (hashTableManager_t *)addr;
    } else {
        g_hash_mgr = (hashTableManager_t *)hash_malloc(sizeof(hashTableManager_t));
    }
}

void *hash_getHashAddr(void) {
    return g_hash_mgr;
}

void hash_delTables(void) {
    for (uint32_t i = HF_HASH_TYPE_BEGIN; i < HF_HASH_TYPE_END; i++) {
        hashTable_t *tbl = &g_hash_mgr->tables[i];
        memList_t *ml = tbl->mem_unit.head;
        while (ml) {
            memList_t *next = ml->next;
            free(ml);
            ml = next;
        }
        free(tbl->buckets);
        memset(tbl, 0, sizeof(hashTable_t));
    }
}

uint32_t hash_queryDataNum(uint32_t type) {
    if (type >= HF_HASH_TYPE_END) return 0;
    hashTable_t *tbl = hash_getTable(type);
    return tbl ? tbl->busy.count : 0;
}
