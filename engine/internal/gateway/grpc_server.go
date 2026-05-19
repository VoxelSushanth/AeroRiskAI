package gateway

import (
	"context"
	"net"

	"google.golang.org/grpc"
)

type GRPCServer struct {
	server *grpc.Server
	port   string
}

func NewGRPCServer(port string) *GRPCServer {
	return &GRPCServer{
		server: grpc.NewServer(),
		port:   port,
	}
}

func (s *GRPCServer) Start() error {
	lis, err := net.Listen("tcp", ":"+s.port)
	if err != nil {
		return err
	}
	return s.server.Serve(lis)
}

func (s *GRPCServer) Stop() {
	s.server.Stop()
}

func (s *GRPCServer) RegisterService(desc *grpc.ServiceDesc, impl interface{}) {
	s.server.RegisterService(desc, impl)
}
