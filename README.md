# DayTracker - Advanced Time Tracker

DayTracker is a highly customizable, always-on-top desktop widget that provides a visual representation of your workday's progress. It's designed to be a simple, unobtrusive tool to help you stay aware of your schedule at a glance.

![image](https://github.com/user-attachments/assets/e2552587-3161-489c-85f3-79832387832b)


## Features

*   **Always-On-Top:** The tracker bar stays visible over all other windows.
*   **Customizable Workday:** Define your day by "Start & End Time" or by "Start Time & Duration".
*   **Visual Progress Bar:** The bar visually depletes as your workday progresses, showing the time remaining.
*   **Rich Theming & Appearance:**
    *   Choose from multiple built-in themes (Default, Forest, Ocean, Sunset).
    *   Use the color pickers to select custom colors for the progress bar, background, and text.
    *   Adjust the window's opacity and corner roundness.
*   **Flexible Display:**
    *   Show progress as a percentage, time remaining, or the calculated end time.
    *   Toggle the text label on or off for a purely visual bar.
*   **Easy Positioning:**
    *   Simply drag the bar anywhere on your screen.
    *   Enable "Auto-Position" to dock it to the full height of the left side of your screen.
*   **Interactive Menu:** Right-click the bar to access the Settings panel, manage breaks, or quit the application.
*   **Break Time Management:** Pause the timer when you take a break to ensure accurate tracking.
*   **Persistent Settings:** All your appearance and behavior customizations are automatically saved in the `adv_tracker_config.json` file.

## Requirements

*   Python 3.x
*   Tkinter (usually included with standard Python installations)

## How to Run

1.  Make sure you have Python 3 installed.
2.  Save the script as `daytracker.py`.
3.  Run the script from your terminal:
    ```bash
    python daytracker.py
    ```

## How to Use

*   **Move the Window:** Click and drag the progress bar to position it on your screen. Your position will be saved automatically. (Note: Dragging is disabled if "Auto-Position" is on).
*   **Access Menu:** Right-click the bar to open the context menu.
*   **Change Settings:** Select "Settings" from the context menu to open the configuration panel. Changes are applied live as you adjust them.
*   **Take a Break:** Right-click and select "Start Break". When you return, right-click and select "End Break". The elapsed break time will be added to your workday's schedule.
*   **Quit:** Right-click and select "Quit".

## Configuration

All settings can be modified via the GUI, but they are stored in the `adv_tracker_config.json` file. The application will create this file with default values on its first run. You can manually edit this file if needed.

```json
{
    "start_time": "09:00",
    "end_time": "17:30",
    "geometry": {
        "width": 35,
        "height": 250,
        "x": 150,
        "y": 150
    },
    "appearance": {
        "bar_color_1": "#1E90FF",
        "bar_color_2": "#00FFFF",
        "background_color": "#2B2B2B",
        "text_color": "#FFFFFF",
        "completed_color": "#00FF00",
        "opacity": 0.9,
        "corner_radius": 15,
        "theme": "Default"
    },
    "behavior": {
        "update_interval_seconds": 5,
        "display_mode": "Percentage",
        "day_definition_mode": "Start Time & Duration",
        "duration_hours": 8.0,
        "show_text_label": true,
        "auto_position": false
    }
}
```
