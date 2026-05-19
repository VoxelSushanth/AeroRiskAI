package disruptor

import "sync/atomic"

type EventSlot[T any] struct {
	sequence int64
	event    T
	padding  [7]int64
}

func NewEventSlot[T any]() *EventSlot[T] {
	return &EventSlot[T]{
		sequence: -1,
	}
}

func (s *EventSlot[T]) Sequence() int64 {
	return atomic.LoadInt64(&s.sequence)
}

func (s *EventSlot[T]) SetSequence(seq int64) {
	atomic.StoreInt64(&s.sequence, seq)
}

func (s *EventSlot[T]) Event() *T {
	return &s.event
}
