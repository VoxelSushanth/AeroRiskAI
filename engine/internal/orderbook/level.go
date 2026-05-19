package orderbook

import (
	"github.com/aerorisk/engine/pkg/financial"
)

type Level struct {
	Price      int64
	Quantity   financial.Quantity
	OrderCount int
	Orders     []*Order
}

func NewLevelFromPrice(price int64) *Level {
	return &Level{
		Price:      price,
		Quantity:   0,
		OrderCount: 0,
		Orders:     make([]*Order, 0),
	}
}

func (l *Level) AddOrder(order *Order) {
	l.Orders = append(l.Orders, order)
	l.Quantity += order.Quantity
	l.OrderCount++
}

func (l *Level) RemoveOrder(orderID uint64) {
	for i, order := range l.Orders {
		if order.ID == orderID {
			l.Quantity -= order.Quantity
			l.OrderCount--
			l.Orders = append(l.Orders[:i], l.Orders[i+1:]...)
			break
		}
	}
}
