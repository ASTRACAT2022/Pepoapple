package runtime

import (
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
)

type Manager struct {
	ConfigPath string
	BackupPath string
}

func NewManager(configPath, backupPath string) *Manager {
	return &Manager{ConfigPath: configPath, BackupPath: backupPath}
}

func (m *Manager) Validate(cfg map[string]interface{}) error {
	if _, ok := cfg["inbounds"]; !ok {
		return fmt.Errorf("config validation failed: missing inbounds")
	}
	return nil
}

func (m *Manager) Apply(cfg map[string]interface{}) error {
	if err := m.backupCurrent(); err != nil {
		return err
	}
	if err := writeJSON(m.ConfigPath, cfg); err != nil {
		_ = m.Rollback()
		return err
	}
	if err := m.reloadServices(); err != nil {
		_ = m.Rollback()
		return err
	}
	return nil
}

func (m *Manager) Rollback() error {
	raw, err := os.ReadFile(m.BackupPath)
	if err != nil {
		return err
	}
	if err := os.WriteFile(m.ConfigPath, raw, 0o600); err != nil {
		return err
	}
	return m.reloadServices()
}

func (m *Manager) backupCurrent() error {
	raw, err := os.ReadFile(m.ConfigPath)
	if err != nil {
		if os.IsNotExist(err) {
			return nil
		}
		return err
	}
	return os.WriteFile(m.BackupPath, raw, 0o600)
}

func (m *Manager) reloadServices() error {
	// Both services are best-effort; deployments can disable one of them.
	commands := [][]string{
		{"systemctl", "restart", "awg2"},
		{"systemctl", "restart", "sing-box"},
	}
	for _, args := range commands {
		cmd := exec.Command(args[0], args[1:]...)
		if err := cmd.Run(); err != nil {
			// Ignore service restarts when service not installed.
			continue
		}
	}
	return nil
}

func writeJSON(path string, payload map[string]interface{}) error {
	raw, err := json.MarshalIndent(payload, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, raw, 0o600)
}
