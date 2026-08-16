import os
import sys
import time
import urllib.request
import cv2
import mediapipe as mp
import pyautogui

pyautogui.FAILSAFE = False

MODEL_PATH = "face_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"

def download_model_if_needed():
    if not os.path.exists(MODEL_PATH):
        print(f"Downloading MediaPipe Face Landmarker model to '{MODEL_PATH}'...")
        try:
            urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
            print("Model downloaded successfully.")
        except Exception as e:
            print(f"Error downloading model file: {e}")
            sys.exit(1)

class EyeTrackerEngine:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.cam = None
        self.screen_w, self.screen_h = pyautogui.size()

        self.curr_screen_x = self.screen_w // 2
        self.curr_screen_y = self.screen_h // 2

        self.last_blink_time = 0
        self.start_time = time.time()

        # Check MediaPipe API availability
        self.has_solutions = hasattr(mp, "solutions") and hasattr(getattr(mp, "solutions", None), "face_mesh")

        if not self.has_solutions:
            download_model_if_needed()
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=vision.RunningMode.VIDEO,
                num_faces=1
            )
            self.landmarker = vision.FaceLandmarker.create_from_options(options)
        else:
            self.landmarker = mp.solutions.face_mesh.FaceMesh(refine_landmarks=True)

    def start_camera(self, device_index=0):
        if self.cam is None or not self.cam.isOpened():
            self.cam = cv2.VideoCapture(device_index)
            self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def stop_camera(self):
        if self.cam is not None and self.cam.isOpened():
            self.cam.release()
            self.cam = None

    def process_frame(self):
        if self.cam is None or not self.cam.isOpened():
            return None, None

        ret, frame = self.cam.read()
        if not ret or frame is None:
            return None, None

        frame = cv2.flip(frame, 1)
        frame_h, frame_w, _ = frame.shape
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        landmarks = None

        if not self.has_solutions:
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            timestamp_ms = int((time.time() - self.start_time) * 1000)
            output = self.landmarker.detect_for_video(mp_image, timestamp_ms)
            if output.face_landmarks:
                landmarks = output.face_landmarks[0]
        else:
            output = self.landmarker.process(rgb_frame)
            if output.multi_face_landmarks:
                landmarks = output.multi_face_landmarks[0].landmark

        info = {
            "landmarks_detected": landmarks is not None,
            "raw_feature": (0.5, 0.5),
            "target_screen": (self.curr_screen_x, self.curr_screen_y),
            "blink": False
        }

        if landmarks:
            # Nose tip (landmark 1) for head position
            nose = landmarks[1]
            head_x = nose.x
            head_y = nose.y

            # Right Iris (landmarks 474:478, center 473)
            iris = landmarks[473] if len(landmarks) > 473 else landmarks[475]
            iris_x = iris.x
            iris_y = iris.y

            # Blend head and eye position based on ratio configuration
            ratio = self.config_manager.get("head_eye_ratio", 0.5)
            combined_x = ratio * head_x + (1.0 - ratio) * iris_x
            combined_y = ratio * head_y + (1.0 - ratio) * iris_y

            info["raw_feature"] = (combined_x, combined_y)

            # Retrieve calibration bounds
            calib = self.config_manager.get("calibration", {})
            x_min = calib.get("raw_x_min", 0.35)
            x_max = calib.get("raw_x_max", 0.65)
            y_min = calib.get("raw_y_min", 0.35)
            y_max = calib.get("raw_y_max", 0.65)

            # Avoid division by zero
            dx = max(0.05, x_max - x_min)
            dy = max(0.05, y_max - y_min)

            # Normalize range into [0, 1]
            norm_x = (combined_x - x_min) / dx
            norm_y = (combined_y - y_min) / dy

            # Apply sensitivity gains and screen scaling
            x_sens = self.config_manager.get("x_sensitivity", 1.5)
            y_sens = self.config_manager.get("y_sensitivity", 1.8)

            target_screen_x = (self.screen_w / 2.0) + (norm_x - 0.5) * self.screen_w * x_sens
            target_screen_y = (self.screen_h / 2.0) + (norm_y - 0.5) * self.screen_h * y_sens

            # Apply deadzone
            deadzone = self.config_manager.get("deadzone", 0.002) * self.screen_w
            if abs(target_screen_x - self.curr_screen_x) > deadzone:
                target_x_filtered = target_screen_x
            else:
                target_x_filtered = self.curr_screen_x

            if abs(target_screen_y - self.curr_screen_y) > deadzone:
                target_y_filtered = target_screen_y
            else:
                target_y_filtered = self.curr_screen_y

            # Apply smoothing
            smooth = self.config_manager.get("smoothing", 0.35)
            self.curr_screen_x += (target_x_filtered - self.curr_screen_x) * smooth
            self.curr_screen_y += (target_y_filtered - self.curr_screen_y) * smooth

            # Clamp within screen dimensions
            clamped_x = max(5, min(self.screen_w - 5, int(self.curr_screen_x)))
            clamped_y = max(5, min(self.screen_h - 5, int(self.curr_screen_y)))

            info["target_screen"] = (clamped_x, clamped_y)

            # Move physical mouse cursor if control is enabled
            if self.config_manager.get("mouse_control_enabled", False):
                try:
                    pyautogui.moveTo(clamped_x, clamped_y)
                except Exception:
                    pass

            # Blink Detection (Eyelid landmarks 145 & 159)
            left_eyelid_bottom = landmarks[145]
            left_eyelid_top = landmarks[159]
            eyelid_dist = abs(left_eyelid_bottom.y - left_eyelid_top.y)

            blink_thresh = self.config_manager.get("blink_threshold", 0.005)
            blink_cooldown = self.config_manager.get("blink_cooldown", 0.8)

            now = time.time()
            if eyelid_dist < blink_thresh and (now - self.last_blink_time) > blink_cooldown:
                info["blink"] = True
                self.last_blink_time = now
                if self.config_manager.get("blink_enabled", True) and self.config_manager.get("mouse_control_enabled", False):
                    try:
                        pyautogui.click()
                    except Exception:
                        pass

            # Draw visual landmarks on camera preview frame
            if self.config_manager.get("draw_landmarks", True):
                # Draw head center (nose tip)
                nx, ny = int(nose.x * frame_w), int(nose.y * frame_h)
                cv2.circle(frame, (nx, ny), 5, (255, 0, 0), -1)

                # Draw iris landmarks (474:478)
                for lm in landmarks[474:478]:
                    ix, iy = int(lm.x * frame_w), int(lm.y * frame_h)
                    cv2.circle(frame, (ix, iy), 2, (0, 255, 0), -1)

                # Draw eyelid landmarks
                for lm in [left_eyelid_bottom, left_eyelid_top]:
                    ex, ey = int(lm.x * frame_w), int(lm.y * frame_h)
                    cv2.circle(frame, (ex, ey), 3, (0, 255, 255), -1)

                if info["blink"]:
                    cv2.putText(frame, "BLINK CLICK!", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        return frame, info
