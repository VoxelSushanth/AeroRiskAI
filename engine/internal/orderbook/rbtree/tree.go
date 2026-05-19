package rbtree

type Color int

const (
	Red Color = iota
	Black
)

type Node[T any] struct {
	key    T
	value  interface{}
	color  Color
	left   *Node[T]
	right  *Node[T]
	parent *Node[T]
}

type RBTree[T any] struct {
	root *Node[T]
	size int
}

func NewRBTree[T any]() *RBTree[T] {
	return &RBTree[T]{}
}

func (t *RBTree[T]) Insert(key T, value interface{}) {
	node := &Node[T]{
		key:   key,
		value: value,
		color: Red,
	}

	var parent *Node[T]
	current := t.root

	for current != nil {
		parent = current
		if less(key, current.key) {
			current = current.left
		} else if greater(key, current.key) {
			current = current.right
		} else {
			current.value = value
			return
		}
	}

	node.parent = parent
	if parent == nil {
		t.root = node
	} else if less(key, parent.key) {
		parent.left = node
	} else {
		parent.right = node
	}

	t.fixInsert(node)
	t.size++
}

func (t *RBTree[T]) fixInsert(node *Node[T]) {
	for node.parent != nil && node.parent.color == Red {
		if node.parent == node.parent.parent.left {
			uncle := node.parent.parent.right
			if uncle != nil && uncle.color == Red {
				node.parent.color = Black
				uncle.color = Black
				node.parent.parent.color = Red
				node = node.parent.parent
			} else {
				if node == node.parent.right {
					node = node.parent
					t.rotateLeft(node)
				}
				node.parent.color = Black
				node.parent.parent.color = Red
				t.rotateRight(node.parent.parent)
			}
		} else {
			uncle := node.parent.parent.left
			if uncle != nil && uncle.color == Red {
				node.parent.color = Black
				uncle.color = Black
				node.parent.parent.color = Red
				node = node.parent.parent
			} else {
				if node == node.parent.left {
					node = node.parent
					t.rotateRight(node)
				}
				node.parent.color = Black
				node.parent.parent.color = Red
				t.rotateLeft(node.parent.parent)
			}
		}
	}
	if t.root != nil {
		t.root.color = Black
	}
}

func (t *RBTree[T]) rotateLeft(node *Node[T]) {
	right := node.right
	node.right = right.left
	if right.left != nil {
		right.left.parent = node
	}
	right.parent = node.parent
	if node.parent == nil {
		t.root = right
	} else if node == node.parent.left {
		node.parent.left = right
	} else {
		node.parent.right = right
	}
	right.left = node
	node.parent = right
}

func (t *RBTree[T]) rotateRight(node *Node[T]) {
	left := node.left
	node.left = left.right
	if left.right != nil {
		left.right.parent = node
	}
	left.parent = node.parent
	if node.parent == nil {
		t.root = left
	} else if node == node.parent.right {
		node.parent.right = left
	} else {
		node.parent.left = left
	}
	left.right = node
	node.parent = left
}

func (t *RBTree[T]) Search(key T) interface{} {
	current := t.root
	for current != nil {
		if less(key, current.key) {
			current = current.left
		} else if greater(key, current.key) {
			current = current.right
		} else {
			return current.value
		}
	}
	return nil
}

func (t *RBTree[T]) Size() int {
	return t.size
}

// Helper functions for comparing values of type T
func less[T any](a, b T) bool {
	switch v := any(a).(type) {
	case int:
		return v < any(b).(int)
	case int64:
		return v < any(b).(int64)
	case uint64:
		return v < any(b).(uint64)
	case float64:
		return v < any(b).(float64)
	default:
		panic("unsupported type for comparison")
	}
}

func greater[T any](a, b T) bool {
	switch v := any(a).(type) {
	case int:
		return v > any(b).(int)
	case int64:
		return v > any(b).(int64)
	case uint64:
		return v > any(b).(uint64)
	case float64:
		return v > any(b).(float64)
	default:
		panic("unsupported type for comparison")
	}
}
