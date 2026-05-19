package disruptor

import (
	"sync/atomic"
)

type Sequencer struct {
	cursor  int64
	padding [7]int64
}

func NewSequencer() *Sequencer {
	return &Sequencer{
		cursor: -1,
	}
}

func (s *Sequencer) Next() int64 {
	return atomic.AddInt64(&s.cursor, 1)
}

func (s *Sequencer) Cursor() int64 {
	return atomic.LoadInt64(&s.cursor)
}
