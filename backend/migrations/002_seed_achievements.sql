-- Migration 002: Seed achievement definitions
INSERT IGNORE INTO achievements (code, title, description, icon, category) VALUES
('first_session', 'First Session', 'Start your first gaming session', '🎮', 'getting_started'),
('first_hour', 'First Hour', 'Play for a cumulative hour', '⏰', 'playtime'),
('ten_hours', 'Ten Hours', 'Play for ten cumulative hours', '🔥', 'playtime'),
('marathon', 'Marathon Session', 'Play a single session for over 2 hours', '🏃', 'playtime'),
('five_systems', 'System Explorer', 'Play games on 5 different systems', '🌍', 'exploration'),
('weekend_warrior', 'Weekend Warrior', 'Play on both Saturday and Sunday', '⚔️', 'streaks'),
('night_owl', 'Night Owl', 'Start a session after midnight', '🦉', 'misc'),
('three_day_streak', 'Three-Day Streak', 'Play on three consecutive days', '🔗', 'streaks'),
('seven_day_streak', 'Seven-Day Streak', 'Play every day for a week', '💎', 'streaks'),
('ai_first_question', 'AI Explorer', 'Ask the AI assistant your first question', '🤖', 'ai'),
('stats_explorer', 'Stats Explorer', 'Visit the stats page', '📊', 'navigation'),
('retro_explorer', 'Retro Explorer', 'Play a game from each decade (80s, 90s, 00s)', '🕹️', 'exploration'),
('controller_master', 'Controller Master', 'Configure a custom controller profile', '🎛️', 'controller'),
('device_loyalist', 'Device Loyalist', 'Play 50 sessions on the same device', '🏠', 'dedication');
