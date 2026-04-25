import sys
sys.path.append(r"C:\Users\alvi9\MyWork\Testing")
from cars import CAR_ROSTER, CAR_ORDER, CAR_UNLOCK_THRESHOLDS
from roads import ROAD_ROSTER, ROAD_ORDER
from modes import MODE_ROSTER, MODE_ORDER

old_spr = {
    "Felucia": (0, 2), "Suprex": (8, 2), "Corveda": (5, 2), "Aurion": (3, 8),
    "Lotrix": (10, 5), "Merren": (4, 8), "Astor": (9, 3), "P11": (11, 8),
    "Vyrex": (12, 4), "Marlon": (2, 6), "Lumbra": (1, 5), "Zondra": (13, 8),
    "CXR": (7, 8), "Vexa": (6, 4)
}

with open("dump.txt", "w") as f:
    f.write("const CarDef car_defs[NUM_CARS] = {\n")
    f.write("  // name       spr col unlock   spd  acc  hdl  brk  fuel  drag   grip   wgt  bst\n")
    for key in CAR_ORDER:
        car = CAR_ROSTER[key]
        spr, col = old_spr[key]
        unl = CAR_UNLOCK_THRESHOLDS[key]
        f.write(f'  {{"{key[:11]}", {spr:>2}, {col:>2}, {unl:<6}, {car["top_speed"]:>3}, {car["accel"]:>2}, {car["handling"]:>2}, {car["braking"]:>2}, {int(car["fuel_eff"]*100):>3}, {car["drag"]:.2f}f, {car["grip"]:.2f}f, {car["weight"]:>2}, {int(car["boost_gain"]*100):>3}}},\n')
    f.write("};\n\n")

    f.write("const RoadStats road_stats[NUM_ROADS] = {\n")
    f.write("  //  name              fric traf risk spawn  pL  pR  rew  drn  spd\n")
    for key in ROAD_ORDER:
        road = ROAD_ROSTER[key]
        rname = road.get('display_name', key.split('.')[0])
        # Convert floats to pct where possible
        f.write(f'  {{"{rname[:15]}", 100, 50, {int(road.get("risk_mult", 1.0)*10)}, {road.get("spawn_threshold_mult", 1.0)}f, 48, 192, {int(road.get("reward_mult", 1.0)*100)}, {int(road.get("fuel_drain_mult", 1.0)*100)}, {int(100)} }},\n')
    f.write("};\n\n")

    f.write("const ModeRules mode_rules[NUM_MODES] = {\n")
    f.write("  // short  risk% spawn% fuel 1h time itm nit foc act pad\n")
    for key in MODE_ORDER:
        mode = MODE_ROSTER[key]
        s = mode["short"]
        o = mode
        # Derive flags based on Python rules:
        r_pct = int(o.get("risk_multiplier", 1.0) * 100)
        s_pct = int(o.get("spawn_rate_mult", 1.0) * 100)
        fuel_d = 0 if o.get("fuel_drain_mult", 1.0) == 0.0 else 1
        oneh = 1 if o.get("one_hit_kill", False) else 0
        timer = 1 if o.get("time_limit") is not None else 0
        items = 1 if o.get("collectibles", True) else 0
        nitro = 1 if o.get("nitro_spawn_mult", 1.0) > 0.0 else 0
        focus = 1 if key == "ZEN" else 0
        act = 0 if o.get("score_formula") == "base_only" else 1
        f.write(f'  {{"{s[:5]}", {r_pct:>3}, {s_pct:>4},   {fuel_d},  {oneh},    {timer},   {items},   {nitro},   {focus},   {act},   0}},\n')
    f.write("};\n\n")

    f.write("static const char *mode_names[] = {\n")
    modes = [f'  "{MODE_ROSTER[k]["name"]}"' for k in MODE_ORDER]
    f.write(", ".join(modes))
    f.write("\n};\n")
