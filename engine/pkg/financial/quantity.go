package financial

import "fmt"

type Quantity int64

func NewQuantity(value int64) Quantity {
	return Quantity(value)
}

func (q Quantity) Value() int64 {
	return int64(q)
}

func (q Quantity) String() string {
	return fmt.Sprintf("%d", q)
}
