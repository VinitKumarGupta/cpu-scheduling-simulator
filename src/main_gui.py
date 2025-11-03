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

class CPUSchedulerApp:
    def __init__(self, master):
        self.master = master
        master.title("CPU Scheduling Simulator")
        master.geometry("1300x850")

        # --- Simulation State ---
        self.processes: List[GUIProcess] = []
        self.current_pid = 1
        self.timeline: List[Tuple[str, float, float]] = []
        self.animation_running = False
        self.current_step = 0
        self.playback_speed = 500  # milliseconds delay per step
        self.current_theme = DARK_THEME  # Default to dark theme

        # Keys must match what update_control_visibility expects
        self.algorithm_options = {
            "FCFS": fcfs, "SJF (Non-Preemptive)": sjf_non_preemptive,
            "SJF (Preemptive)": srtf_preemptive, "Priority (Non-Preemptive)": priority_non_preemptive,
            "Priority (Preemptive)": priority_preemptive, "Round Robin (RR)": round_robin
        }
        self.algorithm_var = tk.StringVar(master, value="FCFS")
        self.quantum_var = tk.DoubleVar(master, value=2.0)
        self.cso_var = tk.DoubleVar(master, value=0.0)  # Context Switch Overhead variable

        self.priority_widgets = {}

        # Ensure theme setup happens before widget creation
        self._setup_style()
        self.master.configure(bg=self.current_theme['bg'])  # Set initial background

        # Initialize input_vars before calling _create_widgets or update_process_table
        self.input_vars = {
            'pid': tk.StringVar(value=str(self.current_pid)),
            'arrival': tk.StringVar(value="0.0"),
            'burst': tk.StringVar(value=""),
            'priority': tk.StringVar(value="1")
        }

        self._create_widgets()
        self._create_menu()

        self.update_process_table()


    def _create_menu(self):
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        theme_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Theme", menu=theme_menu)

        theme_menu.add_command(label="Dark Theme", command=lambda: self.switch_theme(DARK_THEME))
        theme_menu.add_command(label="Light Theme", command=lambda: self.switch_theme(LIGHT_THEME))

    def switch_theme(self, theme):
        self.current_theme = theme
        self.master.configure(bg=theme['bg'])
        self._setup_style()  # Re-call to update style configurations

        # Redraw components to reflect new colors
        try:
            self.ax.set_facecolor(theme['plot_bg'])
            self.ax.tick_params(axis='x', colors=theme['plot_text'])
            self.ax.tick_params(axis='y', colors=theme['plot_text'])
            self.ax.spines['bottom'].set_color(theme['plot_text'])
            self.ax.spines['left'].set_color(theme['plot_text'])
            self.ax.set_xlabel("Time (ms)", color=theme['plot_text'])
            self.ax.set_title(self.ax.get_title(), color=theme['plot_text'])
            self.ax.grid(axis='x', linestyle='--', color=theme['plot_grid'])
            self.canvas.draw()
        except Exception:
            # In case called before plot creation
            pass

        self.update_process_table()  # Redraw table to reflect current theme


    def _setup_style(self):
        self.style = ttk.Style()
        # Use a stable theme
        try:
            self.style.theme_use('clam')
        except Exception:
            pass
        theme = self.current_theme

        # General Configuration
        self.style.configure('TFrame', background=theme['bg'])
        self.style.configure('TLabel', background=theme['bg'], foreground=theme['fg'], font=('Helvetica', 10))
        self.style.configure('TLabelframe', background=theme['bg'], foreground=theme['accent'], bordercolor=theme['border'])
        self.style.configure('TLabelframe.Label', background=theme['bg'], foreground=theme['accent'], font=('Helvetica', 12, 'bold'))

        # Buttons
        self.style.configure('TButton', padding=6, relief="flat", foreground=theme['fg'], font=('Helvetica', 10, 'bold'))

        # Specific Button Colors
        self.style.configure('Run.TButton', background=theme['button_run'], foreground=theme['fg'])
        self.style.configure('Export.TButton', background=theme['button_export'], foreground=theme['fg'])
        self.style.configure('Reset.TButton', background=theme['button_reset'], foreground=theme['fg'])

        # Entry/Combobox
        self.style.configure('TEntry', fieldbackground=theme['input_bg'], foreground=theme['fg'], bordercolor=theme['border'])

        # Dropdown Fix
        self.style.configure('TCombobox', fieldbackground=theme['input_bg'], foreground=theme['fg'], selectbackground=theme['input_bg'])
        self.style.map('TCombobox', fieldbackground=[('readonly', theme['tree_bg'])], foreground=[('readonly', theme['fg'])])
        self.style.configure('TCombobox.Border', background=theme['tree_bg'])

        # Treeview Fix
        self.style.configure("Treeview", background=theme['tree_bg'], foreground=theme['fg'], fieldbackground=theme['tree_bg'])
        self.style.configure("Treeview.Heading", background=theme['tree_heading_bg'], foreground=theme['fg'])


    def _create_widgets(self):
        main_frame = ttk.Frame(self.master, padding="15"); main_frame.pack(fill=tk.BOTH, expand=True)
        left_panel = ttk.Frame(main_frame, width=350); left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15)); left_panel.pack_propagate(False)

        # 1. New Process Input
        input_frame = ttk.LabelFrame(left_panel, text=" ⚙️ New Process Input", padding="10"); input_frame.pack(fill=tk.X, pady=(0, 15))

        for i, (label_text, key) in enumerate([("PID (Read Only):", 'pid'), ("Arrival Time (AT):", 'arrival'), ("Burst Time (BT):", 'burst')]):
            ttk.Label(input_frame, text=label_text).grid(row=i, column=0, sticky="w", padx=5, pady=4)
            entry = ttk.Entry(input_frame, textvariable=self.input_vars[key], width=15)
            entry.grid(row=i, column=1, padx=5, pady=4, sticky="ew")
            if key == 'pid':
                entry.config(state='readonly')

        row = 3
        priority_label = ttk.Label(input_frame, text="Priority (P):")
        priority_entry = ttk.Entry(input_frame, textvariable=self.input_vars['priority'], width=15)
        self.priority_widgets = {'label': priority_label, 'entry': priority_entry, 'row': row}

        input_button_frame = ttk.Frame(input_frame, style='TFrame'); input_button_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky="ew")
        input_button_frame.columnconfigure(0, weight=1); input_button_frame.columnconfigure(1, weight=1)
        ttk.Button(input_button_frame, text="➕ Add Process", command=self.add_process).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(input_button_frame, text="💻 Load Live Processes", command=self.load_live_data).grid(row=0, column=1, sticky="ew", padx=(5, 0))

        # 2. Process List Table
        self._create_process_table(left_panel)

        # 3. Algorithm Selector & Controls
        control_frame = ttk.LabelFrame(left_panel, text=" ⚡ Algorithm Controls", padding="10"); control_frame.pack(fill=tk.X, pady=10)
        control_frame.columnconfigure(0, weight=0); control_frame.columnconfigure(1, weight=1)

        ttk.Label(control_frame, text="Algorithm:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        algo_menu = ttk.Combobox(control_frame, textvariable=self.algorithm_var, values=list(self.algorithm_options.keys()), state="readonly", style='TCombobox')
        algo_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        algo_menu.bind('<<ComboboxSelected>>', self.update_control_visibility)

        # CSO Input (Row 1)
        ttk.Label(control_frame, text="CSO (ms):").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Entry(control_frame, textvariable=self.cso_var, width=15).grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        # Quantum Input (for RR)
        self.quantum_label = ttk.Label(control_frame, text="Quantum (q):"); self.quantum_entry = ttk.Entry(control_frame, textvariable=self.quantum_var, width=15)
        self.update_control_visibility()

        # Action Buttons (Row 2)
        action_buttons_container = ttk.Frame(control_frame, style='TFrame'); action_buttons_container.grid(row=2, column=0, columnspan=2, pady=15, sticky="ew")
        action_button_frame = ttk.Frame(action_buttons_container); action_button_frame.pack(fill=tk.X, expand=True)
        action_button_frame.columnconfigure(0, weight=1); action_button_frame.columnconfigure(1, weight=1); action_button_frame.columnconfigure(2, weight=1)

        ttk.Button(action_button_frame, text="▶ Run", command=self.run_simulation, style='Run.TButton').grid(row=0, column=0, sticky="ew", padx=2)
        ttk.Button(action_button_frame, text="⬇ Export", command=self.export_results_ui, style='Export.TButton').grid(row=0, column=1, sticky="ew", padx=2)
        ttk.Button(action_button_frame, text="⟲ Reset", command=self.reset_data, style='Reset.TButton').grid(row=0, column=2, sticky="ew", padx=2)

        # Prediction Report (Row 3)
        self.prediction_report_frame = ttk.LabelFrame(control_frame, text=" ⚡ Live Prediction Report", padding="10")
        self.prediction_report_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0)); self.prediction_report_frame.grid_remove()
        self.prediction_labels = {}
        for i, metric in enumerate(["FCFS WT:", "SJF WT:", "RR WT:", "Priority WT:"]):
            ttk.Label(self.prediction_report_frame, text=metric, font=('Helvetica', 9, 'bold'), foreground=self.current_theme['fg']).grid(row=i, column=0, sticky="w", padx=(5, 5), pady=2)
            value_label = ttk.Label(self.prediction_report_frame, text="---", foreground='#F0E68C', font=('Helvetica', 9, 'bold'))
            value_label.grid(row=i, column=1, sticky="w", padx=(0, 5), pady=2); self.prediction_labels[metric] = value_label


        # 4. Results and Plot Panel
        right_panel = ttk.Frame(main_frame); right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self._create_results_section(right_panel)
        self._create_plot_section(right_panel)


    def _create_process_table(self, parent):
        table_frame = ttk.LabelFrame(parent, text=" 📋 Current Process List", padding="10"); table_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        columns = ("Int_ID", "Name", "AT", "BT", "P", "Actions")
        self.process_tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=12)

        self.process_tree.heading("Int_ID", text="ID"); self.process_tree.heading("Name", text="Name (PID)"); self.process_tree.heading("AT", text="AT")
        self.process_tree.heading("BT", text="BT"); self.process_tree.heading("P", text="P"); self.process_tree.heading("Actions", text="Actions")
        self.process_tree.column("Int_ID", width=30, anchor=tk.CENTER); self.process_tree.column("Name", width=110, anchor=tk.W)
        self.process_tree.column("AT", width=40, anchor=tk.CENTER); self.process_tree.column("BT", width=40, anchor=tk.CENTER)
        self.process_tree.column("P", width=30, anchor=tk.CENTER); self.process_tree.column("Actions", width=60, anchor=tk.CENTER)

        self.process_tree.pack(fill=tk.BOTH, expand=True)
        self.process_tree.bind('<ButtonRelease-1>', self.handle_table_click)

    def _create_results_section(self, parent):
        results_frame = ttk.LabelFrame(parent, text=" 📊 Performance Metrics", padding="10"); results_frame.pack(fill=tk.X, pady=(0, 15))
        columns = ("PID", "CT", "TAT", "WT"); self.metrics_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=5)
        for col in columns: self.metrics_tree.heading(col, text=col); self.metrics_tree.column(col, width=80, anchor=tk.CENTER)
        self.metrics_tree.pack(fill=tk.BOTH, expand=False, pady=(0, 10))

        summary_frame = ttk.Frame(results_frame, style='TFrame'); summary_frame.pack(fill=tk.X, pady=(5, 0))
        self.summary_labels = {}; metrics = ["Avg TAT:", "Avg WT:", "CPU Util:", "Throughput:"]
        for i, metric in enumerate(metrics):
            ttk.Label(summary_frame, text=metric, font=('Helvetica', 10, 'bold'), foreground=self.current_theme['fg']).grid(row=0, column=i*2, sticky="w", padx=(15, 5))
            value_label = ttk.Label(summary_frame, text="N/A", foreground='#ffffcc', font=('Helvetica', 10, 'bold'))
            value_label.grid(row=0, column=i*2 + 1, sticky="w", padx=(0, 20)); self.summary_labels[metric] = value_label

    def _create_plot_section(self, parent):
        plot_frame = ttk.LabelFrame(parent, text=" 📈 Gantt Chart Visualization", padding="10"); plot_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.fig, self.ax = plt.subplots(figsize=(8, 4), facecolor=self.current_theme['plot_bg'])
        self.fig.tight_layout(pad=3.0)
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame); self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill=tk.BOTH, expand=True)

        self.ax.set_facecolor(self.current_theme['plot_bg']); self.ax.tick_params(axis='x', colors=self.current_theme['plot_text']); self.ax.tick_params(axis='y', colors=self.current_theme['plot_text'])
        self.ax.spines['bottom'].set_color(self.current_theme['plot_text']); self.ax.spines['left'].set_color(self.current_theme['plot_text']); self.ax.set_yticks([]); self.ax.set_xlabel("Time (ms)", color=self.current_theme['plot_text'])
        self.ax.set_title("Gantt Chart", color=self.current_theme['plot_text'], fontdict={'fontsize': 14, 'fontweight': 'bold'}); self.ax.grid(axis='x', linestyle='--', color=self.current_theme['plot_grid'])


    


    def run_prediction_report(self, processes_list: List[GUIProcess]):
        results = {}; cso_time = self.cso_var.get()
        scheduler_processes = [{'pid': str(p['pid']), 'arrival': p['arrival'], 'burst': p['burst'], 'priority': p['priority']} for p in processes_list]

        def safe_run(algo_name, *args):
            try:
                sim_processes = copy.deepcopy(scheduler_processes)
                if algo_name == "Round Robin (RR)":
                    _, metrics = self.algorithm_options[algo_name](sim_processes, self.quantum_var.get(), cso_time)
                else:
                    _, metrics = self.algorithm_options[algo_name](sim_processes, cso_time)
                return calculate_average_metrics(metrics, 1.0).get('Average Waiting Time', float('inf'))
            except Exception:
                return float('inf')

        results["FCFS WT:"] = safe_run("FCFS", scheduler_processes); results["SJF WT:"] = safe_run("SJF (Non-Preemptive)", scheduler_processes)
        results["RR WT:"] = safe_run("Round Robin (RR)", scheduler_processes); results["Priority WT:"] = safe_run("Priority (Preemptive)", scheduler_processes)

        valid_results = {k: v for k, v in results.items() if v != float('inf')}; min_wt = min(valid_results.values()) if valid_results else None

        for key, value in results.items():
            if value == float('inf'): text = "Error"; color = '#ff4d4d'
            else: text = f"{value:.2f} ms"; color = '#7CFC00' if value == min_wt else '#F0E68C'
            self.prediction_labels[key].config(text=text, foreground=color)

        self.prediction_report_frame.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))


    def run_simulation(self):
        self.animation_running = False
        if not self.processes: self.display_results_final({}, "N/A", clear_only=True); return

        algorithm_name = self.algorithm_var.get(); algorithm_func = self.algorithm_options[algorithm_name]
        cso_time = self.cso_var.get(); scheduler_processes = [{'pid': str(p['pid']), 'arrival': p['arrival'], 'burst': p['burst'], 'priority': p['priority']} for p in self.processes]

        try:
            if algorithm_name == "Round Robin (RR)":
                quantum = self.quantum_var.get(); timeline, metrics = algorithm_func(scheduler_processes, self.quantum_var.get(), cso_time)
                if quantum <= 0: messagebox.showerror("Input Error", "Time Quantum must be greater than 0."); return
            else: timeline, metrics = algorithm_func(scheduler_processes, cso_time)

            self.timeline = timeline; self.current_step = 0; self.animation_running = True

            self.ax.clear(); self.ax.set_facecolor(self.current_theme['plot_bg'])
            self.ax.set_title(f"Gantt Chart: {algorithm_name} (Initializing)", color=self.current_theme['plot_text'], fontdict={'fontsize': 14, 'fontweight': 'bold'})
            self.ax.tick_params(axis='x', colors=self.current_theme['plot_text']); self.ax.grid(axis='x', linestyle='--', color=self.current_theme['plot_grid'])
            self.canvas.draw()

            self.master.after(self.playback_speed, self.animate_gantt_chart, metrics, algorithm_name)

        except Exception as e: messagebox.showerror("Simulation Error", f"An error occurred during simulation: {e}"); traceback.print_exc(); self.animation_running = False


    def animate_gantt_chart(self, metrics: Dict[str, Dict[str, float]], algorithm_name: str):
        if not self.animation_running or self.current_step >= len(self.timeline):
            self.animation_running = False; self.display_results_final(metrics, algorithm_name); return

        pid, start, end = self.timeline[self.current_step]

        self.ax.clear(); self.ax.set_facecolor(self.current_theme['plot_bg'])
        self.ax.set_title(f"Gantt Chart: {algorithm_name} (Executing P{pid})", color=self.current_theme['plot_text'], fontdict={'fontsize': 14, 'fontweight': 'bold'})

        for i in range(self.current_step + 1):
            p, s, e = self.timeline[i]; duration = e - s; color = get_process_color(p)

            # Decide text color: white on dark theme, black on light theme. Idle always white
            if p == 'Idle':
                text_color = 'white'
            else:
                text_color = 'white' if self.current_theme == DARK_THEME else 'black'

            edgecolor = 'yellow' if i == self.current_step and p != 'Idle' else 'black'
            linewidth = 2 if i == self.current_step and p != 'Idle' else 1

            self.ax.barh(0.5, duration, left=s, height=0.5, align='center', color=color, edgecolor=edgecolor, linewidth=linewidth)

            if p != 'Idle':
                # Only draw text if the duration is long enough to prevent overlap
                if duration > 1:
                    self.ax.text(s + duration / 2, 0.5, f"P{p}", ha='center', va='center', color=text_color, fontsize=10, fontweight='bold')
            elif duration > 0.5:
                self.ax.text(s + duration / 2, 0.5, f"Idle ({duration:.1f})", ha='center', va='center', color='white', fontsize=10)

        final_time = self.timeline[-1][2]; self.ax.set_xlim(0, final_time * 1.05); self.ax.set_yticks([0.5]); self.ax.set_yticklabels(["CPU"], color=self.current_theme['plot_text'])
        self.ax.tick_params(axis='x', colors=self.current_theme['plot_text']); self.ax.grid(axis='x', linestyle='--', color=self.current_theme['plot_grid']); self.ax.set_xlabel("Time (ms)", color=self.current_theme['plot_text']); self.canvas.draw()

        self.current_step += 1; self.master.after(self.playback_speed, self.animate_gantt_chart, metrics, algorithm_name)


    def display_results_final(self, metrics: Dict[str, Dict[str, float]], algorithm_name: str, clear_only=False):
        for item in self.metrics_tree.get_children(): self.metrics_tree.delete(item)
        for label in self.summary_labels.values(): label.config(text="N/A", foreground='#ffffcc')

        if clear_only or not self.timeline:
            self.ax.clear(); self.ax.set_yticks([]); self.ax.set_title("Gantt Chart", color=self.current_theme['plot_text'], fontdict={'fontsize': 14, 'fontweight': 'bold'}); self.ax.set_facecolor(self.current_theme['plot_bg'])
            self.ax.tick_params(axis='x', colors=self.current_theme['plot_text']); self.ax.grid(axis='x', linestyle='--', color=self.current_theme['plot_grid']); self.canvas.draw()
            return

        final_time = self.timeline[-1][2] if self.timeline else 0.0

        for pid in sorted(metrics.keys(), key=lambda x: int(x)):
            m = metrics[pid]; self.metrics_tree.insert("", tk.END, values=(pid, f"{m['CT']:.2f}", f"{m['TAT']:.2f}", f"{m['WT']:.2f}"))

        avg_metrics = calculate_average_metrics(metrics, final_time); cpu_util = calculate_cpu_utilization(self.timeline, final_time)
        self.summary_labels["Avg TAT:"].config(text=f"{avg_metrics.get('Average Turnaround Time', 0.0):.2f}", foreground='#F0E68C')
        self.summary_labels["Avg WT:"].config(text=f"{avg_metrics.get('Average Waiting Time', 0.0):.2f}", foreground='#F0E68C')
        self.summary_labels["CPU Util:"].config(text=f"{cpu_util:.2f}%", foreground='#7CFC00')
        self.summary_labels["Throughput:"].config(text=f"{avg_metrics.get('Throughput (proc/unit)', 0.0):.3f}", foreground='#F0E68C')

        # Redraw final Gantt chart (no animation, full blocks)
        self.ax.clear(); self.ax.set_facecolor(self.current_theme['plot_bg'])
        self.ax.set_title(f"Gantt Chart: {algorithm_name} (Finished)", color=self.current_theme['plot_text'], fontdict={'fontsize': 14, 'fontweight': 'bold'})

        for p, s, e in self.timeline:
            duration = e - s; color = get_process_color(p); text_color = 'white' if p == 'Idle' else ('white' if self.current_theme == DARK_THEME else 'black')
            self.ax.barh(0.5, duration, left=s, height=0.5, align='center', color=color, edgecolor='black', linewidth=1)

            if p != 'Idle':
                if duration > 1.0:  # Check duration again for final static plot
                    self.ax.text(s + duration / 2, 0.5, f"P{p}", ha='center', va='center', color=text_color, fontsize=10, fontweight='bold')
            elif duration > 0.5:
                self.ax.text(s + duration / 2, 0.5, f"Idle ({duration:.1f})", ha='center', va='center', color='white', fontsize=10)

        self.ax.set_xlim(0, final_time * 1.05); self.ax.set_yticks([0.5]); self.ax.set_yticklabels(["CPU"], color=self.current_theme['plot_text'])
        self.ax.tick_params(axis='x', colors=self.current_theme['plot_text']); self.ax.grid(axis='x', linestyle='--', color=self.current_theme['plot_grid']); self.ax.set_xlabel("Time (ms)", color=self.current_theme['plot_text']); self.canvas.draw()


    def export_results_ui(self):
        """Run a simulation and export results using the utility function `export_results` imported from utils.
        Renamed from `export_results` to avoid confusion between method and utility function name.
        """
        if not self.processes: messagebox.showinfo("Export Error", "Please run a simulation before exporting results."); return
        algorithm_name = self.algorithm_var.get(); cso_time = self.cso_var.get()

        try:
            scheduler_processes = [{'pid': str(p['pid']), 'arrival': p['arrival'], 'burst': p['burst'], 'priority': p['priority']} for p in self.processes]
            if algorithm_name == "Round Robin (RR)":
                timeline, metrics = self.algorithm_options[algorithm_name](scheduler_processes, self.quantum_var.get(), cso_time)
            else:
                timeline, metrics = self.algorithm_options[algorithm_name](scheduler_processes, cso_time)
            success = export_results(self.processes, metrics, timeline, algorithm_name)
            if success: messagebox.showinfo("Export Success", "Simulation results exported successfully!")
        except Exception as e: messagebox.showerror("Export Error", f"Failed to run simulation for export: {e}")

    def update_control_visibility(self, event=None):
        algo = self.algorithm_var.get()

        if algo == "Round Robin (RR)":
            self.quantum_label.grid(row=1, column=0, sticky="w", padx=5, pady=5); self.quantum_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        else:
            self.quantum_label.grid_forget(); self.quantum_entry.grid_forget()

        if "Priority" in algo:
            self.priority_widgets['label'].grid(row=self.priority_widgets['row'], column=0, sticky="w", padx=5, pady=4); self.priority_widgets['entry'].grid(row=self.priority_widgets['row'], column=1, padx=5, pady=4, sticky="ew")
        elif algo in ["FCFS", "SJF (Non-Preemptive)", "SJF (Preemptive)", "Round Robin (RR)"]:
            self.priority_widgets['label'].grid_forget(); self.priority_widgets['entry'].grid_forget()
            self.input_vars['priority'].set("1")

    def add_process(self):
        try:
            pid = self.current_pid; arrival = float(self.input_vars['arrival'].get()); burst = float(self.input_vars['burst'].get())
            priority = int(self.input_vars['priority'].get())
            if burst <= 0: messagebox.showerror("Input Error", "Burst Time must be positive."); return
            if arrival < 0 or burst < 0 or priority < 0: messagebox.showerror("Input Error", "Time and Priority values must be non-negative."); return

            new_process = {'pid': pid, 'name': f"P{pid}", 'arrival': arrival, 'burst': burst, 'priority': priority}
            self.processes.append(new_process); self.processes.sort(key=lambda p: p['arrival'])
            self.update_process_table()
            self.current_pid += 1; self.input_vars['pid'].set(str(self.current_pid))
            self.input_vars['arrival'].set(f"{arrival:.1f}"); self.input_vars['burst'].set(""); self.input_vars['priority'].set("1")
            self.run_simulation()

        except ValueError: messagebox.showerror("Input Error", "Please ensure all fields are valid numbers. Burst Time cannot be empty.")

    def delete_process(self, pid_to_delete):
        self.processes = [p for p in self.processes if p['pid'] != pid_to_delete]; self.update_process_table(); self.run_simulation()

    def handle_table_click(self, event):
        item = self.process_tree.identify_row(event.y)
        if item:
            col = self.process_tree.identify_column(event.x)
            if col == '#6':
                pid_str = self.process_tree.item(item, 'values')[0]
                try: self.delete_process(int(pid_str))
                except ValueError: pass

    def update_process_table(self):
        for item in self.process_tree.get_children(): self.process_tree.delete(item)
        for p in self.processes:
            display_name = p.get('name', f"P{p['pid']}"); display_priority = p['priority']
            self.process_tree.insert("", tk.END, values=(p['pid'], display_name, f"{p['arrival']:.1f}", f"{p['burst']:.1f}", display_priority, "Delete"))

    def reset_data(self):
        self.processes = []; self.current_pid = 1; self.timeline = []
        self.input_vars['pid'].set(str(self.current_pid)); self.input_vars['arrival'].set("0.0"); self.input_vars['burst'].set("")
        self.input_vars['priority'].set("1")
        self.update_process_table()
        self.display_results_final({}, "N/A", clear_only=True)


if __name__ == "__main__":
    import sys, os
    # Fix relative imports when running directly
    sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    try:
        root = tk.Tk()
        app = CPUSchedulerApp(root)
        root.mainloop()
    except Exception as e:
        print(f"Application failed to start: {e}")
