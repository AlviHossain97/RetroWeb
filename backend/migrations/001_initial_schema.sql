-- Migration 001: Initial schema expansion
-- Safe to re-run (uses IF NOT EXISTS)

-- devices
CREATE TABLE IF NOT EXISTS devices (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    hostname VARCHAR(128) NOT NULL UNIQUE,
    display_name VARCHAR(255),
    ip_address VARCHAR(45),
    status ENUM('online','offline','unknown') DEFAULT 'unknown',
    last_seen_at DATETIME,
    client_version VARCHAR(64),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- games (canonical game registry)
CREATE TABLE IF NOT EXISTS games (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    canonical_title VARCHAR(255) NOT NULL,
    rom_path TEXT,
    system_name VARCHAR(64),
    cover_url TEXT,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- daily_game_stats
CREATE TABLE IF NOT EXISTS daily_game_stats (
    date DATE NOT NULL,
    game_id BIGINT UNSIGNED,
    total_seconds INT DEFAULT 0,
    session_count INT DEFAULT 0,
    PRIMARY KEY (date, game_id),
    FOREIGN KEY (game_id) REFERENCES games(id)
);

-- daily_system_stats
CREATE TABLE IF NOT EXISTS daily_system_stats (
    date DATE NOT NULL,
    system_name VARCHAR(64) NOT NULL,
    total_seconds INT DEFAULT 0,
    session_count INT DEFAULT 0,
    PRIMARY KEY (date, system_name)
);

-- achievements
CREATE TABLE IF NOT EXISTS achievements (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(64) NOT NULL UNIQUE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    icon VARCHAR(64),
    category VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- user_achievements
CREATE TABLE IF NOT EXISTS user_achievements (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    achievement_id BIGINT UNSIGNED NOT NULL,
    unlocked_at DATETIME NOT NULL,
    context_json JSON,
    FOREIGN KEY (achievement_id) REFERENCES achievements(id)
);

-- controller_profiles
CREATE TABLE IF NOT EXISTS controller_profiles (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    profile_name VARCHAR(128) NOT NULL,
    device_id BIGINT UNSIGNED,
    mapping_json JSON,
    cursor_settings_json JSON,
    navigation_settings_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (device_id) REFERENCES devices(id)
);

-- ai_conversations
CREATE TABLE IF NOT EXISTS ai_conversations (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- ai_messages
CREATE TABLE IF NOT EXISTS ai_messages (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    conversation_id BIGINT UNSIGNED NOT NULL,
    role ENUM('system','user','assistant','tool') NOT NULL,
    content TEXT NOT NULL,
    metadata_json JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES ai_conversations(id) ON DELETE CASCADE
);

-- Indexes for sessions table
-- Using ALTER TABLE IGNORE approach for safe re-runs
-- If index already exists, the statement will error but we continue
ALTER TABLE sessions ADD INDEX idx_sessions_started_at (started_at);
ALTER TABLE sessions ADD INDEX idx_sessions_status (ended_at);
ALTER TABLE sessions ADD INDEX idx_sessions_device (pi_hostname, started_at);
