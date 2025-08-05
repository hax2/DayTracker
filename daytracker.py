# -*- coding: utf-8 -*-
"""
Advanced Always-On-Top Vertical Time Tracker
Author: Samer
"""
import tkinter as tk
from tkinter import ttk, colorchooser, messagebox
import datetime
import threading
import time
import json
import os
import copy
import math

# --- Configuration Management ---
class ConfigManager:
    """Handles loading, saving, and managing application settings."""
    THEMES = {
        "Default": {
            "bar_color_1": "#1E90FF", "bar_color_2": "#00FFFF",
            "background_color": "#2B2B2B", "text_color": "#FFFFFF",
            "completed_color": "#00FF00"
        },
        "Forest": {
            "bar_color_1": "#228B22", "bar_color_2": "#7CFC00",
            "background_color": "#2F4F4F", "text_color": "#FFFFFF",
            "completed_color": "#32CD32"
        },
        "Ocean": {
            "bar_color_1": "#1E90FF", "bar_color_2": "#87CEFA",
            "background_color": "#4682B4", "text_color": "#FFFFFF",
            "completed_color": "#00BFFF"
        },
        "Sunset": {
            "bar_color_1": "#FF4500", "bar_color_2": "#FFD700",
            "background_color": "#6A5ACD", "text_color": "#FFFFFF",
            "completed_color": "#FF6347"
        }
    }


    DEFAULT_CONFIG = {
        "start_time": "09:00",
        "end_time": "17:30",
        "geometry": {"width": 10, "height": 250, "x": 150, "y": 150},
        "appearance": {
            "bar_color_1": "#1E90FF", "bar_color_2": "#00FFFF",
            "background_color": "#2B2B2B", "text_color": "#FFFFFF",
            "completed_color": "#00FF00", "opacity": 0.9, "corner_radius": 15,
            "theme": "Default",
            "timer": {
                "ring_width": 12,
                "bar_color_1": "#FF4500",
                "bar_color_2": "#FFD700",
                "background_color": "#444444"
            }
        },
        "behavior": {
            "update_interval_seconds": 5, "display_mode": "Percentage",
            "day_definition_mode": "Start Time & Duration", "duration_hours": 8.0,
            "show_text_label": True,
            "auto_position": False, # New: Auto-position to left of screen
        }
    }
    CONFIG_FILE = "adv_tracker_config.json"

    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r') as f:
                    loaded_config = json.load(f)
                    # Deep merge ensures new default settings are added if config file is old
                    return self._deep_merge_dicts(copy.deepcopy(self.DEFAULT_CONFIG), loaded_config)
            except (json.JSONDecodeError, IOError): pass
        return copy.deepcopy(self.DEFAULT_CONFIG)

    def save_config(self):
        try:
            with open(self.CONFIG_FILE, 'w') as f: json.dump(self.config, f, indent=4)
        except IOError as e:
            messagebox.showerror("Config Error", f"Could not save configuration file:\n{e}")

    def get(self, key_path):
        keys = key_path.split('.'); value = self.config
        try:
            for key in keys: value = value[key]
            return value
        except KeyError: # Return default if key doesn't exist (e.g., old config file)
             keys = key_path.split('.'); value = self.DEFAULT_CONFIG
             for key in keys: value = value[key]
             return value


    def set(self, key_path, value):
        keys = key_path.split('.'); d = self.config
        for key in keys[:-1]: d = d.setdefault(key, {})
        d[keys[-1]] = value
    
    def _deep_merge_dicts(self, base, new):
        for key, value in new.items():
            if isinstance(value, dict) and key in base and isinstance(base[key], dict):
                base[key] = self._deep_merge_dicts(base[key], value)
            else: base[key] = value
        return base

