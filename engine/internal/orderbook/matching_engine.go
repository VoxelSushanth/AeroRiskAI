package orderbook

import (
	"sync"

	"github.com/aerorisk/engine/pkg/financial"
)

type Trade struct {
	Price    financial.Price
	Quantity financial.Quantity
	BuyerID  uint64
	SellerID uint64
}

type MatchingEngine struct {
	orderBooks map[financial.Symbol]*OrderBook
	tradeChan  chan *Trade
	mu         sync.RWMutex
}

func NewMatchingEngine() *MatchingEngine {
	return &MatchingEngine{
		orderBooks: make(map[financial.Symbol]*OrderBook),
		tradeChan:  make(chan *Trade, 10000),
	}
}

func (me *MatchingEngine) GetOrderBook(symbol financial.Symbol) *OrderBook {
	me.mu.Lock()
	defer me.mu.Unlock()

	ob, exists := me.orderBooks[symbol]
	if !exists {
		ob = NewOrderBook(symbol)
		me.orderBooks[symbol] = ob
	}
	return ob
}

func (me *MatchingEngine) SubmitOrder(order *Order) []*Trade {
	ob := me.GetOrderBook(order.Symbol)
	return me.matchOrder(ob, order)
}

func (me *MatchingEngine) matchOrder(ob *OrderBook, order *Order) []*Trade {
	var trades []*Trade

	if order.Side == SideBuy {
		for ob.BestAsk() != nil && ob.BestAsk().Price <= order.Price.Value() && order.Quantity > 0 {
			bestAsk := ob.BestAsk()
			if len(bestAsk.Orders) == 0 {
				break
			}

			askOrder := bestAsk.Orders[0]
			matchQty := min(order.Quantity, askOrder.Quantity)

			trade := &Trade{
				Price:    askOrder.Price,
				Quantity: matchQty,
				BuyerID:  order.ID,
				SellerID: askOrder.ID,
			}
			trades = append(trades, trade)
			me.tradeChan <- trade

			order.Quantity -= matchQty
			askOrder.Quantity -= matchQty
			ob.bestAsk = -1

			if askOrder.Quantity == 0 {
				bestAsk.Orders = bestAsk.Orders[1:]
			}
		}

		if order.Quantity > 0 {
			ob.AddOrder(order)
		}
	} else {
		for ob.BestBid() != nil && ob.BestBid().Price >= order.Price.Value() && order.Quantity > 0 {
			bestBid := ob.BestBid()
			if len(bestBid.Orders) == 0 {
				break
			}

			bidOrder := bestBid.Orders[0]
			matchQty := min(order.Quantity, bidOrder.Quantity)

			trade := &Trade{
				Price:    bidOrder.Price,
				Quantity: matchQty,
				BuyerID:  bidOrder.ID,
				SellerID: order.ID,
			}
			trades = append(trades, trade)
			me.tradeChan <- trade

			order.Quantity -= matchQty
			bidOrder.Quantity -= matchQty
			ob.bestBid = -1

			if bidOrder.Quantity == 0 {
				bestBid.Orders = bestBid.Orders[1:]
			}
		}

		if order.Quantity > 0 {
			ob.AddOrder(order)
		}
	}

	return trades
}

func (me *MatchingEngine) CancelOrder(symbol financial.Symbol, orderID uint64, side Side, price financial.Price) {
	ob := me.GetOrderBook(symbol)
	ob.CancelOrder(orderID, side, price)
}

func (me *MatchingEngine) TradeChannel() <-chan *Trade {
	return me.tradeChan
}

func min(a, b financial.Quantity) financial.Quantity {
	if a < b {
		return a
	}
	return b
}
