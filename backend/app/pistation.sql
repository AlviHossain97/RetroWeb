-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: localhost
-- Generation Time: Apr 18, 2026 at 09:31 PM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `pistation`
--

-- --------------------------------------------------------

--
-- Table structure for table `achievements`
--

CREATE TABLE `achievements` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `code` varchar(64) NOT NULL,
  `title` varchar(255) NOT NULL,
  `description` text DEFAULT NULL,
  `icon` varchar(64) DEFAULT NULL,
  `category` varchar(64) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `achievements`
--

INSERT INTO `achievements` (`id`, `code`, `title`, `description`, `icon`, `category`, `created_at`) VALUES
(1, 'first_session', 'First Session', 'Start your first gaming session', '🎮', 'getting_started', '2026-03-13 15:30:05'),
(2, 'first_hour', 'First Hour', 'Play for a cumulative hour', '⏰', 'playtime', '2026-03-13 15:30:05'),
(3, 'ten_hours', 'Ten Hours', 'Play for ten cumulative hours', '🔥', 'playtime', '2026-03-13 15:30:05'),
(4, 'marathon', 'Marathon Session', 'Play a single session for over 2 hours', '🏃', 'playtime', '2026-03-13 15:30:05'),
(5, 'five_systems', 'System Explorer', 'Play games on 5 different systems', '🌍', 'exploration', '2026-03-13 15:30:05'),
(6, 'weekend_warrior', 'Weekend Warrior', 'Play on both Saturday and Sunday', '⚔️', 'streaks', '2026-03-13 15:30:05'),
(7, 'night_owl', 'Night Owl', 'Start a session after midnight', '🦉', 'misc', '2026-03-13 15:30:05'),
(8, 'three_day_streak', 'Three-Day Streak', 'Play on three consecutive days', '🔗', 'streaks', '2026-03-13 15:30:05'),
(9, 'seven_day_streak', 'Seven-Day Streak', 'Play every day for a week', '💎', 'streaks', '2026-03-13 15:30:05'),
(10, 'ai_first_question', 'AI Explorer', 'Ask the AI assistant your first question', '🤖', 'ai', '2026-03-13 15:30:05'),
(11, 'stats_explorer', 'Stats Explorer', 'Visit the stats page', '📊', 'navigation', '2026-03-13 15:30:05'),
(12, 'retro_explorer', 'Retro Explorer', 'Play a game from each decade (80s, 90s, 00s)', '🕹️', 'exploration', '2026-03-13 15:30:05'),
(13, 'controller_master', 'Controller Master', 'Configure a custom controller profile', '🎛️', 'controller', '2026-03-13 15:30:05'),
(14, 'device_loyalist', 'Device Loyalist', 'Play 50 sessions on the same device', '🏠', 'dedication', '2026-03-13 15:30:05');

-- --------------------------------------------------------

--
-- Table structure for table `ai_conversations`
--

CREATE TABLE `ai_conversations` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(255) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `ai_messages`
--

CREATE TABLE `ai_messages` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `conversation_id` bigint(20) UNSIGNED NOT NULL,
  `role` enum('system','user','assistant','tool') NOT NULL,
  `content` text NOT NULL,
  `metadata_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`metadata_json`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `controller_profiles`
--

CREATE TABLE `controller_profiles` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `profile_name` varchar(128) NOT NULL,
  `device_id` bigint(20) UNSIGNED DEFAULT NULL,
  `mapping_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`mapping_json`)),
  `cursor_settings_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`cursor_settings_json`)),
  `navigation_settings_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`navigation_settings_json`)),
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `daily_game_stats`
--

