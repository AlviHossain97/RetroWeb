import threading
import requests
import json
import time

class AIDriver:
    def __init__(self, model="llama3.2-vision:latest"):
        self.model = model
        self.url = "http://localhost:11434/api/generate"
        self.running = True
        self.active = False
        self.latest_state = None
        self.suggested_action = "CENTER"
        self.last_action_time = 0
        self.last_vision_poll = 0.0
        self.last_vision_action = "CENTER"
        self.last_vision_latency = 0.0
        self.vision_enabled = True
        self.last_state_update = 0.0
        self.last_non_center_action = "CENTER"
        self.action_hold_until = 0.0
        self.lock = threading.Lock()
        
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def update_state(self, state):
        with self.lock:
            self.latest_state = state
            self.last_state_update = time.time()

    def get_action(self):
        with self.lock:
            # Safety: if controller stalls or state is stale, fall back to center.
            now = time.time()
            if now - self.last_action_time > 0.8 or now - self.last_state_update > 0.6:
                return "CENTER"
            return self.suggested_action

    def _lane_centers(self, road_left, road_right):
        width = max(120.0, road_right - road_left)
        lane_count = 4
        lane_w = width / lane_count
        return [road_left + (lane_w * (i + 0.5)) for i in range(lane_count)]

    def _normalize_action(self, text):
        out = (text or "").strip().upper()
        if "BRAKE" in out or "SLOW" in out or "BACK" in out:
            return "BRAKE"
        if "LEFT" in out:
            return "LEFT"
        if "RIGHT" in out:
            return "RIGHT"
        return "CENTER"

    def _heuristic_action(self, state):
        if not isinstance(state, dict):
            return "CENTER"

        player_x = float(state.get("player_x", 0.0))
        player_y = float(state.get("player_y", 0.0))
        player_w = float(state.get("player_w", 50.0))
        road_left = float(state.get("road_left", 130.0))
        road_right = float(state.get("road_right", 670.0))
        enemies = state.get("enemies", [])

        player_center = player_x + (player_w * 0.5)
        lane_centers = self._lane_centers(road_left, road_right)
        candidate_x = [max(road_left, min(c - (player_w * 0.5), road_right - player_w)) for c in lane_centers]
        candidate_x.extend([
            max(road_left, min(player_x + off, road_right - player_w))
            for off in (-110, -70, -35, 0, 35, 70, 110)
        ])

        best_x = player_x
        best_score = -1e9
        current_lane_clearance = 0.0

        for cand_x in candidate_x:
            cand_center = cand_x + (player_w * 0.5)
            off = cand_x - player_x

            # Human-like preference: stable steering, but willing to move for better space.
            score = -abs(off) * 0.028
            clearance_ahead = 0.0
            immediate_danger = 0.0

            for e in enemies:
                ex = float(e.get("x", 0.0))
                ey = float(e.get("y", 0.0))
                ew = float(e.get("w", 50.0))
                enemy_center = ex + (ew * 0.5)

                dy = player_y - ey
                if dy < -20 or dy > 300:
                    continue

                dx = abs(cand_center - enemy_center)
                lateral_buffer = dx - ((player_w * 0.45) + (ew * 0.45))

                if 0 <= dy <= 40 and lateral_buffer < 6:
                    immediate_danger += 260.0
                elif 40 < dy <= 120 and lateral_buffer < 12:
                    immediate_danger += 150.0

                if 0 <= dy <= 240:
                    hazard_strength = (240.0 - dy) / 240.0
                    penalty = max(0.0, (60.0 - lateral_buffer) * (1.5 + hazard_strength * 1.8))
                    score -= penalty
                    clearance_ahead += max(0.0, lateral_buffer) * (1.0 - (dy / 320.0))

            score += clearance_ahead * 0.18
            score -= immediate_danger

            # Prefer lane centers very slightly for smoother human-like driving.
            lane_center_dist = min(abs(cand_center - lc) for lc in lane_centers)
            score -= lane_center_dist * 0.03

            if abs(cand_x - player_x) < 8:
                current_lane_clearance = clearance_ahead - immediate_danger

            if score > best_score:
                best_score = score
                best_x = cand_x

        best_center = best_x + (player_w * 0.5)
        best_lane_center_dist = min(abs(best_center - lc) for lc in lane_centers)

        # Keep stable line unless the better lane is meaningfully safer.
        if abs(best_x - player_x) > 24 and best_lane_center_dist < 26:
            if best_score < (current_lane_clearance + 10.0):
                best_x = player_x

        # Emergency decision: if immediate frontal threat and both sides are poor, brake.
        imminent_block = 0
        for e in enemies:
            ex = float(e.get("x", 0.0))
            ey = float(e.get("y", 0.0))
            ew = float(e.get("w", 50.0))
            eh = float(e.get("h", 100.0))
            enemy_center = ex + (ew * 0.5)
            dy = player_y - ey
            if 0 <= dy <= 85 and abs(player_center - enemy_center) < (player_w * 0.52 + ew * 0.52):
                imminent_block += 1

        if imminent_block >= 1 and abs(best_x - player_x) < 12:
            return "BRAKE"

        delta = best_x - player_x
        action = "CENTER"
        if delta < -6:
            action = "LEFT"
        elif delta > 6:
            action = "RIGHT"

        now = time.time()
        if now < self.action_hold_until:
            return self.suggested_action

        if action in ("LEFT", "RIGHT"):
            self.last_non_center_action = action
            self.action_hold_until = now + 0.08
        else:
            self.action_hold_until = now + 0.03

        return action

    def loop(self):
        print(f"AI Driver initialized with model {self.model}")
        while self.running:
            if not self.active or self.latest_state is None:
                time.sleep(0.1)
                continue
            
            with self.lock:
                state = dict(self.latest_state)

            # Primary realtime controller: deterministic local heuristic.
            local_action = self._heuristic_action(state)
            with self.lock:
                self.suggested_action = local_action
                self.last_action_time = time.time()

            image_data = state.get('image', None)
            now = time.time()

            # Secondary controller: optional vision model assist (slow path).
            if not self.vision_enabled or (not image_data) or (now - self.last_vision_poll < 0.45):
                time.sleep(0.01)
                continue

            self.last_vision_poll = now
            start_time = now

            prompt = """
[ROLE]
You are an Autonomous Vehicle Controller driving a car in a video game.
The image provided is what you see out the windshield.

[OBJECTIVE]
1. Drive safely down the road.
2. Avoid hitting collisions (other cars, obstacles).
3. Stay on the road surface.

[INSTRUCTIONS]
- Analyze the image.
- If a car is directly ahead and left is open, output LEFT.
- If a car is directly ahead and right is open, output RIGHT.
- If a car is directly ahead and neither side is safe, output BRAKE.
- If clear, output CENTER.

[OUTPUT]
Return ONLY one single word: LEFT, RIGHT, BRAKE, or CENTER.
"""
            
            try:
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "images": [image_data],
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 10
                    }
                }
                
                # Vision models are slower, 5s timeout might be tight but ok for now
                response = requests.post(self.url, json=payload, timeout=5)
                if response.status_code == 200:
                    result = response.json().get("response", "")
                    action = self._normalize_action(result)
                    self.last_vision_action = action
                    
                    with self.lock:
                        # Heuristic always remains primary for low-latency control.
                        # Vision can still bias turn direction when local action is undecided.
                        if self.suggested_action == "CENTER" and action in ("LEFT", "RIGHT"):
                            self.suggested_action = action
                        elif self.suggested_action in ("LEFT", "RIGHT") and action == self.suggested_action:
                            # Reinforce consistent decisions.
                            self.action_hold_until = time.time() + 0.1
                        self.last_action_time = time.time()
                        latency = time.time() - start_time
                        self.last_vision_latency = latency
                        print(f"AI Vision Action: {result} -> {action} ({latency:.2f}s)")
                
            except Exception as e:
                # Network/model failures should not disable local heuristic driving.
                self.vision_enabled = False

            # Limit query rate slightly less aggressively for vision since inference is slow anyway
            time.sleep(0.01)

    def stop(self):
        self.running = False
