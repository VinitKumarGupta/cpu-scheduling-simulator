"""
utils.py

Contains utility functions for calculating metrics, generating colors, 
exporting simulation results (CSV), and loading live system processes.
"""
import pandas as pd
import psutil # For reading live system processes
from typing import List, Dict, Tuple, Any
from tkinter import filedialog, messagebox
import time
import math 

# Define the type for a basic process structure
ProcessInput = Dict[str, Any]

# --- Global Process Color Map (Final Legend Data Source) ---
# This dictionary maps the internal PID (1, 2, 3...) to a hex color.
# We make this a global constant so the GUI can access the map for the legend.
PROCESS_COLOR_MAP = {
    1: '#1f77b4', 2: '#ff7f0e', 3: '#2ca02c', 4: '#d62728', 
    5: '#9467bd', 6: '#8c564b', 7: '#e377c2', 8: '#7f7f7f', 
    9: '#bcbd22', 10: '#17becf', 11: '#aec7e8', 12: '#ffbb78',
    13: '#98df8a', 14: '#ff9896', 15: '#c5b0d5', 16: '#c49c94',
    17: '#f7b6d2', 18: '#c7c7c7', 19: '#dbdb8d', 20: '#9edae5'
}
IDLE_COLOR = '#444444' # Dark gray for idle time


def load_live_processes() -> List[ProcessInput]:
    """
    Fetches a snapshot of currently running processes from the OS using psutil 
    and estimates simulation parameters (AT, BT, Priority).
    
    This function takes two snapshots 2 seconds apart to estimate the CPU load 
    during that period, providing a more accurate Burst Time estimate.
    """
    
    # --- Step 1: Take Snapshot 1 ---
    snapshot1 = {}
    for proc in psutil.process_iter(['pid', 'name', 'cpu_times', 'status', 'nice']):
        if proc.info['status'] == psutil.STATUS_RUNNING or proc.info['status'] == psutil.STATUS_SLEEPING:
            try:
                snapshot1[proc.info['pid']] = {
                    'name': proc.info['name'],
                    'cpu_time_user': proc.info['cpu_times'].user,
                    'cpu_time_system': proc.info['cpu_times'].system,
                    'nice': proc.info['nice'] 
                }
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    
    # --- Step 2: Wait for 2 seconds ---
    time.sleep(2) 
    
    # --- Step 3: Take Snapshot 2 and Calculate Delta ---
    live_processes = []
    pid_counter = 1
    
    for proc in psutil.process_iter(['pid', 'name', 'cpu_times', 'cpu_percent', 'status', 'nice']):
        if proc.info['pid'] in snapshot1:
            try:
                p1 = snapshot1[proc.info['pid']]
                p2 = proc.info
                
                # CPU time used during the 2-second interval (the delta)
                cpu_delta = (p2['cpu_times'].user + p2['cpu_times'].system) - \
                            (p1['cpu_time_user'] + p1['cpu_time_system'])

                if cpu_delta > 0.05: # Only include processes that actually consumed measurable CPU time
                    
                    # --- Estimate Priority (P) (Realistic) ---
                    base_nice = p1['nice'] 
                    
                    # FIX: Handle NoneType crash - If niceness is None (for kernel threads), assign a neutral value (e.g., 0)
                    if base_nice is None: 
                        base_nice = 0
                        
                    # Normalize the niceness value (standard niceness range is -20 to +19; add 21 to shift to [1, 40])
                    priority_estimate = base_nice + 21 
                    priority = max(1, min(40, priority_estimate)) 

                    # --- Estimate Burst Time (BT) ---
                    burst_time = max(1.0, cpu_delta * 8.0) 
                    
                    live_processes.append({
                        'pid': pid_counter, # Reassign internal PID starting from 1
                        'name': p2['name'], # Use the actual process name
                        'arrival': 0.0,     # Assume available immediately
                        'burst': burst_time,
                        'priority': priority
                    })
                    pid_counter += 1

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
            
    # Sort processes by the priority (highest priority first)
    live_processes.sort(key=lambda p: p['priority'])
    
    return live_processes


