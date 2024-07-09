import threading
import queue
import time
from collections import deque

resource_mutexes = {}
resource_availability = {}

edf_waiting_queue = queue.PriorityQueue()
rms_waiting_queue = deque()
timer = time.time()
alg = 'EDF'

def display(processors):
    resource_status = ' '.join([f"{res}:{count}" for res, count in resource_availability.items()])
    edf_queue = ', '.join([t.name for t in list(edf_waiting_queue.queue)])
    rms_queue = ', '.join([t.name for t in list(rms_waiting_queue)])
    print("")
    print("")
    print(f"Resources: {resource_status}")
    print("")
    print(f"Waiting Queue EDF: [{edf_queue}]")
    print(f"Waiting Queue RMS: [{rms_queue}]")
    print("")
    for p in processors:
        print(f"CPU{p.id + 1}:")
        print(f"CPU Utilization: {(p.utilization / 1.0) * 100:.2f}%")
        ready_queue = [f"{t.name}:{t.repeat_count}" for t in list(p.ready_queue.queue)]
        print(f"Ready Queue[ {', '.join(ready_queue)} ]")
        print(f"Running Task: {p.running_task.name if p.running_task else 'idle'}")


def is_task_schedulable(task, processor):
    return processor.utilization + (task.execution_time / task.period) <= 1.0

def assign_tasks(tasks, processors, alg):
    unschedulable_tasks = []
    for task in tasks:
        p = processors[task.pid]
        if is_task_schedulable(task, p):
            p.ready_queue.put(task)
            p.utilization += (task.execution_time / task.period)
        else:
            unschedulable_tasks.append(task)
    if alg == 'EDF':
        for task in unschedulable_tasks:
            edf_waiting_queue.put(task)
    elif alg == 'RMS':
        for task in unschedulable_tasks:
            rms_waiting_queue.append(task)

def balance_task_load(processors, alg):
    for processor in processors:
        if processor.utilization < 0.5:
            if alg == 'RMS' and rms_waiting_queue:
                task = rms_waiting_queue.popleft()
                if is_task_schedulable(task, processor):
                    processor.ready_queue.put(task)
                    processor.utilization += (task.execution_time / task.period)
                else:
                    rms_waiting_queue.append(task)
            if alg == 'EDF' and not edf_waiting_queue.empty():
                task = edf_waiting_queue.get()
                if is_task_schedulable(task, processor):
                    processor.ready_queue.put(task)
                    processor.utilization += (task.execution_time / task.period)
                else:
                    edf_waiting_queue.put(task)

            for other_processor in processors:
                if other_processor.utilization > 0.75 and not other_processor.ready_queue.empty():
                    task = other_processor.ready_queue.get()
                    if is_task_schedulable(task, processor):
                        processor.ready_queue.put(task)
                        processor.utilization += (task.execution_time / task.period)
                        other_processor.utilization -= (task.execution_time / task.period)
                    else:
                        other_processor.ready_queue.put(task)

def lock_resources(task, locked_resources):
    for resource, amount in task.resources.items():
        if amount > 0:
            if not resource_mutexes[resource].acquire(blocking=False):
                return False
            locked_resources.append(resource)
            resource_availability[resource] -= amount
    return True

def release_locked_resources(locked_resources, resources):
    for resource in locked_resources:
        resource_mutexes[resource].release()
        resource_availability[resource] += resources[resource]

def execute_task(task, stop_event):
    timer = time.time()
    while task.remaining_time > 0 and not stop_event.is_set():
        task.remaining_time -= 1
        time.sleep(1)
    print(f"Task {task.name} processed in {time.time() - timer:.2f} seconds")

def worker(processor, stop_event, scheduling_algo):
    while not stop_event.is_set():
        try:
            task = processor.ready_queue.get(timeout=1)
        except queue.Empty:
            continue

        locked_resources = []
        if not lock_resources(task, locked_resources):
            release_locked_resources(locked_resources, task.resources)
            if scheduling_algo == 'EDF':
                edf_waiting_queue.put(task)
            elif scheduling_algo == 'RMS':
                rms_waiting_queue.append(task)
            processor.ready_queue.task_done()
            continue

        processor.running_task = task
        execute_task(task, stop_event)

        release_locked_resources(locked_resources, task.resources)
        task.repeat_count -= 1
        if task.repeat_count > 0:
            task.deadline = time.time() + task.period
            task.remaining_time = task.execution_time
            processor.ready_queue.put(task)
        else:
            processor.utilization = max(processor.utilization - (task.execution_time / task.period), 0)
        processor.running_task = None
        processor.ready_queue.task_done()

