package orderbook

import "github.com/aerorisk/engine/pkg/financial"

type Side int

const (
	SideUnknown Side = iota
	SideBuy
	SideSell
)

type Order struct {
	ID        uint64          `json:"id"`
	Symbol    financial.Symbol `json:"symbol"`
	Side      Side            `json:"side"`
	Price     financial.Price  `json:"price"`
	Quantity  financial.Quantity `json:"quantity"`
	Timestamp int64           `json:"timestamp"`
}

func NewOrder(id uint64, symbol financial.Symbol, side Side, price financial.Price, quantity financial.Quantity) *Order {
	return &Order{
		ID:       id,
		Symbol:   symbol,
		Side:     side,
		Price:    price,
		Quantity: quantity,
	}
}
