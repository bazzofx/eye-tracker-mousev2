# Eye Control Mouse v2 Pro 👁️🖱️

A powerful Python application that utilizes computer vision to track eye gaze and head movement, allowing full hands-free mouse control with interactive calibration and customizable settings.

---

## 🌟 Key Features

- **🎯 Interactive 9-Point Calibration System**:
  Full-screen calibration wizard that maps your head and eye movement range directly to your display screen, making it effortless to reach every corner.

- **🎛️ Head vs. Eye Movement Ratio Control**:
  Adjust the blend factor between head translation and iris movement (0% Head / 100% Eye up to 100% Head / 0% Eye).

- **⚡ Independent X & Y Sensitivity Gains**:
  Fine-tune horizontal ($X$) and vertical ($Y$) multipliers so cursor movement comfortably matches your setup.

- **🎯 Advanced Smoothing & Tremor Deadzone**:
  Exponential filtering and deadzone thresholds eliminate micro-shakes when holding your gaze statically.

- **👆 Blink Click Detection**:
  Automatic click trigger on eye blinks with customizable threshold and safety cooldown.

- **🖥️ Modern CustomTkinter GUI**:
  Dark-themed desktop app featuring live webcam preview, real-time tracking badges, sliders, toggles, and master ON/OFF switch.

---

## 🛠️ Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/bazzofx/eye-tracker-mousev2.git
   cd eye-tracker-mousev2
   ```

2. **Install requirements**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python main.py
   ```

---

## 🎯 How to Calibrate

1. Click **"🎯 Start 9-Point Full Calibration"** in the app.
2. A full-screen window will appear.
3. Look directly at each glowing red dot as it moves across the 9 grid points of your screen.
4. Once completed, the app automatically calculates your personal movement boundaries and saves them to `config.json`.

---

## 📜 Configuration (`config.json`)

Settings are saved persistently in `config.json` and can also be adjusted via the UI sliders:
- `x_sensitivity`: Multiplier for horizontal cursor motion.
- `y_sensitivity`: Multiplier for vertical cursor motion.
- `head_eye_ratio`: Balance between head movement and eye gaze tracking.
- `smoothing`: Interpolation factor for cursor motion smoothness.
- `deadzone`: Tremor cancellation threshold.
- `blink_threshold`: Sensitivity for blink click detection.
- `mouse_control_enabled`: Toggle physical mouse cursor movement.
