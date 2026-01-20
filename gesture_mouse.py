import time
import math

import cv2
import pyautogui
import mediapipe as mp

# -----------------------------
# Config (v6.1)
# -----------------------------
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0

CAM_INDEX = 0
CAM_W, CAM_H = 1280, 720

CONTROL_MARGIN = 0.12

SMOOTHING = 0.90
DEADZONE = 4
MAX_STEP = 70

# Pinch / click / drag
PINCH_PIXELS = 55
DRAG_HOLD_TIME = 0.25
CLICK_COOLDOWN = 0.15

# Scroll
SCROLL_SENSITIVITY = 2600
SCROLL_DEADZONE = 0.003
SCROLL_CLAMP = 180

# Adaptive speed
GAIN_MIN = 0.45
GAIN_MAX = 1.85
VEL_LOW = 0.0025
VEL_HIGH = 0.0300

EDGE_SLOW_ZONE_PX = 140
EDGE_SLOW_GAIN = 0.55
STEADY_VEL_THRESH = 0.0020
STEADY_GAIN = 0.55

# Intent detection
INTENT_STABLE_FRAMES = 4
INTENT_SWITCH_MARGIN = 0.12
ACTION_CONF_THRESH = 0.50   # used for MOVE / SCROLL / DRAG only


# -----------------------------
# Setup
# -----------------------------
screen_w, screen_h = pyautogui.size()

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils

