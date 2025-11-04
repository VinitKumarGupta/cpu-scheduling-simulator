# ⚡ CPU Scheduling Simulator (OS Project)

This project is a comprehensive CPU Scheduling Simulator designed to visualize and analyze the performance of various scheduling algorithms commonly studied in Operating Systems courses. It features a graphical user interface (GUI) built with `tkinter`, animated Gantt charts using `matplotlib`, and the ability to load real-time process data from the operating system using `psutil`.

## ✨ Features

* **Interactive GUI:** User-friendly interface built with `tkinter`.
* **Animated Gantt Charts:** Visualize the execution timeline of processes with a step-by-step animation.
* **Performance Metrics:** Calculate and display key performance indicators:
    * Completion Time (CT)
    * Turnaround Time (TAT)
    * Waiting Time (WT)
    * Average Turnaround Time (Avg TAT)
    * Average Waiting Time (Avg WT)
    * CPU Utilization and Throughput
* **Context Switch Overhead (CSO):** Algorithms can be simulated with a customizable Context Switch Overhead (CSO) time.
* **Live Process Loading:** Load a snapshot of currently running OS processes to use as input for the simulation, with estimated Burst Time and Priority based on CPU usage and niceness.
* **Theme Switching:** Toggle between Dark and Light themes.
* **Export Results:** Export all simulation data (input, metrics, timeline) to a CSV file.

## ⚙️ Supported Algorithms

The simulator includes implementations for both non-preemptive and preemptive versions of popular algorithms:

1.  **First-Come, First-Served (FCFS)**
2.  **Shortest Job First (SJF) - Non-Preemptive**
3.  **Shortest Remaining Time First (SRTF) - Preemptive (Preemptive SJF)**
4.  **Priority - Non-Preemptive**
5.  **Priority - Preemptive**
6.  **Round Robin (RR)** (with adjustable time quantum)

## 💻 Installation and Setup

### Prerequisites

You must have Python installed (Python 3.x is recommended).

### Install Dependencies

The required libraries are listed in `requirements.txt`.

1.  Clone the repository:
    ```bash
    git clone [https://github.com/vinitkumargupta/cpu-scheduling-simulator.git](https://github.com/vinitkumargupta/cpu-scheduling-simulator.git)
    cd cpu-scheduling-simulator
    ```

2.  Install the required packages:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: The `psutil` library is required for the "Load Live Processes" feature.*

## ▶️ Usage

To launch the GUI, run the main script from the `src` directory:

```bash
python src/main_gui.py
