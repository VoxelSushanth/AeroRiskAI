package orderbook

type Level struct {
	Price    int64
	Quantity int64
	OrderCount int
}

func NewLevelFromPrice(price int64) *Level {
	return &Level{
		Price:      price,
		Quantity:   0,
		OrderCount: 0,
	}
}
