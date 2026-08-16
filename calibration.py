import time
import tkinter as tk

class CalibrationWindow(tk.Toplevel):
    def __init__(self, parent, tracker_engine, config_manager, on_complete_callback=None):
        super().__init__(parent)
        self.tracker_engine = tracker_engine
        self.config_manager = config_manager
        self.on_complete_callback = on_complete_callback

        self.title("Eye Control Mouse - 9-Point Calibration")
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.configure(bg="#111827")  # Sleek dark background

        self.canvas = tk.Canvas(self, bg="#111827", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.screen_w = self.winfo_screenwidth()
        self.screen_h = self.winfo_screenheight()

        # 9 Target locations (percentages of screen)
        self.target_points = [
            (0.10, 0.10, "Top-Left"),
            (0.50, 0.10, "Top-Center"),
            (0.90, 0.10, "Top-Right"),
            (0.10, 0.50, "Center-Left"),
            (0.50, 0.50, "Center"),
            (0.90, 0.50, "Center-Right"),
            (0.10, 0.90, "Bottom-Left"),
            (0.50, 0.90, "Bottom-Center"),
            (0.90, 0.90, "Bottom-Right")
        ]

        self.current_step = 0
        self.collected_samples = []
        self.calibration_results = []
        self.is_running = True

        self.bind("<Escape>", self.cancel_calibration)

        # Instructions label
        self.info_label = tk.Label(
            self,
            text="Look directly at the glowing red dot as it moves around the screen.",
            font=("Helvetica", 18, "bold"),
            fg="#F9FAFB",
            bg="#111827"
        )
        self.info_label.place(relx=0.5, rely=0.03, anchor="center")

        self.sub_label = tk.Label(
            self,
            text="Press ESC anytime to cancel.",
            font=("Helvetica", 12),
            fg="#9CA3AF",
            bg="#111827"
        )
        self.sub_label.place(relx=0.5, rely=0.06, anchor="center")

        # Start calibration sequence after brief delay
        self.after(800, self.next_target)

    def cancel_calibration(self, event=None):
        self.is_running = False
        self.destroy()

    def next_target(self):
        if not self.is_running:
            return

        if self.current_step >= len(self.target_points):
            self.finish_calibration()
            return

        px, py, name = self.target_points[self.current_step]
        cx = int(px * self.screen_w)
        cy = int(py * self.screen_h)

        self.collected_samples = []
        self.animate_and_collect(cx, cy, name, 0)

    def animate_and_collect(self, cx, cy, name, frame_count):
        if not self.is_running:
            return

        self.canvas.delete("all")

        # Pulsating circle radius
        pulse_radius = 25 + int(8 * (frame_count % 10 < 5))

        # Outer ring
        self.canvas.create_oval(
            cx - pulse_radius - 10, cy - pulse_radius - 10,
            cx + pulse_radius + 10, cy + pulse_radius + 10,
            outline="#EF4444", width=3
        )
        # Inner solid dot
        self.canvas.create_oval(
            cx - 12, cy - 12, cx + 12, cy + 12,
            fill="#F87171", outline="#FFFFFF", width=2
        )

        # Progress text
        step_text = f"Point {self.current_step + 1} / {len(self.target_points)} ({name})"
        self.canvas.create_text(
            cx, cy + 50,
            text=step_text,
            fill="#E5E7EB",
            font=("Helvetica", 14, "bold")
        )

        # Sample raw feature from tracker
        _, info = self.tracker_engine.process_frame()
        if info and info.get("landmarks_detected"):
            self.collected_samples.append(info["raw_feature"])

        # Collect for ~20 frames (~1 second per point)
        if frame_count < 22:
            self.after(40, lambda: self.animate_and_collect(cx, cy, name, frame_count + 1))
        else:
            if self.collected_samples:
                avg_x = sum(s[0] for s in self.collected_samples) / len(self.collected_samples)
                avg_y = sum(s[1] for s in self.collected_samples) / len(self.collected_samples)
                self.calibration_results.append((px, py, avg_x, avg_y))

            self.current_step += 1
            self.after(300, self.next_target)

    def finish_calibration(self):
        if not self.calibration_results:
            self.cancel_calibration()
            return

        # Calculate bounding min/max from left, right, top, bottom points
        left_samples = [res[2] for res in self.calibration_results if res[0] <= 0.2]
        right_samples = [res[2] for res in self.calibration_results if res[0] >= 0.8]
        top_samples = [res[3] for res in self.calibration_results if res[1] <= 0.2]
        bottom_samples = [res[3] for res in self.calibration_results if res[1] >= 0.8]

        raw_x_min = sum(left_samples) / len(left_samples) if left_samples else min(res[2] for res in self.calibration_results)
        raw_x_max = sum(right_samples) / len(right_samples) if right_samples else max(res[2] for res in self.calibration_results)
        raw_y_min = sum(top_samples) / len(top_samples) if top_samples else min(res[3] for res in self.calibration_results)
        raw_y_max = sum(bottom_samples) / len(bottom_samples) if bottom_samples else max(res[3] for res in self.calibration_results)

        calib_data = {
            "is_calibrated": True,
            "raw_x_min": raw_x_min,
            "raw_x_max": raw_x_max,
            "raw_y_min": raw_y_min,
            "raw_y_max": raw_y_max,
            "points": self.calibration_results
        }

        self.config_manager.set("calibration", calib_data)
        self.config_manager.save()

        if self.on_complete_callback:
            self.on_complete_callback(calib_data)

        self.destroy()