def handle_waiting_tasks(processors, alg):
    if alg == 'RMS':
        while rms_waiting_queue:
            t = rms_waiting_queue.popleft()
            p = processors[t.pid]
            if is_task_schedulable(t, p):
                p.ready_queue.put(t)
                p.utilization += (t.execution_time / t.period)
            else:
                rms_waiting_queue.append(t)
                break
    elif alg == 'EDF':
        while not edf_waiting_queue.empty():
            t = edf_waiting_queue.get()
            p = processors[t.pid]
            if is_task_schedulable(t, p):
                p.ready_queue.put(t)
                p.utilization += (t.execution_time / t.period)
            else:
                edf_waiting_queue.put(t)
                break

def update_utilization(processors):
    for p in processors:
        p.utilization_history.append(p.utilization)

def check_termination_condition(processors):
    return edf_waiting_queue.empty() and not rms_waiting_queue and all(p.ready_queue.empty() and p.running_task is None for p in processors)

def main_thread(processors, stop_event, scheduling_algo):
    for p in processors:
        t = threading.Thread(target=worker, args=(p, stop_event, scheduling_algo))
        t.start()
        p.thread = t

    while not stop_event.is_set():
        handle_waiting_tasks(processors, scheduling_algo)
        balance_task_load(processors, scheduling_algo)
        time.sleep(1)
        update_utilization(processors)
        if check_termination_condition(processors):
            stop_event.set()

    for p in processors:
        p.ready_queue.join()



class Task:
    def __init__(self, name, period, execution_time, resources, pid, repeat_count):
        self.pid = pid
        self.name = name
        self.period = period
        self.execution_time = execution_time
        self.resources = resources
        self.repeat_count = repeat_count
        self.deadline = time.time() + self.period
        self.remaining_time = execution_time

    def __lt__(self, other):
        return self.deadline < other.deadline # EDF
        # return self.period < other.period # RMS

class Processor:
    def __init__(self, id):
        self.id = id
        self.utilization_history = deque()
        self.ready_queue = queue.PriorityQueue()
        self.utilization = 0
        self.running_task = None
        self.thread = None


tasks = [
        Task('T1', 50, 2, {'R1': 1, 'R2': 0, 'R3': 0}, 0, 4),
        Task("T1", 50, 2, {'R1': 1, 'R2': 0, 'R3': 0}, 0, 4),
        Task("T2", 70, 3, {'R1': 0, 'R2': 2, 'R3': 0}, 1, 5),
        Task("T3", 30, 1, {'R1': 0, 'R2': 0, 'R3': 1}, 2, 6),
        Task("T4", 50, 2, {'R1': 1, 'R2': 1, 'R3': 0}, 0, 3),
        Task("T5", 60, 3, {'R1': 0, 'R2': 2, 'R3': 1}, 1, 2),
    ]

resources = list(map(int, input("Enter Resources: ").split()))

for index, resource in enumerate(resources):
    resource_name = f"R{index + 1}"
    resource_mutexes[resource_name] = threading.Lock()
    resource_availability[resource_name] = resource

processors = [Processor(i) for i in range(3)]

assign_tasks(tasks, processors, alg)

for t in tasks:
    deadlines = [t.period * i for i in range(1, t.repeat_count + 1)]
    print(f"{t.name} Deadlines: {', '.join(map(str, deadlines))}")

stop_event = threading.Event()
scheduler = threading.Thread(target=main_thread, args=(processors, stop_event, alg))
scheduler.start()

try:
    while scheduler.is_alive():
        display(processors)
        time.sleep(1)
except KeyboardInterrupt:
    stop_event.set()

scheduler.join()

display(processors)