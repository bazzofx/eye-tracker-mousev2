# Importing required modules
import os
import sys
import time
import urllib.request
import cv2
import mediapipe as mp
import pyautogui

# Disable PyAutoGUI fail-safe to prevent crash when cursor hits screen edge
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

# Check if legacy mp.solutions is available or if modern Tasks API should be used
has_solutions = hasattr(mp, "solutions") and hasattr(getattr(mp, "solutions", None), "face_mesh")

if not has_solutions:
    print("Using MediaPipe Tasks API (FaceLandmarker)...")
    download_model_if_needed()
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision

    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        running_mode=vision.RunningMode.VIDEO,
        num_faces=1
    )
    landmarker = vision.FaceLandmarker.create_from_options(options)
else:
    print("Using MediaPipe Solutions API (FaceMesh)...")
    face_mesh = mp.solutions.face_mesh.FaceMesh(refine_landmarks=True)

# Accessing camera
cam = cv2.VideoCapture(0)
screen_w, screen_h = pyautogui.size()
screen_x, screen_y = screen_w // 2, screen_h // 2
smooth_factor = 0.4  # Smooth movement factor

start_time = time.time()

print("Starting Eye Control Mouse. Press 'q' or 'ESC' on the video window to exit.")

while True:
    ret, frame = cam.read()
    if not ret:
        print("Camera frame not available. Exiting...")
        break

    frame = cv2.flip(frame, 1)
    frame_h, frame_w, _ = frame.shape
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    landmarks = None

    if not has_solutions:
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        timestamp_ms = int((time.time() - start_time) * 1000)
        output = landmarker.detect_for_video(mp_image, timestamp_ms)
        if output.face_landmarks:
            landmarks = output.face_landmarks[0]
    else:
        output = face_mesh.process(rgb_frame)
        if output.multi_face_landmarks:
            landmarks = output.multi_face_landmarks[0].landmark

    if landmarks:
        # Iris landmarks for cursor control (landmarks 474:478)
        for id, landmark in enumerate(landmarks[474:478]):
            x = int(landmark.x * frame_w)
            y = int(landmark.y * frame_h)
            cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)

            if id == 1:
                # Calculate screen coordinates based on iris position
                target_x = screen_w / frame_w * x
                target_y = screen_h / frame_h * y

                # Apply smoothing
                screen_x += (target_x - screen_x) * smooth_factor
                screen_y += (target_y - screen_y) * smooth_factor

                # Keep cursor within screen bounds
                clamped_x = max(10, min(screen_w - 10, screen_x))
                clamped_y = max(10, min(screen_h - 10, screen_y))

                # Move cursor
                pyautogui.moveTo(clamped_x, clamped_y)

        # Blink detection using eye landmarks
        left_eye = [landmarks[145], landmarks[159]]
        for landmark in left_eye:
            x = int(landmark.x * frame_w)
            y = int(landmark.y * frame_h)
            cv2.circle(frame, (x, y), 3, (0, 255, 255), -1)

        # Calculate eyelid distance
        if (left_eye[0].y - left_eye[1].y) < 0.004:
            pyautogui.click()
            pyautogui.sleep(0.5)

    cv2.imshow("Eye Control Mouse", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == ord('q') or key == 27:  # 'q' or ESC to exit
        break

cam.release()
cv2.destroyAllWindows()