# --- Main Application ---
class TimeProgressBar(tk.Tk):
    def __init__(self, config_manager):
        super().__init__()
        self.config_manager = config_manager
        self.drag_info = {}; self.current_percentage = 0.0
        self.target_percentage = 0.0; self.animation_job = None
        self.time_remaining_seconds = 0
        self.total_work_seconds = 3600 # Default to 1 hour to prevent zero division

        self.overrideredirect(True); self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "black"); self.configure(bg="black")

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.label = tk.Label(self, bg="#000001", fg="white", font=("Segoe UI", 9, "bold"))

        self.active_timers = [] # List to hold multiple timer windows

        self._create_context_menu(); self._bind_events(); self.apply_config()
        threading.Thread(target=self._update_loop, daemon=True).start()

    def _create_context_menu(self):
        self.context_menu = tk.Menu(self, tearoff=0, bg="#333333", fg="white")
        self.context_menu.add_command(label="Settings", command=self.open_settings)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Start Break", command=self._start_break)
        self.context_menu.add_command(label="End Break", command=self._end_break, state="disabled")
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Start Timer", command=self.open_timer_setter)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Quit", command=self.quit)

    def _bind_events(self):
        self.bind("<ButtonPress-1>", self._on_press); self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", self._on_release); self.bind("<Button-3>", self._show_context_menu)

    def _calculate_day_range(self):
        """Calculates and returns start, end, and total seconds for the workday."""
        now = datetime.datetime.now()
        start_h, start_m = map(int, self.config_manager.get('start_time').split(':'))
        start_of_day = now.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
        
        mode = self.config_manager.get('behavior.day_definition_mode')
        if mode == "Start Time & Duration":
            end_of_day = start_of_day + datetime.timedelta(hours=self.config_manager.get('behavior.duration_hours'))
        else: # "Start Time & End Time"
            end_h, end_m = map(int, self.config_manager.get('end_time').split(':'))
            end_of_day = now.replace(hour=end_h, minute=end_m, second=0, microsecond=0)
            if end_of_day < start_of_day: end_of_day += datetime.timedelta(days=1)
        
        # If 'now' is before the workday started, look at yesterday's workday
        if now < start_of_day:
            start_of_day -= datetime.timedelta(days=1)
            end_of_day -= datetime.timedelta(days=1)
            
        total_seconds = (end_of_day - start_of_day).total_seconds()
        return start_of_day, end_of_day, total_seconds

    def _update_loop(self):
        while True:
            try:
                now = datetime.datetime.now()
                start_of_day, end_of_day, total_seconds = self._calculate_day_range()
                
                self.total_work_seconds = total_seconds if total_seconds > 0 else 1
                
                elapsed_seconds = (now - start_of_day).total_seconds()
                self.time_remaining_seconds = self.total_work_seconds - elapsed_seconds
                
                # CHANGE: Percentage is now based on time REMAINING
                self.target_percentage = max(0, min(100, (self.time_remaining_seconds / self.total_work_seconds) * 100))
                
                if self.animation_job is None: self.after(0, self._animate_bar)
            except (ValueError, TypeError): 
                self.target_percentage = 0
                self.total_work_seconds = 3600 # Reset on error
            time.sleep(self.config_manager.get('behavior.update_interval_seconds'))

    def _animate_bar(self):
        diff = self.target_percentage - self.current_percentage
        if abs(diff) < 0.1: 
            self.current_percentage = self.target_percentage
            self.animation_job = None
        else: 
            self.current_percentage += diff * 0.15
            self.animation_job = self.after(16, self._animate_bar)
        self._redraw_canvas()

    def _redraw_canvas(self):
        self.canvas.delete("all"); w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1: return
        
        r = min(self.config_manager.get('appearance.corner_radius'), w//2, h//2)
        bg_color = self.config_manager.get('appearance.background_color')
        
        # Draw background
        self._create_rounded_rectangle(0, 0, w, h, r, fill=bg_color)

        # Draw the progress bar (time remaining)
        bar_height = h * (self.current_percentage / 100); y0 = h - bar_height
        c1 = self.config_manager.get('appearance.bar_color_1'); c2 = self.config_manager.get('appearance.bar_color_2')
        if self.time_remaining_seconds <= 0:
            c1 = self.config_manager.get('appearance.completed_color')
            c2 = c1
        if c1 == c2:
            self._create_rounded_rectangle(0, y0, w, h, r, fill=c1)
        else:
            self._create_gradient_bar(0, y0, w, h, r, c1, c2)

        # NEW: Draw hourly segment lines on TOP of the bar
        total_hours = round(self.total_work_seconds / 3600)
        if total_hours > 1:
            segment_height = h / total_hours
            for i in range(1, total_hours):
                y_pos = i * segment_height
                # A faint line that contrasts with a dark background
                self.canvas.create_line(0, y_pos, w, y_pos, fill="#555555", width=1)
        
        # NEW: Conditionally show or hide the label
        if self.config_manager.get('behavior.show_text_label'):
            self._update_label_text()
            self.label.place(relx=0.5, rely=0.5, anchor="center")
        else:
            self.label.place_forget() # Hide the label

    def _create_rounded_rectangle(self, x1, y1, x2, y2, r, **kwargs):
        p = [x1+r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y2-r, x2, y2, x2-r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y1+r, x1, y1]
        self.canvas.create_polygon(p, **kwargs, smooth=True, joinstyle=tk.ROUND)

    def _create_gradient_bar(self, x1, y1, x2, y2, r, c1, c2):
        try: c1r,c2r = self.winfo_rgb(c1), self.winfo_rgb(c2)
        except tk.TclError: return
        h = y2 - y1;
        if h <= 0: return
        r_rat,g_rat,b_rat = (c2r[0]-c1r[0])/h, (c2r[1]-c1r[1])/h, (c2r[2]-c1r[2])/h
        for i in range(int(y1), int(y2)):
            nr,ng,nb = int(c1r[0]+(i-y1)*r_rat), int(c1r[1]+(i-y1)*g_rat), int(c1r[2]+(i-y1)*b_rat)
            color = f'#{max(0,min(65535,nr)):04x}{max(0,min(65535,ng)):04x}{max(0,min(65535,nb)):04x}'
            self.canvas.create_line(x1, i, x2, i, fill=color)
        self._create_rounded_rectangle(x1, y1, x2, y2, r, fill="", outline="") # Use empty fill/outline to clip

    def _update_label_text(self):
        mode = self.config_manager.get('behavior.display_mode')
        # Since the bar shows remaining time, the text should be consistent
        if self.time_remaining_seconds > 0:
            h, rem = divmod(self.time_remaining_seconds, 3600)
            m, _ = divmod(rem, 60)
            h, m = int(h), int(m)
            if mode == "Time Remaining":
                text = f"{h}h {m}m" if h > 0 else f"{m}m"
            elif mode == "End Time":
                _, end_of_day, _ = self._calculate_day_range()
                text = f"Ends {end_of_day.strftime('%H:%M')}"
            else: # Percentage mode
                text = f"{self.current_percentage:.0f}%"
        else:
            text = "Done"
        self.label.config(text=text)

    def apply_config(self):
        self.attributes("-topmost", True)
        app = self.config_manager.get('appearance')
        self.attributes("-alpha", app['opacity'])
        self.label.configure(fg=app['text_color'], bg="#000001")
        self.attributes("-transparentcolor", "#000001")

        # NEW: Auto-positioning logic
        if self.config_manager.get('behavior.auto_position'):
            screen_height = self.winfo_screenheight()
            self.geometry(f"{self.config_manager.get('geometry.width')}x{screen_height}+0+0")
        else:
            geo = self.config_manager.get('geometry')
            self.geometry(f"{geo['width']}x{geo['height']}+{geo['x']}+{geo['y']}")

        self._redraw_canvas()

    def open_settings(self):
        if not hasattr(self, 'settings_window') or not self.settings_window.winfo_exists():
            self.settings_window = SettingsWindow(self, self.config_manager)
        self.settings_window.lift()

    def open_timer_setter(self):
        if not hasattr(self, 'setter_window') or not self.setter_window.winfo_exists():
            self.setter_window = TimerSetterWindow(self, self.config_manager)
        self.setter_window.lift()

    def _on_press(self, e): self.drag_info = {'x':self.winfo_x(), 'y':self.winfo_y(), 'mx':e.x_root, 'my':e.y_root}
    def _on_drag(self, e):
        if self.drag_info and not self.config_manager.get('behavior.auto_position'):
            self.geometry(f"+{self.drag_info['x']+(e.x_root-self.drag_info['mx'])}+{self.drag_info['y']+(e.y_root-self.drag_info['my'])}")
    def _on_release(self, e):
        if self.drag_info:
            self.config_manager.set('geometry.x', self.winfo_x()); self.config_manager.set('geometry.y', self.winfo_y())
            self.config_manager.save_config(); self.drag_info = {}
    def _show_context_menu(self, e): self.context_menu.post(e.x_root, e.y_root)

    def _start_break(self):
        self.break_start_time = datetime.datetime.now()
        self.context_menu.entryconfig("Start Break", state="disabled")
        self.context_menu.entryconfig("End Break", state="normal")

    def _end_break(self):
        if hasattr(self, 'break_start_time'):
            break_duration = datetime.datetime.now() - self.break_start_time
            start_of_day, _, _ = self._calculate_day_range()
            new_start_of_day = start_of_day + break_duration
            self.config_manager.set('start_time', new_start_of_day.strftime('%H:%M'))
            self.context_menu.entryconfig("Start Break", state="normal")
            self.context_menu.entryconfig("End Break", state="disabled")
            del self.break_start_time

# --- Timer Setter Window ---
class TimerSetterWindow(tk.Toplevel):
    def __init__(self, master, config_manager):
        super().__init__(master)
        self.master = master
        self.config_manager = config_manager
        self.title("Set Timer")
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.minutes_var = tk.StringVar(value="15")
        self.seconds_var = tk.StringVar(value="0")

        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(expand=True, fill="both")

        ttk.Label(main_frame, text="Set Timer Duration").pack(pady=(0, 10))

        input_frame = ttk.Frame(main_frame)
        input_frame.pack(pady=5)

        ttk.Label(input_frame, text="Minutes:").grid(row=0, column=0, padx=5, sticky="w")
        ttk.Entry(input_frame, textvariable=self.minutes_var, width=7).grid(row=0, column=1, padx=5)

        ttk.Label(input_frame, text="Seconds:").grid(row=1, column=0, padx=5, sticky="w")
        ttk.Entry(input_frame, textvariable=self.seconds_var, width=7).grid(row=1, column=1, padx=5)

        ttk.Button(main_frame, text="Start Timer", command=self._start_timer).pack(pady=(15, 0))

        self.center_window()

    def _start_timer(self):
        try:
            minutes = int(self.minutes_var.get() or 0)
            seconds = int(self.seconds_var.get() or 0)
            total_seconds = (minutes * 60) + seconds

            if total_seconds > 0:
                # Position the new timer under the last active one, or near the master
                last_y = self.master.winfo_y()
                if self.master.active_timers:
                    last_y = self.master.active_timers[-1].winfo_y() + self.master.active_timers[-1].winfo_height() + 10

                new_timer = CircularTimerWindow(self.master, self.config_manager, total_seconds, last_y)
                self.master.active_timers.append(new_timer)
                new_timer.lift()
                self.master.attributes("-topmost", True)
                self.destroy()
            else:
                messagebox.showerror("Invalid Input", "Please enter a total duration greater than zero.", parent=self)
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers for minutes and seconds.", parent=self)

    def center_window(self):
        self.update_idletasks()
        mx, my, mw, mh = self.master.winfo_x(), self.master.winfo_y(), self.master.winfo_width(), self.master.winfo_height()
        ww, wh = self.winfo_width(), self.winfo_height()
        x = mx + (mw // 2) - (ww // 2)
        y = my + (mh // 2) - (wh // 2)
        self.geometry(f'250x150+{x}+{y}')


# --- Circular Timer Window ---
class CircularTimerWindow(tk.Toplevel):
    def __init__(self, master, config_manager, duration_seconds, y_pos):
        super().__init__(master)
        self.master = master
        self.config_manager = config_manager
        self.duration = duration_seconds
        self.remaining_seconds = duration_seconds
        self.animation_job = None
        self.drag_info = {}

        self.overrideredirect(True)
        self.attributes("-topmost", True)
        self.attributes("-transparentcolor", "black")
        self.configure(bg="black")

        geo = self.config_manager.get('geometry')
        screen_w = self.winfo_screenwidth()
        x = geo['x'] + geo['width'] + 20
        y = y_pos
        if x + 100 > screen_w: # 100 is the window width
            x = geo['x'] - 100 - 20
        self.geometry(f"100x100+{x}+{y}")

        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        self.label = tk.Label(self, bg="#000001", fg="white", font=("Segoe UI", 12, "bold"))
        self.label.place(relx=0.5, rely=0.5, anchor="center")

        self._bind_events()
        self.apply_config()
        self._update_timer()

    def _bind_events(self):
        self.bind("<ButtonPress-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<Button-3>", self._close_timer) # Right-click to close

    def _on_press(self, e): self.drag_info = {'x': self.winfo_x(), 'y': self.winfo_y(), 'mx': e.x_root, 'my': e.y_root}
    def _on_drag(self, e):
        if self.drag_info:
            self.geometry(f"+{self.drag_info['x'] + (e.x_root - self.drag_info['mx'])}+{self.drag_info['y'] + (e.y_root - self.drag_info['my'])}")
    
    def _close_timer(self, e=None):
        if self.animation_job:
            self.after_cancel(self.animation_job)
        self.animation_job = None
        if self in self.master.active_timers:
            self.master.active_timers.remove(self)
        self.destroy()

    def apply_config(self):
        app = self.config_manager.get('appearance')
        timer_app = self.config_manager.get('appearance.timer')
        self.attributes("-alpha", app['opacity'])
        self.label.configure(fg=app['text_color'], bg="#000001")
        self.attributes("-transparentcolor", "#000001")
        self._redraw_canvas()

    def _update_timer(self):
        if self.remaining_seconds > 0:
            self._redraw_canvas()
            self.remaining_seconds -= 1
            self.animation_job = self.after(1000, self._update_timer)
        else:
            self.label.config(text="Done!")
            if self.animation_job:
                self.after_cancel(self.animation_job)
            self.animation_job = None
            self._flash_and_close()

    def _flash_and_close(self, count=6): # Flash 3 times (on/off)
        if count > 0:
            current_alpha = self.attributes('-alpha')
            new_alpha = 0.5 if current_alpha > 0.8 else 1.0
            self.attributes('-alpha', new_alpha)
            self.after(250, lambda: self._flash_and_close(count - 1))
        else:
            self._close_timer()

    def _redraw_canvas(self):
        self.canvas.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w <= 1 or h <= 1: return

        bg_color = self.config_manager.get('appearance.timer.background_color')
        c1 = self.config_manager.get('appearance.timer.bar_color_1')
        c2 = self.config_manager.get('appearance.timer.bar_color_2')
        ring_width = self.config_manager.get('appearance.timer.ring_width')

        self.canvas.config(bg=self.attributes("-transparentcolor"))

        self.canvas.create_arc(
            ring_width//2, ring_width//2, w-(ring_width//2), h-(ring_width//2),
            start=0, extent=360, style=tk.ARC, width=ring_width-2, outline=bg_color
        )

        percentage_remaining = self.remaining_seconds / self.duration if self.duration > 0 else 0
        self._create_gradient_arc(w/2, h/2, min(w,h)/2 - ring_width/2, ring_width, percentage_remaining, c1, c2)

        m, s = divmod(self.remaining_seconds, 60)
        self.label.config(text=f"{int(m):02d}:{int(s):02d}")

    def _create_gradient_arc(self, cx, cy, radius, width, percentage, c1, c2):
        try:
            c1_rgb = self.winfo_rgb(c1)
            c2_rgb = self.winfo_rgb(c2)
        except tk.TclError:
            return

        total_steps = int(360 * percentage)
        if total_steps <= 0: return

        for i in range(total_steps):
            angle = i - 90 # Start from top
            rad = math.radians(angle)
            
            ratio = i / 360.0
            r = int(c1_rgb[0] * (1 - ratio) + c2_rgb[0] * ratio)
            g = int(c1_rgb[1] * (1 - ratio) + c2_rgb[1] * ratio)
            b = int(c1_rgb[2] * (1 - ratio) + c2_rgb[2] * ratio)
            color = f'#{r:04x}{g:04x}{b:04x}'

            x = cx + radius * math.cos(rad)
            y = cy + radius * math.sin(rad)
            self.canvas.create_oval(x-width/2, y-width/2, x+width/2, y+width/2, fill=color, outline=color)


# --- Settings Window ---
class SettingsWindow(tk.Toplevel):
    def __init__(self, master, config_manager):
        super().__init__(master)
        self.master = master
        self.config_manager = config_manager
        self.temp_config = copy.deepcopy(config_manager.config)
        self.title("Settings")
        self.transient(master)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.vars = {}
        self._create_widgets()
        self.update_idletasks()
        self.center_window()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding=15)
        main_frame.pack(expand=True, fill="both")
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1) # Create two equally weighted columns

        # --- Column Frames ---
        left_column = ttk.Frame(main_frame)
        left_column.grid(row=0, column=0, sticky="new", padx=(0, 10))
        right_column = ttk.Frame(main_frame)
        right_column.grid(row=0, column=1, sticky="new", padx=(10, 0))

        # --- Create & Place Sections ---
        day_lf = ttk.LabelFrame(left_column, text="Day Definition", padding=10)
        day_lf.pack(fill="x", pady=5, expand=True)
        
        geo_lf = ttk.LabelFrame(left_column, text="Size & Position", padding=10)
        geo_lf.pack(fill="x", pady=5, expand=True)

        app_lf = ttk.LabelFrame(right_column, text="Appearance", padding=10)
        app_lf.pack(fill="x", pady=5, expand=True)

        beh_lf = ttk.LabelFrame(right_column, text="Behavior", padding=10)
        beh_lf.pack(fill="x", pady=5, expand=True)

        # --- Populate "Day Definition" ---
        self._create_combobox(day_lf, "Mode", "behavior.day_definition_mode", 0, ["Start Time & End Time", "Start Time & Duration"], self._toggle_day_controls)
        self._create_entry(day_lf, "Start Time (HH:MM)", "start_time", 1, validate_time=True)
        self.end_time_row = self._create_entry(day_lf, "End Time (HH:MM)", "end_time", 2, validate_time=True)
        self.duration_row = self._create_spin_slider(day_lf, "Duration", "behavior.duration_hours", 3, 1, 48, 0.5, "hrs")

        # --- Populate "Size & Position" ---
        self.width_row = self._create_spin_slider(geo_lf, "Width", "geometry.width", 0, 4, 500, 1, "px")
        self.height_row = self._create_spin_slider(geo_lf, "Height", "geometry.height", 1, 50, 1000, 1, "px")
        self._create_checkbox(geo_lf, "Auto-Position", "behavior.auto_position", 2, self._toggle_geo_controls)
        
        # --- Populate "Appearance" ---
        self._create_combobox(app_lf, "Theme", "appearance.theme", 0, list(self.config_manager.THEMES.keys()), self._apply_theme)
        self._create_color_picker(app_lf, "Bar Start Color", "appearance.bar_color_1", 1)
        self._create_color_picker(app_lf, "Bar End Color", "appearance.bar_color_2", 2)
        self._create_color_picker(app_lf, "Completed Color", "appearance.completed_color", 3)
        self._create_color_picker(app_lf, "Background Color", "appearance.background_color", 4)
        self._create_color_picker(app_lf, "Text Color", "appearance.text_color", 5)
        self.radius_row = self._create_spin_slider(app_lf, "Corner Radius", "appearance.corner_radius", 6, 0, 100, 1, "px")
        self.opacity_row = self._create_spin_slider(app_lf, "Opacity", "appearance.opacity", 7, 0.1, 1.0, 0.05, "")
        self._create_spin_slider(app_lf, "Timer Ring Width", "appearance.timer.ring_width", 8, 1, 50, 1, "px")
        self._create_color_picker(app_lf, "Timer Bar Start", "appearance.timer.bar_color_1", 9)
        self._create_color_picker(app_lf, "Timer Bar End", "appearance.timer.bar_color_2", 10)
        self._create_color_picker(app_lf, "Timer Background", "appearance.timer.background_color", 11)
        
        # --- Populate "Behavior" ---
        self._create_combobox(beh_lf, "Display Text", "behavior.display_mode", 0, ["Percentage", "Time Remaining", "End Time"])
        self._create_checkbox(beh_lf, "Show Text Label", "behavior.show_text_label", 1)

        # --- Buttons ---
        btn_frame = ttk.Frame(main_frame, padding=(0, 10, 0, 0))
        btn_frame.grid(row=1, column=0, columnspan=2, sticky="e")
        ttk.Button(btn_frame, text="Save & Close", command=self._on_save).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self._on_close).pack(side="right")
        
        # --- Finalize initial state of controls ---
        self._toggle_day_controls()
        self._toggle_geo_controls()

    def _toggle_day_controls(self, event=None):
        mode = self.vars['behavior.day_definition_mode'].get()
        if mode == "Start Time & Duration":
            for w in self.end_time_row: w.grid_remove()
            for w in self.duration_row: w.grid()
        else:
            for w in self.duration_row: w.grid_remove()
            for w in self.end_time_row: w.grid()

    def _toggle_geo_controls(self, event=None):
        auto_on = self.vars['behavior.auto_position'].get()
        state = "disabled" if auto_on else "normal"
        # Only disable the height controls, since width is still used in auto-mode
        for w in self.height_row:
            if isinstance(w, (ttk.Scale, ttk.Spinbox, ttk.Entry)):
                w.configure(state=state)
            elif isinstance(w, ttk.Frame):
                 for child in w.winfo_children():
                      child.configure(state=state)

    def _create_control_row(self, parent, label_text, row):
        label = ttk.Label(parent, text=label_text)
        label.grid(row=row, column=0, sticky="w", padx=5, pady=2)
        control_frame = ttk.Frame(parent)
        control_frame.grid(row=row, column=1, sticky="ew", padx=5, pady=2)
        parent.columnconfigure(1, weight=1)
        return label, control_frame

    def _create_entry(self, p, l, k, r, validate_time=False):
        self.vars[k] = tk.StringVar(value=self.config_manager.get(k))
        lbl, c_frame = self._create_control_row(p, l, r)
        vcmd = (self.register(self._validate_time_format), '%P') if validate_time else None
        c = ttk.Entry(c_frame, textvariable=self.vars[k], validate='key', validatecommand=vcmd)
        c.pack(fill="x"); c.bind("<KeyRelease>", lambda e, key=k: self._live_update(key, self.vars[key].get()))
        return lbl, c_frame

    def _create_combobox(self, p, l, k, r, v, cmd=None):
        self.vars[k] = tk.StringVar(value=self.config_manager.get(k))
        lbl, c_frame = self._create_control_row(p, l, r)
        c = ttk.Combobox(c_frame, textvariable=self.vars[k], values=v, state="readonly")
        c.pack(fill="x");
        if cmd: c.bind("<<ComboboxSelected>>", cmd)
        c.bind("<<ComboboxSelected>>", lambda e, key=k: self._live_update(key, self.vars[key].get()), add="+")
        return lbl, c_frame

    def _create_color_picker(self, p, l, k, r):
        self.vars[k] = tk.StringVar(value=self.config_manager.get(k))
        lbl, c_frame = self._create_control_row(p, l, r)
        prv = tk.Label(c_frame, text="   ", relief="sunken", borderwidth=1, bg=self.vars[k].get()); prv.pack(side="left", padx=(0,5))
        e = ttk.Entry(c_frame, textvariable=self.vars[k]); e.pack(side="left", expand=True, fill="x")
        def pick():
            c = colorchooser.askcolor(title=f"Choose {l}", initialcolor=self.vars[k].get())
            if c and c[1]: self.vars[k].set(c[1].upper()); self._live_update(k, c[1]); prv.config(bg=c[1])
        b = ttk.Button(c_frame, text="...", width=3, command=pick); b.pack(side="left", padx=(5,0))
        e.bind("<KeyRelease>", lambda ev, key=k, p=prv: (self._live_update(key, self.vars[key].get()), p.config(bg=self.vars[key].get())))
        return lbl, c_frame
    
    def _create_spin_slider(self, p, l, k, r, from_, to, step, unit=""):
        self.vars[k] = tk.DoubleVar(value=self.config_manager.get(k))
        lbl, c_frame = self._create_control_row(p, l, r)
        def update_from_spinbox(event=None):
            try:
                val = float(spinbox.get())
                self.vars[k].set(val); self._live_update(k, val)
            except (ValueError, tk.TclError): pass
        def update_from_slider(value):
            val = round(float(value) / step) * step
            if step >= 1: val = int(val)
            self.vars[k].set(val); spinbox.set(val); self._live_update(k, val)
        spinbox = ttk.Spinbox(c_frame, from_=from_, to=to, increment=step, textvariable=self.vars[k], command=update_from_spinbox, width=6)
        spinbox.pack(side="left", padx=(0,5))
        spinbox.bind("<KeyRelease>", update_from_spinbox)
        slider = ttk.Scale(c_frame, from_=from_, to=to, variable=self.vars[k], orient="horizontal", command=update_from_slider)
        slider.pack(side="left", expand=True, fill="x")
        return lbl, c_frame

    def _create_checkbox(self, p, l, k, r, cmd=None):
        self.vars[k] = tk.BooleanVar(value=self.config_manager.get(k))
        lbl, c_frame = self._create_control_row(p, l, r)
        def on_toggle():
            self._live_update(k, self.vars[k].get())
            if cmd: cmd()
        c = ttk.Checkbutton(c_frame, variable=self.vars[k], command=on_toggle)
        c.pack(side="left")
        return lbl, c_frame

    def _live_update(self, k, v):
        try:
            current_config_val = self.config_manager.get(k)
            # Try to cast new value to the type of the old value to maintain type consistency
            value_to_set = type(current_config_val)(v)
            self.config_manager.set(k, value_to_set)
            self.master.apply_config()
        except (ValueError, tk.TclError, KeyError, IndexError): pass

    def _apply_theme(self, event=None):
        theme_name = self.vars['appearance.theme'].get()
        theme = self.config_manager.THEMES.get(theme_name)
        if theme:
            for key, value in theme.items():
                self.vars[f'appearance.{key}'].set(value)
                self._live_update(f'appearance.{key}', value)

    def _validate_time_format(self, new_value):
        if not new_value:
            return True
        try:
            h, m = new_value.split(':')
            return len(h) <= 2 and len(m) <= 2 and 0 <= int(h) <= 23 and 0 <= int(m) <= 59
        except (ValueError, IndexError):
            return False

    def _on_save(self): self.master.config_manager.save_config(); self.master.attributes("-topmost", True); self.destroy()
    def _on_close(self): self.master.config_manager.config = self.temp_config; self.master.apply_config(); self.master.attributes("-topmost", True); self.destroy()

    def center_window(self):
        self.update_idletasks()
        self.resizable(False, False) # Prevent resizing now that layout is fixed
        mx, my, mw = self.master.winfo_x(), self.master.winfo_y(), self.master.winfo_width()
        ww, wh = self.winfo_width(), self.winfo_height()
        x, y = mx + mw + 10, my
        # Check if it goes off-screen to the right, and if so, place it on the left
        if x + ww > self.winfo_screenwidth(): 
            x = mx - ww - 10
        # Check if it goes off-screen to the left, and if so, place it at the edge
        if x < 0: 
            x = 10
        self.geometry(f'+{x}+{y}')

if __name__ == "__main__":
    try: 
        config = ConfigManager()
        app = TimeProgressBar(config)
        app.mainloop()
    except Exception as e: 
        messagebox.showerror("Fatal Error", f"An unrecoverable error occurred:\n{e}")
