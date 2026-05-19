package gateway

import (
	"sync"
	"time"
)

type RateLimiter struct {
	tokens     map[uint64]*tokenBucket
	mu         sync.RWMutex
	maxTokens  int64
	refillRate time.Duration
}

type tokenBucket struct {
	tokens     int64
	lastRefill time.Time
}

func NewRateLimiter(maxTokens int64, refillRate time.Duration) *RateLimiter {
	return &RateLimiter{
		tokens:     make(map[uint64]*tokenBucket),
		maxTokens:  maxTokens,
		refillRate: refillRate,
	}
}

func (rl *RateLimiter) Allow(userID uint64) bool {
	rl.mu.Lock()
	defer rl.mu.Unlock()

	bucket, exists := rl.tokens[userID]
	if !exists {
		bucket = &tokenBucket{
			tokens:     rl.maxTokens,
			lastRefill: time.Now(),
		}
		rl.tokens[userID] = bucket
	}

	rl.refill(bucket)

	if bucket.tokens > 0 {
		bucket.tokens--
		return true
	}

	return false
}

func (rl *RateLimiter) refill(bucket *tokenBucket) {
	now := time.Now()
	elapsed := now.Sub(bucket.lastRefill)
	tokensToAdd := int64(elapsed / rl.refillRate)

	if tokensToAdd > 0 {
		bucket.tokens = min64(bucket.tokens+tokensToAdd, rl.maxTokens)
		bucket.lastRefill = now
	}
}

func min64(a, b int64) int64 {
	if a < b {
		return a
	}
	return b
}