def calculate_average_metrics(metrics: Dict[str, Dict[str, float]], final_time: float) -> Dict[str, float]:
    """
    Calculates average metrics (TAT, WT) and throughput based on per-process metrics.
    """
    if not metrics:
        return {}

    num_processes = len(metrics)
    total_tat = sum(m['TAT'] for m in metrics.values())
    total_wt = sum(m['WT'] for m in metrics.values())

    avg_tat = total_tat / num_processes
    avg_wt = total_wt / num_processes
    
    # Throughput is defined as the number of completed processes per unit of time
    throughput = num_processes / final_time if final_time > 0 else 0

    return {
        "Average Turnaround Time": avg_tat,
        "Average Waiting Time": avg_wt,
        "Total Waiting Time": total_wt,
        "Throughput (proc/unit)": throughput
    }

def calculate_cpu_utilization(timeline: List[Tuple[str, float, float]], final_time: float) -> float:
    """
    Calculates CPU utilization percentage based on non-idle time.
    """
    if final_time <= 0:
        return 0.0

    # Sum up the time spent on any process that is not 'Idle'
    busy_time = sum(end - start for pid, start, end in timeline if pid != 'Idle')
    
    # Utilization is (Busy Time / Total Time) * 100
    utilization = (busy_time / final_time) * 100
    return utilization

def get_process_color(pid: str) -> str:
    """
    Returns the color string for a given process ID based on the global map.
    """
    if pid == 'Idle':
        return IDLE_COLOR
    
    try:
        # Map PID to the fixed color index in the global map
        return PROCESS_COLOR_MAP[(int(pid) - 1) % len(PROCESS_COLOR_MAP) + 1]
    except ValueError:
        return '#aaaaaa' # Default color if PID is not a number

def export_results(processes_input: List[ProcessInput], 
                   metrics: Dict[str, Dict[str, float]], 
                   timeline: List[Tuple[str, float, float]], 
                   algorithm_name: str) -> bool:
    """
    Exports simulation input, metrics, and timeline to a single CSV file.
    
    Returns: True if export was successful, False otherwise.
    """
    try:
        # Open file dialog to choose save location
        default_filename = f"{algorithm_name.replace(' ', '_')}_results.csv"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_filename,
            filetypes=[("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        
        if not filepath:
            return False # User cancelled the dialog

        # --- 1. Create Metrics DataFrame ---
        df_metrics = pd.DataFrame.from_dict(metrics, orient='index')
        df_metrics.index.name = 'pid' # Ensure column name matches input for merging
        df_metrics = df_metrics.reset_index() # Make PID a regular column

        # Calculate Averages for Summary
        final_time = max(t[2] for t in timeline) if timeline else 0.0
        avg_metrics = calculate_average_metrics(metrics, final_time)
        cpu_util = calculate_cpu_utilization(timeline, final_time)

        # Combine input and output metrics
        df_input = pd.DataFrame(processes_input)
        df_final = pd.merge(df_input, df_metrics, on='pid', how='left')

        # --- 2. Create Timeline DataFrame ---
        df_timeline = pd.DataFrame(timeline, columns=['PID', 'Start_Time', 'End_Time'])
        
        # --- 3. Write to CSV ---
        with open(filepath, 'w', newline='') as f:
            # Write Header and Summary Information
            f.write(f"CPU Scheduling Simulation Report\n")
            f.write(f"Algorithm,{algorithm_name}\n")
            f.write(f"Average Turnaround Time,{avg_metrics.get('Average Turnaround Time', 'N/A'):.2f}\n")
            f.write(f"Average Waiting Time,{avg_metrics.get('Average Waiting Time', 'N/A'):.2f}\n")
            f.write(f"CPU Utilization,{cpu_util:.2f}%\n")
            f.write(f"Total Completion Time,{final_time:.2f}\n\n")

            f.write("--- Process Metrics (Input and Output) ---\n")
            df_final.to_csv(f, index=False, float_format='%.2f')
            
            f.write("\n\n--- Execution Timeline ---\n")
            df_timeline.to_csv(f, index=False, float_format='%.2f')

        return True

    except Exception as e:
        # In a real GUI, this should ideally log the error
        print(f"Error during export: {e}")
        messagebox.showerror("Export Error", f"An error occurred during export: {e}")
        return False
