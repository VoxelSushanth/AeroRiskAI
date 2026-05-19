package disruptor

import (
	"runtime"
	"sync/atomic"
)

type EventSlot[T any] struct {
	sequence int64
	event    T
	padding  [7]int64
}

type RingBuffer[T any] struct {
	buffer  []EventSlot[T]
	mask    int64
	cursor  int64
	gate    int64
	padding [7]int64
}

func NewRingBuffer[T any](size int) *RingBuffer[T] {
	powerOf2 := 1
	for powerOf2 < size {
		powerOf2 *= 2
	}

	buffer := make([]EventSlot[T], powerOf2)
	for i := range buffer {
		buffer[i].sequence = -1
	}

	return &RingBuffer[T]{
		buffer: buffer,
		mask:   int64(powerOf2 - 1),
		cursor: -1,
		gate:   -1,
	}
}

func (rb *RingBuffer[T]) Next() int64 {
	for {
		current := atomic.LoadInt64(&rb.cursor)
		next := current + 1

		if atomic.CompareAndSwapInt64(&rb.cursor, current, next) {
			index := next & rb.mask
			slot := &rb.buffer[index]

			for {
				seq := atomic.LoadInt64(&slot.sequence)
				if seq < next {
					if atomic.CompareAndSwapInt64(&slot.sequence, seq, next) {
						return next
					}
				} else {
					runtime.Gosched()
				}
			}
		}
		runtime.Gosched()
	}
}

func (rb *RingBuffer[T]) Get(sequence int64) *T {
	index := sequence & rb.mask
	return &rb.buffer[index].event
}

func (rb *RingBuffer[T]) Publish(sequence int64) {
	index := sequence & rb.mask
	slot := &rb.buffer[index]
	atomic.StoreInt64(&slot.sequence, sequence)
}

func (rb *RingBuffer[T]) Size() int64 {
	return atomic.LoadInt64(&rb.cursor) - atomic.LoadInt64(&rb.gate)
}
