import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import copy
from typing import List, Dict, Any, Tuple
import traceback
import time  # Used inside load_live_processes indirectly

# Local imports (Flat imports for PyInstaller compatibility)
from scheduler import (
    fcfs, sjf_non_preemptive, srtf_preemptive,
    priority_non_preemptive, priority_preemptive, round_robin
)
from utils import calculate_average_metrics, calculate_cpu_utilization, export_results, get_process_color, load_live_processes

# Type hint for Process data structure used in GUI
GUIProcess = Dict[str, Any]

# --- Theme Configuration ---
# Improved contrast and defined color palettes
DARK_THEME = {
    'bg': '#1e1e1e', 'fg': '#ffffff', 'accent': '#00bcd4', 'border': '#444444',
    'input_bg': "#2c3e50", 'tree_bg': '#282828', 'tree_heading_bg': '#3f51b5',
    'plot_bg': '#1e1e1e', 'plot_grid': '#555555', 'plot_text': 'white',
    'button_run': '#0078d7', 'button_export': '#4caf50', 'button_reset': '#f44336'
}
LIGHT_THEME = {'bg': '#fafafa',            # Softer white background
    'fg': "#0b0101",            # Dark gray text (easier on eyes than pure black)
    'accent': '#007acc',        # VS Code-like accent blue
    'border': '#d0d0d0',        # Gentle border tone
    'input_bg': '#ffffff',      # Input field background
    'tree_bg': '#ffffff',       # Table/tree background
    'tree_heading_bg': '#1976d2', # Blue heading for contrast
    'plot_bg': '#ffffff',       # Plot background
    'plot_grid': "#48778f",    # Light but visible grid
    'plot_text': "#000000",    # Black for maximum readability
    'button_run': '#0078d7',   # Modern blue
    'button_export': '#2e7d32',# Muted green (good contrast)
    'button_reset': '#d32f2f'  # Muted red
}