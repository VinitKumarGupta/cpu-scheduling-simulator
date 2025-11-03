"""
scheduler.py

Contains implementations of CPU scheduling algorithms. Each algorithm returns an 
execution timeline (list of (pid, start, end)) and per-process metrics.

All functions now accept 'cso_time' for consistency, even if non-preemptive 
algorithms do not use it, simplifying the caller (main_gui.py).
"""
from typing import List, Dict, Tuple
import copy
import math

# Define types for clarity
Process = Dict[str, float]  # keys: pid, arrival, burst, priority, remainingTime

def sjf_non_preemptive(processes: List[Process], cso_time: float = 0.0) -> Tuple[List[Tuple[str, float, float]], Dict[str, Dict[str, float]]]:
    """Shortest Job First (SJF) - Non-preemptive."""
    procs = copy.deepcopy(processes)
    time = 0.0
    timeline = []
    metrics = {}
    completed = set()
    n = len(procs)
    last_process_id = None

    while len(completed) < n:
        # 1. Identify available processes (arrived and not completed)
        available = [p for p in procs if p['arrival'] <= time and p['pid'] not in completed]
        
        if not available:
            # 2. Idle until next arrival
            future = [p['arrival'] for p in procs if p['pid'] not in completed]
            if not future:
                break # All done
            
            next_arrival = min(future)
            if timeline and timeline[-1][0] == 'Idle':
                timeline[-1] = ('Idle', timeline[-1][1], next_arrival)
            else:
                timeline.append(('Idle', time, next_arrival))
            time = next_arrival
            continue

        # 3. Choose shortest burst time (SJF)
        curr = min(available, key=lambda p: p['burst'])
        
        # 4. Apply CSO if a different process is starting/switched
        if last_process_id is not None and last_process_id != curr['pid']:
            time += cso_time
        elif last_process_id is None and time > 0:
             time += cso_time # Apply CSO if starting after idle/initial start

        start = time
        end = start + curr['burst']
        
        # Add the process execution segment
        timeline.append((curr['pid'], start, end))
        
        # Calculate metrics
        ct = end
        tat = ct - curr['arrival']
        wt = tat - curr['burst']
        metrics[curr['pid']] = {'CT': ct, 'TAT': tat, 'WT': wt}
        
        completed.add(curr['pid'])
        time = end
        last_process_id = curr['pid']

    return timeline, metrics


def srtf_preemptive(processes: List[Process], cso_time: float = 0.0) -> Tuple[List[Tuple[str, float, float]], Dict[str, Dict[str, float]]]:
    """Shortest Remaining Time First (SRTF) - Preemptive SJF."""
    procs = copy.deepcopy(processes)
    for p in procs:
        p['remaining'] = p['burst']
    
    n = len(procs)
    time = 0.0
    timeline = []
    metrics = {}
    completed_pids = set()
    last_run_pid = None

    while len(completed_pids) < n:
        # 1. Identify available processes (arrived and not completed)
        available = [p for p in procs if p['arrival'] <= time and p['pid'] not in completed_pids]
        
        if not available:
            # 2. Idle until next arrival
            future = [p['arrival'] for p in procs if p['pid'] not in completed_pids and p['arrival'] > time]
            if not future:
                break
            
            next_arrival = min(future)
            if timeline and timeline[-1][0] == 'Idle':
                timeline[-1] = ('Idle', timeline[-1][1], next_arrival)
            else:
                timeline.append(('Idle', time, next_arrival))
            time = next_arrival
            last_run_pid = 'Idle'
            continue

        # 3. Choose shortest remaining time (SRTF)
        curr_proc = min(available, key=lambda p: p['remaining'])
        current_pid = curr_proc['pid']

        # 4. Check for Preemption and apply CSO
        if last_run_pid is not None and last_run_pid != current_pid:
            # If the current process is different from the last, a switch occurs
            time += cso_time
        
        # 5. Determine run time (until next event: arrival or completion)
        
        # Time to completion
        time_to_complete = curr_proc['remaining']
        
        # Time to next arrival that could preempt
        next_preemption_time = time_to_complete
        future_arrivals = [p['arrival'] for p in procs if p['arrival'] > time and p['pid'] not in completed_pids]

        if future_arrivals:
            next_arrival = min(future_arrivals)
            # Check if a future arrival has a shorter burst time than the current remaining time
            for p in procs:
                if p['arrival'] == next_arrival and p['burst'] < curr_proc['remaining']:
                     next_preemption_time = next_arrival - time
                     break
        
        run_for = min(time_to_complete, next_preemption_time)

        # 6. Execute run slice
        start_time = time
        end_time = start_time + run_for
        curr_proc['remaining'] -= run_for
        time = end_time
        
        # Update timeline (merging contiguous blocks)
        if timeline and timeline[-1][0] == current_pid and abs(timeline[-1][2] - start_time) < 1e-9:
            pid, s, e = timeline.pop()
            timeline.append((pid, s, end_time))
        else:
            timeline.append((current_pid, start_time, end_time))

        last_run_pid = current_pid

        # 7. Check for Completion
        if curr_proc['remaining'] <= 1e-9:
            completed_pids.add(current_pid)
            proc_data = next(p for p in processes if p['pid'] == current_pid)
            ct = time
            tat = ct - proc_data['arrival']
            wt = tat - proc_data['burst']
            metrics[current_pid] = {'CT': ct, 'TAT': tat, 'WT': wt}

    return timeline, metrics


