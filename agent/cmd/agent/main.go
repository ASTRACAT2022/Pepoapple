package main

import (
	"log"
	"time"

	"pepoapple/agent/internal/api"
	"pepoapple/agent/internal/config"
	"pepoapple/agent/internal/runtime"
)

func main() {
	cfg := config.Load()
	client := api.NewClient(cfg.APIBaseURL)
	manager := runtime.NewManager(cfg.ConfigPath, cfg.BackupPath)

	log.Printf("agent started, backend=%s", cfg.APIBaseURL)
	ticker := time.NewTicker(cfg.HeartbeatInterval)
	defer ticker.Stop()

	for {
		if err := client.Heartbeat(cfg.NodeToken, "awg2-unknown", "singbox-unknown"); err != nil {
			log.Printf("heartbeat error: %v", err)
		}

		desired, err := client.DesiredConfig(cfg.NodeToken)
		if err != nil {
			log.Printf("desired-config error: %v", err)
		} else {
			if err := manager.Validate(desired.DesiredConfig); err != nil {
				_ = client.ApplyResult(cfg.NodeToken, desired.DesiredConfigRevision, "failed", map[string]interface{}{"error": err.Error()})
			} else if err := manager.Apply(desired.DesiredConfig); err != nil {
				_ = client.ApplyResult(cfg.NodeToken, desired.DesiredConfigRevision, "failed", map[string]interface{}{"error": err.Error()})
			} else {
				_ = client.ApplyResult(cfg.NodeToken, desired.DesiredConfigRevision, "success", map[string]interface{}{})
			}
		}

		<-ticker.C
	}
}
