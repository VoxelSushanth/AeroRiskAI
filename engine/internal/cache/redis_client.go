package cache

import (
"context"
"fmt"
"time"

"github.com/go-redis/redis/v8"
)

type RedisClient struct {
client *redis.Client
}

func NewRedisClient(addr string) *RedisClient {
client := redis.NewClient(&redis.Options{
Addr:         addr,
Password:     "",
DB:           0,
PoolSize:     100,
MinIdleConns: 10,
DialTimeout:  5 * time.Second,
ReadTimeout:  3 * time.Second,
WriteTimeout: 3 * time.Second,
PoolTimeout:  5 * time.Second,
})

return &RedisClient{
client: client,
}
}

func (c *RedisClient) Ping(ctx context.Context) error {
return c.client.Ping(ctx).Err()
}

func (c *RedisClient) Close() error {
return c.client.Close()
}

func (c *RedisClient) Get(ctx context.Context, key string) ([]byte, error) {
val, err := c.client.Get(ctx, key).Bytes()
if err == redis.Nil {
return nil, nil
}
return val, err
}

func (c *RedisClient) Set(ctx context.Context, key string, value []byte, expiration time.Duration) error {
return c.client.Set(ctx, key, value, expiration).Err()
}

func (c *RedisClient) Del(ctx context.Context, keys ...string) error {
return c.client.Del(ctx, keys...).Err()
}

func (c *RedisClient) Exists(ctx context.Context, key string) (bool, error) {
n, err := c.client.Exists(ctx, key).Result()
return n > 0, err
}

func (c *RedisClient) Incr(ctx context.Context, key string) (int64, error) {
return c.client.Incr(ctx, key).Result()
}

func (c *RedisClient) Decr(ctx context.Context, key string) (int64, error) {
return c.client.Decr(ctx, key).Result()
}

func (c *RedisClient) HGet(ctx context.Context, key, field string) ([]byte, error) {
val, err := c.client.HGet(ctx, key, field).Bytes()
if err == redis.Nil {
return nil, nil
}
return val, err
}

func (c *RedisClient) HSet(ctx context.Context, key, field string, value interface{}) error {
return c.client.HSet(ctx, key, field, value).Err()
}

func (c *RedisClient) HDel(ctx context.Context, key string, fields ...string) error {
return c.client.HDel(ctx, key, fields...).Err()
}

func (c *RedisClient) HGetAll(ctx context.Context, key string) (map[string]string, error) {
return c.client.HGetAll(ctx, key).Result()
}

func (c *RedisClient) Publish(ctx context.Context, channel string, message interface{}) error {
return c.client.Publish(ctx, channel, message).Err()
}

func (c *RedisClient) Subscribe(ctx context.Context, channels ...string) *redis.PubSub {
return c.client.Subscribe(ctx, channels...)
}

const (
KeyPrefixAccount      = "acct:"
KeyPrefixCircuitBreak = "cb:"
KeyPrefixOrder        = "ord:"
KeyPrefixPosition     = "pos:"
)

func AccountKey(accountID string) string {
return fmt.Sprintf("%s%s", KeyPrefixAccount, accountID)
}

func CircuitBreakKey(accountID string) string {
return fmt.Sprintf("%s%s", KeyPrefixCircuitBreak, accountID)
}

func OrderKey(orderID string) string {
return fmt.Sprintf("%s%s", KeyPrefixOrder, orderID)
}

func PositionKey(accountID, symbol string) string {
return fmt.Sprintf("%s%s:%s", KeyPrefixPosition, accountID, symbol)
}
