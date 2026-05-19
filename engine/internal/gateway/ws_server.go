package gateway

import (
	"encoding/json"
	"net/http"
	"sync"

	"github.com/aerorisk/engine/internal/publisher"
	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
CheckOrigin: func(r *http.Request) bool {
return true
},
}

type WSClient struct {
conn *websocket.Conn
send chan []byte
}

type WSServer struct {
clients   map[*WSClient]bool
mu        sync.RWMutex
broadcast chan []byte
publisher *publisher.KafkaPublisher
addr      string
stopCh    chan struct{}
}

func NewWSServer(addr string, pub *publisher.KafkaPublisher) *WSServer {
return &WSServer{
clients:   make(map[*WSClient]bool),
broadcast: make(chan []byte, 256),
publisher: pub,
addr:      addr,
stopCh:    make(chan struct{}),
}
}

func (s *WSServer) HandleWS(w http.ResponseWriter, r *http.Request) {
conn, err := upgrader.Upgrade(w, r, nil)
if err != nil {
http.Error(w, "failed to upgrade", http.StatusBadRequest)
return
}

client := &WSClient{
conn: conn,
send: make(chan []byte, 256),
}

s.mu.Lock()
s.clients[client] = true
s.mu.Unlock()

go s.readPump(client)
go s.writePump(client)
}

func (s *WSServer) readPump(client *WSClient) {
defer func() {
s.mu.Lock()
delete(s.clients, client)
s.mu.Unlock()
close(client.send)
client.conn.Close()
}()

for {
select {
case <-s.stopCh:
return
default:
_, message, err := client.conn.ReadMessage()
if err != nil {
return
}
// Process incoming message - route to publisher
if s.publisher != nil {
// Parse and publish to Kafka
_ = message
}
}
}
}

func (s *WSServer) writePump(client *WSClient) {
defer func() {
s.mu.Lock()
delete(s.clients, client)
s.mu.Unlock()
client.conn.Close()
}()

for {
select {
case <-s.stopCh:
return
case message, ok := <-client.send:
if !ok {
return
}
if err := client.conn.WriteMessage(websocket.TextMessage, message); err != nil {
return
}
}
}
}

func (s *WSServer) Broadcast(message interface{}) {
data, err := json.Marshal(message)
if err != nil {
return
}
select {
case s.broadcast <- data:
default:
// Drop message if broadcast channel is full
}
}

func (s *WSServer) Start() error {
// Start broadcast distributor
go func() {
for {
select {
case <-s.stopCh:
return
case message := <-s.broadcast:
s.mu.RLock()
for client := range s.clients {
select {
case client.send <- message:
default:
// Client buffer full, skip
}
}
s.mu.RUnlock()
}
}
}()

http.HandleFunc("/ws", s.HandleWS)
http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
w.WriteHeader(http.StatusOK)
w.Write([]byte("ok"))
})
return http.ListenAndServe(s.addr, nil)
}

func (s *WSServer) Stop() {
close(s.stopCh)
s.mu.Lock()
defer s.mu.Unlock()
for client := range s.clients {
client.conn.Close()
}
}
