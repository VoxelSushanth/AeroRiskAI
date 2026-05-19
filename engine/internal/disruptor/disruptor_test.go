package disruptor

import (
	"sync/atomic"
	"testing"
)

func TestRingBuffer_Next(t *testing.T) {
	rb := NewRingBuffer[int](1024)

	seq := rb.Next()
	if seq != 0 {
		t.Errorf("expected sequence 0, got %d", seq)
	}

	seq = rb.Next()
	if seq != 1 {
		t.Errorf("expected sequence 1, got %d", seq)
	}
}

func TestRingBuffer_Get(t *testing.T) {
	rb := NewRingBuffer[int](1024)

	seq := rb.Next()
	rb.buffer[seq&rb.mask].event = 42
	rb.Publish(seq)

	val := rb.Get(seq)
	if *val != 42 {
		t.Errorf("expected 42, got %d", *val)
	}
}

func TestRingBuffer_Publish(t *testing.T) {
	rb := NewRingBuffer[int](1024)

	seq := rb.Next()
	rb.buffer[seq&rb.mask].event = 100
	rb.Publish(seq)

	slot := &rb.buffer[seq&rb.mask]
	if atomic.LoadInt64(&slot.sequence) != seq {
		t.Error("sequence not published")
	}
}

func TestSequencer_Next(t *testing.T) {
	s := NewSequencer()

	seq := s.Next()
	if seq != 0 {
		t.Errorf("expected sequence 0, got %d", seq)
	}

	seq = s.Next()
	if seq != 1 {
		t.Errorf("expected sequence 1, got %d", seq)
	}
}

func TestBatchProcessor(t *testing.T) {
	rb := NewRingBuffer[int](1024)
	bp := NewBatchProcessor(rb, 10)

	received := make(chan int, 100)
	bp.AddHandler(func(v *int) {
		received <- *v
	})

	bp.Start()

	for i := 0; i < 5; i++ {
		seq := rb.Next()
		rb.buffer[seq&rb.mask].event = i
		rb.Publish(seq)
	}

	for i := 0; i < 5; i++ {
		select {
		case v := <-received:
			if v != i {
				t.Errorf("expected %d, got %d", i, v)
			}
		default:
		}
	}

	bp.Stop()
}
