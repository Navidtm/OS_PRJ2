# Task Scheduling Simulation (OS PROJECT)

This program simulates task scheduling on multiple processors using either Earliest Deadline First (EDF) or Rate Monotonic Scheduling (RMS) algorithms.

The tasks are assigned to processors, and the resources required by each task are managed using mutexes for mutual exclusion.

## How to Run the Program

1. **Clone the Repository**:

   ```sh
   git clone https://github.com/Navidtm/OS_PRJ2.git
   ```

2. **Install Python**:
   Ensure you have Python installed on your system. The program is compatible with Python 3.x.

3. **Run the Program**:
   Execute the program using the following command:

   ```sh
   python index.py
   ```

4. **Input Resources**:
   When prompted, enter the available resources separated by spaces. For example:

   ```
   Enter Resources: 5 3 2
   ```

   This indicates there are 5 units of Resource 1, 3 units of Resource 2, and 2 units of Resource 3 available.

5. **Observe Output**:
   The program will display the status of resources, waiting queues, and processors. The task deadlines and their processing status will be printed to the console.

## Example Output

```yaml

Enter Resources: 5 3 2
T1 Deadlines: 50, 100, 150, 200
T1 Deadlines: 50, 100, 150, 200
T2 Deadlines: 70, 140, 210, 280, 350
T3 Deadlines: 30, 60, 90, 120, 150, 180
T4 Deadlines: 50, 100, 150
T5 Deadlines: 60, 120
Resources: R1:5 R2:3 R3:2
Waiting Queue EDF: []
Waiting Queue RMS: []
CPU1:
CPU Utilization: 0.00%
Ready Queue[ ]
Running Task: idle
CPU2:
CPU Utilization: 0.00%
Ready Queue[ ]
Running Task: idle
CPU3:
CPU Utilization: 0.00%
Ready Queue[ ]
Running Task: idle
Task T1 processed in 2.00 seconds
...

```
