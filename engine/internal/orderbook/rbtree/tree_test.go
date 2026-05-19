package rbtree

import "testing"

func TestRBTree_Insert(t *testing.T) {
	tree := NewRBTree[int]()

	tree.Insert(5, "five")
	tree.Insert(3, "three")
	tree.Insert(7, "seven")

	if tree.Size() != 3 {
		t.Errorf("expected size 3, got %d", tree.Size())
	}
}

func TestRBTree_Search(t *testing.T) {
	tree := NewRBTree[int]()

	tree.Insert(5, "five")
	tree.Insert(3, "three")
	tree.Insert(7, "seven")

	val := tree.Search(5)
	if val != "five" {
		t.Errorf("expected 'five', got %v", val)
	}

	val = tree.Search(3)
	if val != "three" {
		t.Errorf("expected 'three', got %v", val)
	}

	val = tree.Search(10)
	if val != nil {
		t.Errorf("expected nil, got %v", val)
	}
}

func TestRBTree_Update(t *testing.T) {
	tree := NewRBTree[int]()

	tree.Insert(5, "five")
	tree.Insert(5, "updated")

	val := tree.Search(5)
	if val != "updated" {
		t.Errorf("expected 'updated', got %v", val)
	}

	if tree.Size() != 1 {
		t.Errorf("expected size 1, got %d", tree.Size())
	}
}
