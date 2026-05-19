package orderbook

import (
	"sync"

	"github.com/aerorisk/engine/pkg/financial"
)

type Level struct {
	Price    financial.Price
	Quantity financial.Quantity
	Orders   []*Order
}

func NewLevel(price financial.Price) *Level {
	return &Level{
		Price:    price,
		Quantity: 0,
		Orders:   make([]*Order, 0),
	}
}

func (l *Level) AddOrder(order *Order) {
	l.Orders = append(l.Orders, order)
	l.Quantity += order.Quantity
}

func (l *Level) RemoveOrder(orderID uint64) {
	for i, order := range l.Orders {
		if order.ID == orderID {
			l.Quantity -= order.Quantity
			l.Orders = append(l.Orders[:i], l.Orders[i+1:]...)
			break
		}
	}
}

type OrderBook struct {
	symbol     financial.Symbol
	bidLevels  map[int64]*Level
	askLevels  map[int64]*Level
	bestBid    int64
	bestAsk    int64
	mu         sync.RWMutex
}

func NewOrderBook(symbol financial.Symbol) *OrderBook {
	return &OrderBook{
		symbol:    symbol,
		bidLevels: make(map[int64]*Level),
		askLevels: make(map[int64]*Level),
		bestBid:   -1,
		bestAsk:   -1,
	}
}

func (ob *OrderBook) AddOrder(order *Order) {
	ob.mu.Lock()
	defer ob.mu.Unlock()

	price := order.Price.Value()
	var levels map[int64]*Level

	if order.Side == SideBuy {
		levels = ob.bidLevels
		if price > ob.bestBid {
			ob.bestBid = price
		}
	} else {
		levels = ob.askLevels
		if ob.bestAsk == -1 || price < ob.bestAsk {
			ob.bestAsk = price
		}
	}

	level, exists := levels[price]
	if !exists {
		level = NewLevel(order.Price)
		levels[price] = level
	}

	level.AddOrder(order)
}

func (ob *OrderBook) CancelOrder(orderID uint64, side Side, price financial.Price) {
	ob.mu.Lock()
	defer ob.mu.Unlock()

	var levels map[int64]*Level
	if side == SideBuy {
		levels = ob.bidLevels
	} else {
		levels = ob.askLevels
	}

	level, exists := levels[price.Value()]
	if exists {
		level.RemoveOrder(orderID)
		if len(level.Orders) == 0 {
			delete(levels, price.Value())
		}
	}
}

func (ob *OrderBook) BestBid() *Level {
	ob.mu.RLock()
	defer ob.mu.RUnlock()

	if ob.bestBid == -1 {
		return nil
	}
	return ob.bidLevels[ob.bestBid]
}

func (ob *OrderBook) BestAsk() *Level {
	ob.mu.RLock()
	defer ob.mu.RUnlock()

	if ob.bestAsk == -1 {
		return nil
	}
	return ob.askLevels[ob.bestAsk]
}

func (ob *OrderBook) Spread() int64 {
	ob.mu.RLock()
	defer ob.mu.RUnlock()

	if ob.bestBid == -1 || ob.bestAsk == -1 {
		return -1
	}
	return ob.bestAsk - ob.bestBid
}