CREATE TABLE `daily_game_stats` (
  `date` date NOT NULL,
  `game_id` bigint(20) UNSIGNED NOT NULL,
  `total_seconds` int(11) DEFAULT 0,
  `session_count` int(11) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `daily_system_stats`
--

CREATE TABLE `daily_system_stats` (
  `date` date NOT NULL,
  `system_name` varchar(64) NOT NULL,
  `total_seconds` int(11) DEFAULT 0,
  `session_count` int(11) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `devices`
--

CREATE TABLE `devices` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `hostname` varchar(128) NOT NULL,
  `display_name` varchar(255) DEFAULT NULL,
  `ip_address` varchar(45) DEFAULT NULL,
  `status` enum('online','offline','unknown') DEFAULT 'unknown',
  `last_seen_at` datetime DEFAULT NULL,
  `client_version` varchar(64) DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `games`
--

CREATE TABLE `games` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `canonical_title` varchar(255) NOT NULL,
  `rom_path` text DEFAULT NULL,
  `system_name` varchar(64) DEFAULT NULL,
  `cover_url` text DEFAULT NULL,
  `description` text DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `updated_at` timestamp NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- --------------------------------------------------------

--
-- Table structure for table `sessions`
--

CREATE TABLE `sessions` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `pi_hostname` varchar(128) NOT NULL,
  `rom_path` text NOT NULL,
  `system_name` varchar(64) DEFAULT NULL,
  `emulator` varchar(64) DEFAULT NULL,
  `core` varchar(64) DEFAULT NULL,
  `started_at` datetime NOT NULL,
  `ended_at` datetime DEFAULT NULL,
  `duration_seconds` int(11) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Dumping data for table `sessions`
--

INSERT INTO `sessions` (`id`, `pi_hostname`, `rom_path`, `system_name`, `emulator`, `core`, `started_at`, `ended_at`, `duration_seconds`, `created_at`) VALUES
(6, 'normalize-test', '/home/pi/RetroPie/roms/nes/Super Mario Bros. 3 (Europe).zip', 'nes', 'retroarch', 'fceumm', '2026-02-20 14:00:00', '2026-03-02 12:34:54', 858894, '2026-02-20 14:00:08'),
(7, 'retropie', '/home/pi/RetroPie/roms/gb/Pokemon - Red Version (USA, Europe) (SGB Enhanced).zip', 'gb', 'lr-gambatte', 'gambatte', '2026-03-06 15:51:05', '2026-03-06 16:09:31', 1106, '2026-03-06 15:51:05'),
(8, 'retropie', '/home/pi/RetroPie/roms/gb/Pokemon - Red Version (USA, Europe) (SGB Enhanced).zip', 'gb', 'lr-gambatte', 'gambatte', '2026-03-06 15:52:27', '2026-03-06 15:56:24', 237, '2026-03-06 15:52:27'),
(9, 'retropie', '/home/pi/RetroPie/roms/gb/Pokemon - Red Version (USA, Europe) (SGB Enhanced).zip', 'gb', 'lr-gambatte', 'gambatte', '2026-03-06 15:56:50', '2026-03-06 16:14:09', 1039, '2026-03-06 15:56:57'),
(11, 'retropie', '/home/pi/RetroPie/roms/gba/RedRacer_Phys.gba', 'gba', 'lr-mgba', 'mgba', '2026-03-18 13:00:27', '2026-03-18 13:01:35', 67, '2026-03-18 13:00:28'),
(12, 'retropie', '/home/pi/RetroPie/roms/gba/RedRacer_Phys.gba', 'gba', 'lr-mgba', 'mgba', '2026-03-18 13:13:41', '2026-03-18 13:15:50', 128, '2026-03-18 13:13:42'),
(13, 'retropie', '/home/pi/RetroPie/roms/gb/Pokemon - Red Version (USA, Europe) (SGB Enhanced).zip', 'gb', 'lr-gambatte', 'gambatte', '2026-03-18 13:16:31', '2026-03-18 13:17:22', 50, '2026-03-18 13:16:32'),
(14, 'retropie', '/home/pi/RetroPie/roms/gba/RedRacer_Phys.gba', 'gba', 'lr-mgba', 'mgba', '2026-03-18 13:17:29', '2026-03-18 13:19:47', 137, '2026-03-18 13:17:29'),
(15, 'retropie', '/home/pi/RetroPie/roms/gba/RedRacer_Phys.gba', 'gba', 'lr-mgba', 'mgba', '2026-03-18 13:20:27', '2026-03-18 14:05:33', 2706, '2026-03-18 13:20:28'),
(16, 'retropie', '/home/pi/RetroPie/roms/gba/RedRacer_Phys.gba', 'gba', 'lr-mgba', 'mgba', '2026-03-18 14:05:33', '2026-03-18 14:09:48', 255, '2026-03-18 14:05:33'),
(17, 'retropie', '/home/pi/RetroPie/roms/gba/RedRacer_Phys.gba', 'gba', 'lr-mgba', 'mgba', '2026-03-18 14:14:36', '2026-03-18 14:17:13', 156, '2026-03-18 14:14:40'),
(18, 'retropie', '/home/pi/RetroPie/roms/gb/Pokemon - Red Version (USA, Europe) (SGB Enhanced).zip', 'gb', 'lr-gambatte', 'gambatte', '2026-03-20 13:05:27', '2026-03-20 13:08:31', 184, '2026-03-20 13:05:29'),
(19, 'retropie', '/home/pi/RetroPie/roms/gb/Pokemon - Red Version (USA, Europe) (SGB Enhanced).zip', 'gb', 'lr-gambatte', 'gambatte', '2026-03-20 13:08:31', '2026-03-20 13:09:38', 66, '2026-03-20 13:08:33'),
(20, 'retropie', '/home/pi/RetroPie/roms/gba/RedRacer_Phys.gba', 'gba', 'lr-mgba', 'mgba', '2026-03-20 13:12:29', '2026-03-20 13:17:48', 318, '2026-03-20 13:12:30'),
(21, 'retropie', '/home/pi/RetroPie/roms/gb/Pokemon - Red Version (USA, Europe) (SGB Enhanced).zip', 'gb', 'lr-gambatte', 'gambatte', '2026-03-20 13:24:22', '2026-03-20 13:25:47', 85, '2026-03-20 13:24:25');

-- --------------------------------------------------------

--
-- Table structure for table `user_achievements`
--

CREATE TABLE `user_achievements` (
  `id` bigint(20) UNSIGNED NOT NULL,
  `achievement_id` bigint(20) UNSIGNED NOT NULL,
  `unlocked_at` datetime NOT NULL,
  `context_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`context_json`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `achievements`
--
ALTER TABLE `achievements`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `code` (`code`);

--
-- Indexes for table `ai_conversations`
--
ALTER TABLE `ai_conversations`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `ai_messages`
--
ALTER TABLE `ai_messages`
  ADD PRIMARY KEY (`id`),
  ADD KEY `conversation_id` (`conversation_id`);

--
-- Indexes for table `controller_profiles`
--
ALTER TABLE `controller_profiles`
  ADD PRIMARY KEY (`id`),
  ADD KEY `device_id` (`device_id`);

--
-- Indexes for table `daily_game_stats`
--
ALTER TABLE `daily_game_stats`
  ADD PRIMARY KEY (`date`,`game_id`),
  ADD KEY `game_id` (`game_id`);

--
-- Indexes for table `daily_system_stats`
--
ALTER TABLE `daily_system_stats`
  ADD PRIMARY KEY (`date`,`system_name`);

--
-- Indexes for table `devices`
--
ALTER TABLE `devices`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `hostname` (`hostname`);

--
-- Indexes for table `games`
--
ALTER TABLE `games`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `sessions`
--
ALTER TABLE `sessions`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_sessions_rom` (`rom_path`(255)),
  ADD KEY `idx_sessions_started` (`started_at`),
  ADD KEY `idx_sessions_started_at` (`started_at`),
  ADD KEY `idx_sessions_status` (`ended_at`),
  ADD KEY `idx_sessions_device` (`pi_hostname`,`started_at`);

--
-- Indexes for table `user_achievements`
--
ALTER TABLE `user_achievements`
  ADD PRIMARY KEY (`id`),
  ADD KEY `achievement_id` (`achievement_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `achievements`
--
ALTER TABLE `achievements`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=15;

--
-- AUTO_INCREMENT for table `ai_conversations`
--
ALTER TABLE `ai_conversations`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `ai_messages`
--
ALTER TABLE `ai_messages`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `controller_profiles`
--
ALTER TABLE `controller_profiles`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `devices`
--
ALTER TABLE `devices`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `games`
--
ALTER TABLE `games`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `sessions`
--
ALTER TABLE `sessions`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=22;

--
-- AUTO_INCREMENT for table `user_achievements`
--
ALTER TABLE `user_achievements`
  MODIFY `id` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `ai_messages`
--
ALTER TABLE `ai_messages`
  ADD CONSTRAINT `ai_messages_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `ai_conversations` (`id`) ON DELETE CASCADE;

--
-- Constraints for table `controller_profiles`
--
ALTER TABLE `controller_profiles`
  ADD CONSTRAINT `controller_profiles_ibfk_1` FOREIGN KEY (`device_id`) REFERENCES `devices` (`id`);

--
-- Constraints for table `daily_game_stats`
--
ALTER TABLE `daily_game_stats`
  ADD CONSTRAINT `daily_game_stats_ibfk_1` FOREIGN KEY (`game_id`) REFERENCES `games` (`id`);

--
-- Constraints for table `user_achievements`
--
ALTER TABLE `user_achievements`
  ADD CONSTRAINT `user_achievements_ibfk_1` FOREIGN KEY (`achievement_id`) REFERENCES `achievements` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
