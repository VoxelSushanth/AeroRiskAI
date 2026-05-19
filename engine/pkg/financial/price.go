package financial

import "fmt"

type Price int64

func NewPrice(value int64) Price {
	return Price(value)
}

func (p Price) Value() int64 {
	return int64(p)
}

func (p Price) String() string {
	return fmt.Sprintf("%d.%04d", p/10000, p%10000)
}