def priority_non_preemptive(processes: List[Process], cso_time: float = 0.0) -> Tuple[List[Tuple[str, float, float]], Dict[str, Dict[str, float]]]:
    """Priority Scheduling - Non-preemptive."""
    procs = copy.deepcopy(processes)
    time = 0.0
    timeline = []
    metrics = {}
    completed = set()
    n = len(procs)
    last_process_id = None

    while len(completed) < n:
        available = [p for p in procs if p['arrival'] <= time and p['pid'] not in completed]
        
        if not available:
            future = [p['arrival'] for p in procs if p['pid'] not in completed]
            if not future: break
            
            next_arrival = min(future)
            if timeline and timeline[-1][0] == 'Idle':
                timeline[-1] = ('Idle', timeline[-1][1], next_arrival)
            else:
                timeline.append(('Idle', time, next_arrival))
            time = next_arrival
            continue

        # Choose highest priority (lowest number)
        curr = min(available, key=lambda p: p['priority'])
        
        # Apply CSO if a different process is starting/switched
        if last_process_id is not None and last_process_id != curr['pid']:
            time += cso_time
        elif last_process_id is None and time > 0:
             time += cso_time 

        start = time
        end = start + curr['burst']
        
        timeline.append((curr['pid'], start, end))
        
        ct = end
        tat = ct - curr['arrival']
        wt = tat - curr['burst']
        metrics[curr['pid']] = {'CT': ct, 'TAT': tat, 'WT': wt}
        
        completed.add(curr['pid'])
        time = end
        last_process_id = curr['pid']

    return timeline, metrics


def priority_preemptive(processes: List[Process], cso_time: float = 0.0) -> Tuple[List[Tuple[str, float, float]], Dict[str, Dict[str, float]]]:
    """Priority Scheduling - Preemptive."""
    procs = copy.deepcopy(processes)
    for p in procs:
        p['remaining'] = p['burst']
    
    n = len(procs)
    time = 0.0
    timeline = []
    metrics = {}
    completed_pids = set()
    last_run_pid = None

    while len(completed_pids) < n:
        available = [p for p in procs if p['arrival'] <= time and p['pid'] not in completed_pids]
        
        if not available:
            future = [p['arrival'] for p in procs if p['pid'] not in completed_pids and p['arrival'] > time]
            if not future:
                break
            
            next_arrival = min(future)
            if timeline and timeline[-1][0] == 'Idle':
                timeline[-1] = ('Idle', timeline[-1][1], next_arrival)
            else:
                timeline.append(('Idle', time, next_arrival))
            time = next_arrival
            last_run_pid = 'Idle'
            continue

        # Choose highest priority (lowest number)
        curr_proc = min(available, key=lambda p: p['priority'])
        current_pid = curr_proc['pid']

        # Check for Preemption and apply CSO
        if last_run_pid is not None and last_run_pid != current_pid:
            time += cso_time
        
        # Determine run time (until next event: arrival or completion)
        time_to_complete = curr_proc['remaining']
        next_preemption_time = time_to_complete
        
        # Find next priority arrival (potential preemption point)
        future_arrivals = [p for p in procs if p['arrival'] > time and p['pid'] not in completed_pids]
        
        if future_arrivals:
            # Find the arrival time of the process with the highest priority among future arrivals
            preempting_arrival = None
            preempting_priority = curr_proc['priority'] 
            
            for p in future_arrivals:
                if p['priority'] < preempting_priority:
                    preempting_priority = p['priority']
                    preempting_arrival = p['arrival']

            if preempting_arrival is not None:
                next_preemption_time = preempting_arrival - time
        
        run_for = min(time_to_complete, next_preemption_time)

        # Execute run slice
        start_time = time
        end_time = start_time + run_for
        curr_proc['remaining'] -= run_for
        time = end_time
        
        # Update timeline (merging contiguous blocks)
        if timeline and timeline[-1][0] == current_pid and abs(timeline[-1][2] - start_time) < 1e-9:
            pid, s, e = timeline.pop()
            timeline.append((pid, s, end_time))
        else:
            timeline.append((current_pid, start_time, end_time))

        last_run_pid = current_pid

        # Check for Completion
        if curr_proc['remaining'] <= 1e-9:
            completed_pids.add(current_pid)
            proc_data = next(p for p in processes if p['pid'] == current_pid)
            ct = time
            tat = ct - proc_data['arrival']
            wt = tat - proc_data['burst']
            metrics[current_pid] = {'CT': ct, 'TAT': tat, 'WT': wt}

    return timeline, metrics
