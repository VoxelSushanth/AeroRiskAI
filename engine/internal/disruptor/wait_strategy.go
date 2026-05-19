package disruptor

import (
	"runtime"
	"sync/atomic"
)

type WaitStrategy interface {
	WaitFor(sequence int64, cursor *int64) int64
}

type BusySpinWaitStrategy struct{}

func (b *BusySpinWaitStrategy) WaitFor(sequence int64, cursor *int64) int64 {
	for {
		available := atomic.LoadInt64(cursor)
		if available >= sequence {
			return available
		}
		runtime.Gosched()
	}
}

type YieldingWaitStrategy struct{}

func (y *YieldingWaitStrategy) WaitFor(sequence int64, cursor *int64) int64 {
	counter := 0
	for {
		available := atomic.LoadInt64(cursor)
		if available >= sequence {
			return available
		}
		counter++
		if counter > 10 {
			runtime.Gosched()
		}
	}
}
