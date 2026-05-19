package financial

type Symbol string

func NewSymbol(s string) Symbol {
	return Symbol(s)
}

func (s Symbol) String() string {
	return string(s)
}
