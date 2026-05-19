package orderbook

import (
	"testing"

	"github.com/aerorisk/engine/pkg/financial"
)

func TestOrderBook_AddOrder(t *testing.T) {
	symbol := financial.NewSymbol("AAPL")
	ob := NewOrderBook(symbol)

	order := NewOrder(1, symbol, SideBuy, financial.NewPrice(10000), financial.NewQuantity(100))
	ob.AddOrder(order)

	bestBid := ob.BestBid()
	if bestBid == nil {
		t.Fatal("expected best bid to exist")
	}

	if bestBid.Price.Value() != 10000 {
		t.Errorf("expected price 10000, got %d", bestBid.Price.Value())
	}
}

func TestOrderBook_CancelOrder(t *testing.T) {
	symbol := financial.NewSymbol("AAPL")
	ob := NewOrderBook(symbol)

	order := NewOrder(1, symbol, SideBuy, financial.NewPrice(10000), financial.NewQuantity(100))
	ob.AddOrder(order)

	ob.CancelOrder(1, SideBuy, financial.NewPrice(10000))

	bestBid := ob.BestBid()
	if bestBid != nil && len(bestBid.Orders) > 0 {
		t.Error("expected order to be cancelled")
	}
}

func TestMatchingEngine_Match(t *testing.T) {
	me := NewMatchingEngine()
	symbol := financial.NewSymbol("AAPL")

	buyOrder := NewOrder(1, symbol, SideBuy, financial.NewPrice(10000), financial.NewQuantity(100))
	sellOrder := NewOrder(2, symbol, SideSell, financial.NewPrice(10000), financial.NewQuantity(50))

	me.SubmitOrder(buyOrder)
	trades := me.SubmitOrder(sellOrder)

	if len(trades) != 1 {
		t.Fatalf("expected 1 trade, got %d", len(trades))
	}

	if trades[0].Quantity != 50 {
		t.Errorf("expected quantity 50, got %d", trades[0].Quantity)
	}
}

func TestOrderBook_Spread(t *testing.T) {
	symbol := financial.NewSymbol("AAPL")
	ob := NewOrderBook(symbol)

	bidOrder := NewOrder(1, symbol, SideBuy, financial.NewPrice(9900), financial.NewQuantity(100))
	askOrder := NewOrder(2, symbol, SideSell, financial.NewPrice(10100), financial.NewQuantity(100))

	ob.AddOrder(bidOrder)
	ob.AddOrder(askOrder)

	spread := ob.Spread()
	if spread != 200 {
		t.Errorf("expected spread 200, got %d", spread)
	}
}
