import sys
import time
import tkinter as tk
import customtkinter as ctk
import cv2
from PIL import Image, ImageTk

from config import ConfigManager
from tracker import EyeTrackerEngine
from calibration import CalibrationWindow

# Set CustomTkinter theme and appearance mode
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class EyeControlApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Eye Control Mouse v2 Pro")
        self.geometry("1100x720")
        self.minsize(950, 650)

        # Config & Engine
        self.config_mgr = ConfigManager()
        self.tracker_engine = EyeTrackerEngine(self.config_mgr)

        self.is_running = True
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Build UI layout
        self.create_header()
        self.create_main_content()

        # Start Camera Processing
        self.tracker_engine.start_camera(0)
        self.update_video_feed()

    def create_header(self):
        header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#1E293B", height=65)
        header_frame.pack(side="top", fill="x")

        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="👁️ Eye Control Mouse v2",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#F8FAFC"
        )
        title_label.pack(side="left", padx=20, pady=15)

        # Master Toggle Switch
        self.mouse_toggle_var = ctk.BooleanVar(value=self.config_mgr.get("mouse_control_enabled", False))
        self.mouse_switch = ctk.CTkSwitch(
            header_frame,
            text="ENABLE MOUSE CONTROL",
            font=ctk.CTkFont(size=14, weight="bold"),
            variable=self.mouse_toggle_var,
            command=self.toggle_mouse_control,
            onvalue=True,
            offvalue=False,
            progress_color="#22C55E"
        )
        self.mouse_switch.pack(side="right", padx=25, pady=15)

    def create_main_content(self):
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=15, pady=15)

        # Grid setup: Left column (Camera & Calibration), Right column (Sliders & Controls)
        content_frame.grid_columnconfigure(0, weight=5)
        content_frame.grid_columnconfigure(1, weight=6)
        content_frame.grid_rowconfigure(0, weight=1)

        # LEFT PANEL: Camera Preview & Calibration
        left_panel = ctk.CTkFrame(content_frame, fg_color="#0F172A", corner_radius=12)
        left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        cam_title = ctk.CTkLabel(
            left_panel,
            text="Live Camera & Tracking Feed",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        cam_title.pack(anchor="w", padx=15, pady=(15, 10))

        # Video Canvas / Label
        self.video_label = ctk.CTkLabel(left_panel, text="", fg_color="#1E293B", corner_radius=8)
        self.video_label.pack(fill="both", expand=True, padx=15, pady=5)

        # Status & Calibration Frame
        status_frame = ctk.CTkFrame(left_panel, fg_color="#1E293B", corner_radius=8)
        status_frame.pack(fill="x", padx=15, pady=15)

        self.calib_status_label = ctk.CTkLabel(
            status_frame,
            text="Calibration Status: Loading...",
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.calib_status_label.pack(anchor="w", padx=15, pady=(10, 5))
        self.update_calibration_badge()

        self.pos_status_label = ctk.CTkLabel(
            status_frame,
            text="Cursor Position: X: 0, Y: 0",
            font=ctk.CTkFont(size=12),
            text_color="#94A3B8"
        )
        self.pos_status_label.pack(anchor="w", padx=15, pady=(0, 10))

        # Calibration Button
        self.calib_btn = ctk.CTkButton(
            left_panel,
            text="🎯 Start 9-Point Full Calibration",
            font=ctk.CTkFont(size=15, weight="bold"),
            fg_color="#6366F1",
            hover_color="#4F46E5",
            height=45,
            command=self.start_calibration
        )
        self.calib_btn.pack(fill="x", padx=15, pady=(0, 15))

        # RIGHT PANEL: Settings Sliders & Tuning Controls
        right_panel = ctk.CTkScrollableFrame(content_frame, fg_color="#0F172A", corner_radius=12)
        right_panel.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)

        # Section 1: Movement Gain / Sensitivity
        self.create_section_title(right_panel, "⚙️ Movement & Gain Calibration")

        self.x_sens_slider = self.create_slider_setting(
            right_panel,
            label_text="X-Sensitivity (Horizontal Gain):",
            from_val=0.5, to_val=4.0,
            curr_val=self.config_mgr.get("x_sensitivity", 1.5),
            command=lambda v: self.config_mgr.set("x_sensitivity", float(v))
        )

        self.y_sens_slider = self.create_slider_setting(
            right_panel,
            label_text="Y-Sensitivity (Vertical Gain):",
            from_val=0.5, to_val=4.0,
            curr_val=self.config_mgr.get("y_sensitivity", 1.8),
            command=lambda v: self.config_mgr.set("y_sensitivity", float(v))
        )

        self.ratio_slider = self.create_slider_setting(
            right_panel,
            label_text="Head vs Eye Movement Ratio (0% Head / 100% Eye):",
            from_val=0.0, to_val=1.0,
            curr_val=self.config_mgr.get("head_eye_ratio", 0.5),
            command=lambda v: self.config_mgr.set("head_eye_ratio", float(v)),
            val_formatter=lambda v: f"{int(v*100)}% Head / {int((1-v)*100)}% Eye"
        )

        # Section 2: Smoothing & Deadzone
        self.create_section_title(right_panel, "🎯 Motion Filtering & Deadzone")

        self.smooth_slider = self.create_slider_setting(
            right_panel,
            label_text="Cursor Smoothing (Lower = Faster, Higher = Smoother):",
            from_val=0.05, to_val=0.9,
            curr_val=self.config_mgr.get("smoothing", 0.35),
            command=lambda v: self.config_mgr.set("smoothing", float(v))
        )

        self.deadzone_slider = self.create_slider_setting(
            right_panel,
            label_text="Deadzone Threshold (Ignore Tremors):",
            from_val=0.0, to_val=0.01,
            curr_val=self.config_mgr.get("deadzone", 0.002),
            command=lambda v: self.config_mgr.set("deadzone", float(v)),
            val_formatter=lambda v: f"{v:.4f}"
        )

        # Section 3: Click & Display Options
        self.create_section_title(right_panel, "👆 Blink Click & Display Settings")

        self.blink_switch_var = ctk.BooleanVar(value=self.config_mgr.get("blink_enabled", True))
        self.blink_switch = ctk.CTkSwitch(
            right_panel,
            text="Enable Blink Click",
            variable=self.blink_switch_var,
            command=lambda: self.config_mgr.set("blink_enabled", self.blink_switch_var.get())
        )
        self.blink_switch.pack(anchor="w", padx=15, pady=8)

        self.blink_thresh_slider = self.create_slider_setting(
            right_panel,
            label_text="Blink Sensitivity Threshold:",
            from_val=0.002, to_val=0.012,
            curr_val=self.config_mgr.get("blink_threshold", 0.005),
            command=lambda v: self.config_mgr.set("blink_threshold", float(v)),
            val_formatter=lambda v: f"{v:.4f}"
        )

        self.landmarks_switch_var = ctk.BooleanVar(value=self.config_mgr.get("draw_landmarks", True))
        self.landmarks_switch = ctk.CTkSwitch(
            right_panel,
            text="Draw Camera Landmark Overlays",
            variable=self.landmarks_switch_var,
            command=lambda: self.config_mgr.set("draw_landmarks", self.landmarks_switch_var.get())
        )
        self.landmarks_switch.pack(anchor="w", padx=15, pady=8)

        # Action Buttons: Save & Reset
        btn_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=20)

        save_btn = ctk.CTkButton(
            btn_frame,
            text="💾 Save Configuration",
            fg_color="#10B981",
            hover_color="#059669",
            command=self.save_configuration
        )
        save_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

        reset_btn = ctk.CTkButton(
            btn_frame,
            text="↺ Reset Defaults",
            fg_color="#EF4444",
            hover_color="#DC2626",
            command=self.reset_defaults
        )
        reset_btn.pack(side="right", expand=True, fill="x", padx=(5, 0))

    def create_section_title(self, parent, text):
        lbl = ctk.CTkLabel(
            parent,
            text=text,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#CBD5E1"
        )
        lbl.pack(anchor="w", padx=15, pady=(15, 5))

    def create_slider_setting(self, parent, label_text, from_val, to_val, curr_val, command, val_formatter=None):
        frame = ctk.CTkFrame(parent, fg_color="#1E293B", corner_radius=8)
        frame.pack(fill="x", padx=15, pady=6)

        header_frame = ctk.CTkFrame(frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(8, 2))

        lbl = ctk.CTkLabel(header_frame, text=label_text, font=ctk.CTkFont(size=12))
        lbl.pack(side="left")

        val_lbl = ctk.CTkLabel(header_frame, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color="#38BDF8")
        val_lbl.pack(side="right")

        def update_val(v):
            val = float(v)
            if val_formatter:
                val_lbl.configure(text=val_formatter(val))
            else:
                val_lbl.configure(text=f"{val:.2f}")
            command(val)

        slider = ctk.CTkSlider(
            frame,
            from_=from_val,
            to=to_val,
            number_of_steps=100,
            command=update_val
        )
        slider.set(curr_val)
        slider.pack(fill="x", padx=10, pady=(0, 8))

        update_val(curr_val)
        return slider

    def toggle_mouse_control(self):
        val = self.mouse_toggle_var.get()
        self.config_mgr.set("mouse_control_enabled", val)
        self.config_mgr.save()

    def update_calibration_badge(self):
        calib = self.config_mgr.get("calibration", {})
        if calib.get("is_calibrated", False):
            self.calib_status_label.configure(
                text="Calibration Status: ✅ Calibrated (Range Active)",
                text_color="#4ADE80"
            )
        else:
            self.calib_status_label.configure(
                text="Calibration Status: ⚠️ Default (Run 9-Point Calibration)",
                text_color="#FBBF24"
            )

    def start_calibration(self):
        # Temporarily disable mouse control during calibration
        was_enabled = self.config_mgr.get("mouse_control_enabled", False)
        self.config_mgr.set("mouse_control_enabled", False)

        def on_complete(data):
            self.config_mgr.set("mouse_control_enabled", was_enabled)
            self.update_calibration_badge()

        CalibrationWindow(self, self.tracker_engine, self.config_mgr, on_complete)

    def save_configuration(self):
        self.config_mgr.save()

    def reset_defaults(self):
        self.config_mgr.reset_defaults()
        self.mouse_toggle_var.set(False)
        self.update_calibration_badge()

    def update_video_feed(self):
        if not self.is_running:
            return

        frame, info = self.tracker_engine.process_frame()
        if frame is not None:
            # Resize frame to fit canvas
            img_h, img_w, _ = frame.shape
            display_w = 440
            display_h = int(img_h * (display_w / img_w))
            frame_resized = cv2.resize(frame, (display_w, display_h))

            # Convert to PIL Image
            img = Image.fromarray(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB))
            imgtk = ImageTk.PhotoImage(image=img)

            self.video_label.imgtk = imgtk
            self.video_label.configure(image=imgtk)

            if info and info.get("target_screen"):
                tx, ty = info["target_screen"]
                self.pos_status_label.configure(text=f"Cursor Position: X: {tx}, Y: {ty}")

        self.after(20, self.update_video_feed)

    def on_closing(self):
        self.is_running = False
        self.tracker_engine.stop_camera()
        self.destroy()
        sys.exit(0)

if __name__ == "__main__":
    app = EyeControlApp()
    app.mainloop()