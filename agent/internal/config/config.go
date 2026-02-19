package config

import (
	"os"
	"strconv"
	"time"
)

type Config struct {
	APIBaseURL        string
	NodeToken         string
	HeartbeatInterval time.Duration
	DesiredPath       string
	ConfigPath        string
	BackupPath        string
}

func Load() Config {
	interval := 15
	if raw := os.Getenv("AGENT_HEARTBEAT_INTERVAL_SEC"); raw != "" {
		if parsed, err := strconv.Atoi(raw); err == nil && parsed > 0 {
			interval = parsed
		}
	}

	return Config{
		APIBaseURL:        getenv("AGENT_API_BASE_URL", "http://127.0.0.1:8080"),
		NodeToken:         getenv("AGENT_NODE_TOKEN", "change-me"),
		HeartbeatInterval: time.Duration(interval) * time.Second,
		DesiredPath:       getenv("AGENT_DESIRED_PATH", "/var/lib/pepoapple/desired.json"),
		ConfigPath:        getenv("AGENT_CONFIG_PATH", "/etc/pepoapple/runtime.json"),
		BackupPath:        getenv("AGENT_BACKUP_PATH", "/var/lib/pepoapple/runtime.backup.json"),
	}
}

func getenv(key, fallback string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return fallback
}
