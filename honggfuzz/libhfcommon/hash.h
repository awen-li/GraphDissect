#ifndef _HASH_H_
#define _HASH_H_

#include <stdint.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <assert.h>

/* Hash table types */
typedef enum {
    HF_HASH_TYPE_BEGIN = 1,
    HF_HASH_TYPE_FUNCTION = HF_HASH_TYPE_BEGIN,
    HF_HASH_TYPE_END
} hashType_t;

typedef struct {
    uint8_t  *key;
    uint32_t key_len;
    uint32_t type;
    uint32_t id;
} hashReq_t;

typedef struct {
    uint8_t  *data;
    uint32_t id;
    uint32_t reserved;
} hashAck_t;

/* API */
bool hash_createByKey(hashReq_t *req, hashAck_t *ack);
bool hash_queryByKey(hashReq_t *req, hashAck_t *ack);
bool hash_createNoKey(hashReq_t *req, hashAck_t *ack);
bool hash_queryById(hashReq_t *req, hashAck_t *ack);
bool hash_deleteById(hashReq_t *req);
bool hash_createTable(uint32_t type, uint32_t data_len, uint32_t key_len);
uint32_t hash_queryCount(uint32_t type);
void     hash_destroyAll(void);
void     hash_init(void *addr);
void    *hash_getStorage(void);


#endif 
