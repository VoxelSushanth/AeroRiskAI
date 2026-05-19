package disruptor

import (
	"sync"
)

type BatchProcessor[T any] struct {
	buffer     *RingBuffer[T]
	handlers   []func(*T)
	wg         sync.WaitGroup
	done       chan struct{}
	batchSize  int
}

func NewBatchProcessor[T any](buffer *RingBuffer[T], batchSize int) *BatchProcessor[T] {
	return &BatchProcessor[T]{
		buffer:    buffer,
		batchSize: batchSize,
		done:      make(chan struct{}),
	}
}

func (bp *BatchProcessor[T]) AddHandler(handler func(*T)) {
	bp.handlers = append(bp.handlers, handler)
}

func (bp *BatchProcessor[T]) Start() {
	bp.wg.Add(1)
	go bp.processLoop()
}

func (bp *BatchProcessor[T]) processLoop() {
	defer bp.wg.Done()

	sequence := int64(0)
	for {
		select {
		case <-bp.done:
			return
		default:
			batch := make([]*T, 0, bp.batchSize)
			for i := 0; i < bp.batchSize; i++ {
				seq := sequence + int64(i) + 1
				event := bp.buffer.Get(seq)
				if event != nil {
					batch = append(batch, event)
					sequence = seq
				} else {
					break
				}
			}

			for _, event := range batch {
				for _, handler := range bp.handlers {
					handler(event)
				}
			}
		}
	}
}

func (bp *BatchProcessor[T]) Stop() {
	close(bp.done)
	bp.wg.Wait()
}
