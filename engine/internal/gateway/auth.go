package gateway

import (
	"context"
	"errors"
	"strings"
)

var ErrInvalidToken = errors.New("invalid token")

type AuthManager struct {
	tokens map[string]uint64
}

func NewAuthManager() *AuthManager {
	return &AuthManager{
		tokens: make(map[string]uint64),
	}
}

func (a *AuthManager) ValidateToken(token string) (uint64, error) {
	if userID, exists := a.tokens[token]; exists {
		return userID, nil
	}
	return 0, ErrInvalidToken
}

func (a *AuthManager) GenerateToken(userID uint64) string {
	token := generateToken()
	a.tokens[token] = userID
	return token
}

func (a *AuthManager) RevokeToken(token string) {
	delete(a.tokens, token)
}

func generateToken() string {
	return "token_" + randomString(32)
}

func randomString(n int) string {
	const letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	b := make([]byte, n)
	for i := range b {
		b[i] = letters[i%len(letters)]
	}
	return string(b)
}

func ExtractTokenFromHeader(authHeader string) (string, error) {
	parts := strings.Split(authHeader, " ")
	if len(parts) != 2 || parts[0] != "Bearer" {
		return "", ErrInvalidToken
	}
	return parts[1], nil
}
