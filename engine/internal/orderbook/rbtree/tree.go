package rbtree

type Color int

const (
	Red Color = iota
	Black
)

type Node[T comparable] struct {
	key    T
	value  interface{}
	color  Color
	left   *Node[T]
	right  *Node[T]
	parent *Node[T]
}

type RBTree[T comparable] struct {
	root *Node[T]
	size int
}

func NewRBTree[T comparable]() *RBTree[T] {
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
		if key < current.key {
			current = current.left
		} else if key > current.key {
			current = current.right
		} else {
			current.value = value
			return
		}
	}

	node.parent = parent
	if parent == nil {
		t.root = node
	} else if key < parent.key {
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
	t.root.color = Black
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
		if key < current.key {
			current = current.left
		} else if key > current.key {
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