hands = mp_hands.Hands(
    max_num_hands=1,
    model_complexity=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

cap = cv2.VideoCapture(CAM_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM_H)

smooth_x, smooth_y = screen_w / 2, screen_h / 2

paused = False
dragging = False

scroll_prev_y = None
scroll_accum = 0.0

pinch_prev = False
pinch_start_time = None
did_drag_this_pinch = False
last_click_time = 0.0

prev_time = time.time()

prev_idx_norm = None
prev_idx_time = None
vel_smooth = 0.0

current_intent = "IDLE"
current_conf = 0.0
intent_candidate = None
intent_candidate_frames = 0


# -----------------------------
# Helpers
# -----------------------------
def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def clamp01(v):
    return clamp(v, 0.0, 1.0)

def distance(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

def finger_up(lms, tip_id, pip_id):
    return lms[tip_id].y < lms[pip_id].y

def apply_control_margin(nx, ny, margin):
    margin = clamp(margin, 0.0, 0.45)
    denom = 1.0 - 2.0 * margin
    if denom <= 1e-6:
        return clamp01(nx), clamp01(ny)
    return clamp01((nx - margin) / denom), clamp01((ny - margin) / denom)

def map_velocity_to_gain(v):
    if v <= VEL_LOW:
        return GAIN_MIN
    if v >= VEL_HIGH:
        return GAIN_MAX
    t = (v - VEL_LOW) / (VEL_HIGH - VEL_LOW)
    t = t * t * (3 - 2 * t)
    return GAIN_MIN + t * (GAIN_MAX - GAIN_MIN)


# -----------------------------
# Main loop
# -----------------------------
while True:
    ok, frame = cap.read()
    if not ok:
        break

    frame = cv2.flip(frame, 1)
    fh, fw = frame.shape[:2]

    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(rgb)

    pinch_dist = 999.0
    scores = {k: 0.0 for k in ["MOVE", "SCROLL", "PINCH", "DRAG", "CLICK", "IDLE"]}

    if result.multi_hand_landmarks:
        hand = result.multi_hand_landmarks[0]
        lms = hand.landmark
        mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)

        index_up = finger_up(lms, 8, 6)
        middle_up = finger_up(lms, 12, 10)

        ix, iy = int(lms[8].x * fw), int(lms[8].y * fh)
        tx, ty = int(lms[4].x * fw), int(lms[4].y * fh)

        pinch_dist = distance((ix, iy), (tx, ty))
        pinch = pinch_dist < PINCH_PIXELS

        now = time.time()

        # -------- velocity --------
        idx_norm = (lms[8].x, lms[8].y)
        if prev_idx_norm is None:
            prev_idx_norm = idx_norm
            prev_idx_time = now

        dt = max(1e-6, now - prev_idx_time)
        vx = (idx_norm[0] - prev_idx_norm[0]) / dt
        vy = (idx_norm[1] - prev_idx_norm[1]) / dt
        vel = math.hypot(vx, vy)
        vel_smooth = 0.85 * vel_smooth + 0.15 * vel

        prev_idx_norm = idx_norm
        prev_idx_time = now

        gain = map_velocity_to_gain(vel_smooth)

        if vel_smooth < STEADY_VEL_THRESH:
            gain *= STEADY_GAIN

        cx, cy = pyautogui.position()
        if cx < EDGE_SLOW_ZONE_PX or cx > screen_w - EDGE_SLOW_ZONE_PX:
            gain *= EDGE_SLOW_GAIN
        if cy < EDGE_SLOW_ZONE_PX or cy > screen_h - EDGE_SLOW_ZONE_PX:
            gain *= EDGE_SLOW_GAIN

        gain = clamp(gain, 0.25, 2.5)

        # -------- intent scores --------
        scroll_mode = index_up and middle_up
        move_mode = index_up and not scroll_mode

        scores["MOVE"] = 0.9 if move_mode else 0.0
        scores["SCROLL"] = 1.0 if scroll_mode else 0.0
        scores["PINCH"] = 1.0 if pinch else 0.0
        scores["DRAG"] = 1.0 if dragging else 0.0
        scores["IDLE"] = 0.35 if not (move_mode or scroll_mode or pinch or dragging) else 0.0

        # -------- pause --------
        if paused:
            if dragging:
                pyautogui.mouseUp()
                dragging = False
            scroll_prev_y = None
            scroll_accum = 0.0
            pinch_prev = pinch
            pinch_start_time = None
            did_drag_this_pinch = False

        else:
            # -------- pinch timing --------
            pinch_start = pinch and not pinch_prev
            pinch_end = not pinch and pinch_prev

            if pinch_start:
                pinch_start_time = now
                did_drag_this_pinch = False

            if pinch and not dragging and pinch_start_time is not None:
                if (now - pinch_start_time) >= DRAG_HOLD_TIME:
                    pyautogui.mouseDown()
                    dragging = True
                    did_drag_this_pinch = True

            if pinch_end:
                if dragging:
                    pyautogui.mouseUp()
                    dragging = False
                else:
                    # CLICK: no confidence gating
                    if pinch_start_time and (now - pinch_start_time) < DRAG_HOLD_TIME:
                        if (now - last_click_time) > CLICK_COOLDOWN:
                            pyautogui.click()
                            last_click_time = now
                            scores["CLICK"] = 1.0

                pinch_start_time = None
                did_drag_this_pinch = False

            pinch_prev = pinch

            # -------- scroll --------
            if scroll_mode and scores["SCROLL"] >= ACTION_CONF_THRESH:
                palm_y = (lms[0].y + lms[9].y) / 2
                if scroll_prev_y is None:
                    scroll_prev_y = palm_y
                dy = palm_y - scroll_prev_y
                scroll_prev_y = palm_y

                if abs(dy) > SCROLL_DEADZONE:
                    scroll_accum += -dy * SCROLL_SENSITIVITY

                amt = int(scroll_accum)
                if amt:
                    amt = clamp(amt, -SCROLL_CLAMP, SCROLL_CLAMP)
                    pyautogui.scroll(amt)
                    scroll_accum -= amt
            else:
                scroll_prev_y = None
                scroll_accum = 0.0

            # -------- movement --------
            should_move = (move_mode and scores["MOVE"] >= ACTION_CONF_THRESH) or dragging
            if should_move:
                nx, ny = apply_control_margin(lms[8].x, lms[8].y, CONTROL_MARGIN)
                target_x = nx * screen_w
                target_y = ny * screen_h

                dx = (target_x - smooth_x) * gain
                dy = (target_y - smooth_y) * gain

                smooth_x += (1 - SMOOTHING) * dx
                smooth_y += (1 - SMOOTHING) * dy

                cx, cy = pyautogui.position()
                step = max(abs(smooth_x - cx), abs(smooth_y - cy))
                if step > MAX_STEP:
                    s = MAX_STEP / step
                    smooth_x = cx + (smooth_x - cx) * s
                    smooth_y = cy + (smooth_y - cy) * s

                if abs(smooth_x - cx) > DEADZONE or abs(smooth_y - cy) > DEADZONE:
                    pyautogui.moveTo(smooth_x, smooth_y)

        cv2.circle(frame, (ix, iy), 7, (255, 255, 255), -1)
        cv2.circle(frame, (tx, ty), 7, (255, 255, 255), -1)
        cv2.line(frame, (ix, iy), (tx, ty), (255, 255, 255), 2)

    # -------- intent selection --------
    if paused:
        best_intent, best_conf = "PAUSED", 1.0
    else:
        best_intent, best_conf = max(scores.items(), key=lambda kv: kv[1])

    # FPS
    fps = 1.0 / max(1e-6, time.time() - prev_time)
    prev_time = time.time()

    cv2.putText(frame, f"Intent: {best_intent}", (12, 32),
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2)
    cv2.putText(frame, f"FPS: {fps:.1f}", (12, 64),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (220, 220, 220), 2)

    cv2.imshow("Gesture Mouse Control (v6.1)", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        break
    elif key == 32:
        paused = not paused
        if paused and dragging:
            pyautogui.mouseUp()
            dragging = False

cap.release()
cv2.destroyAllWindows()
