package gateway

import (
	"context"
	"encoding/json"
	"net/http"
	"sync"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		return true
	},
}

type WSServer struct {
	clients    map[*websocket.Conn]bool
	mu         sync.RWMutex
	broadcast  chan []byte
}

func NewWSServer() *WSServer {
	return &WSServer{
		clients:   make(map[*websocket.Conn]bool),
		broadcast: make(chan []byte, 100),
	}
}

func (s *WSServer) HandleWS(w http.ResponseWriter, r *http.Request) {
	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		http.Error(w, "failed to upgrade", http.StatusBadRequest)
		return
	}

	s.mu.Lock()
	s.clients[conn] = true
	s.mu.Unlock()

	go s.readPump(conn)
	go s.writePump(conn)
}

func (s *WSServer) readPump(conn *websocket.Conn) {
	defer func() {
		s.mu.Lock()
		delete(s.clients, conn)
		s.mu.Unlock()
		conn.Close()
	}()

	for {
		_, message, err := conn.ReadMessage()
		if err != nil {
			break
		}
		// Process message
		_ = message
	}
}

func (s *WSServer) writePump(conn *websocket.Conn) {
	defer func() {
		s.mu.Lock()
		delete(s.clients, conn)
		s.mu.Unlock()
		conn.Close()
	}()

	for {
		select {
		case message := <-s.broadcast:
			conn.WriteMessage(websocket.TextMessage, message)
		}
	}
}

func (s *WSServer) Broadcast(message interface{}) {
	data, _ := json.Marshal(message)
	s.broadcast <- data
}

func (s *WSServer) Start(addr string) error {
	http.HandleFunc("/ws", s.HandleWS)
	return http.ListenAndServe(addr, nil)
}
