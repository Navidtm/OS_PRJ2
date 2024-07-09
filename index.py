import threading
import queue
import time
from collections import deque

resource_mutexes = {}
resource_availability = {}

edf_waiting_queue = queue.PriorityQueue()
rms_waiting_queue = deque()
timer = time.time()


class Task:
    def __init__(self, name, period, execution_time, resource_usage, processor_id, repeat_count):
        self.name = name
        self.period = period
        self.execution_time = execution_time
        self.resource_usage = resource_usage
        self.processor_id = processor_id
        self.repeat_count = repeat_count
        self.deadline = time.time() + self.period
        self.remaining_time = execution_time

    def __lt__(self, other):
        return self.deadline < other.deadline # EDF
        # return self.deadline < other.deadline # RMS

class Processor:
    def __init__(self, processor_id):
        self.processor_id = processor_id
        self.ready_queue = queue.PriorityQueue()
        self.thread = None
        self.utilization = 0
        self.running_task = None
        self.utilization_history = deque()

def is_task_schedulable(task, processor):
    return processor.utilization + (task.execution_time / task.period) <= 1.0

def assign_tasks(tasks, processors, alg):
    unschedulable_tasks = []
    for task in tasks:
        p = processors[task.processor_id]
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
            if alg == 'EDF' and not edf_waiting_queue.empty():
                task = edf_waiting_queue.get()
                if is_task_schedulable(task, processor):
                    processor.ready_queue.put(task)
                    processor.utilization += (task.execution_time / task.period)
                else:
                    edf_waiting_queue.put(task)
            elif alg == 'RMS' and rms_waiting_queue:
                task = rms_waiting_queue.popleft()
                if is_task_schedulable(task, processor):
                    processor.ready_queue.put(task)
                    processor.utilization += (task.execution_time / task.period)
                else:
                    rms_waiting_queue.append(task)
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
    for resource, amount in task.resource_usage.items():
        if amount > 0:
            if not resource_mutexes[resource].acquire(blocking=False):
                return False
            locked_resources.append(resource)
            resource_availability[resource] -= amount
    return True

def release_locked_resources(locked_resources, resource_usage):
    for resource in locked_resources:
        resource_mutexes[resource].release()
        resource_availability[resource] += resource_usage[resource]

def execute_task(task, stop_event):
    timer = time.time()
    while task.remaining_time > 0 and not stop_event.is_set():
        task.remaining_time -= 1
        time.sleep(1)
    print(f"Task {task.name} processed in {time.time() - timer:.2f} seconds")

def processor_worker(processor, stop_event, scheduling_algo):
    while not stop_event.is_set():
        try:
            task = processor.ready_queue.get(timeout=1)
        except queue.Empty:
            continue

        locked_resources = []
        if not lock_resources(task, locked_resources):
            release_locked_resources(locked_resources, task.resource_usage)
            if scheduling_algo == 'EDF':
                edf_waiting_queue.put(task)
            elif scheduling_algo == 'RMS':
                rms_waiting_queue.append(task)
            processor.ready_queue.task_done()
            continue

        processor.running_task = task
        execute_task(task, stop_event)

        release_locked_resources(locked_resources, task.resource_usage)
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
    if alg == 'EDF':
        while not edf_waiting_queue.empty():
            task = edf_waiting_queue.get()
            p = processors[task.processor_id]
            if is_task_schedulable(task, p):
                p.ready_queue.put(task)
                p.utilization += (task.execution_time / task.period)
            else:
                edf_waiting_queue.put(task)
                break
    elif alg == 'RMS':
        while rms_waiting_queue:
            task = rms_waiting_queue.popleft()
            p = processors[task.processor_id]
            if is_task_schedulable(task, p):
                p.ready_queue.put(task)
                p.utilization += (task.execution_time / task.period)
            else:
                rms_waiting_queue.append(task)
                break

def update_utilization(processors):
    for p in processors:
        p.utilization_history.append(p.utilization)

def check_termination_condition(processors):
    return all(p.ready_queue.empty() and p.running_task is None for p in processors) and edf_waiting_queue.empty() and not rms_waiting_queue

def main_thread(processors, stop_event, scheduling_algo):
    for p in processors:
        t = threading.Thread(target=processor_worker, args=(p, stop_event, scheduling_algo))
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

def display_status(processors):
    resource_status = ' '.join([f"{res}:{count}" for res, count in resource_availability.items()])
    edf_queue = ', '.join([t.name for t in list(edf_waiting_queue.queue)])
    rms_queue = ', '.join([t.name for t in list(rms_waiting_queue)])
    print(f"Resources: {resource_status}")
    print(f"Waiting Queue EDF: [{edf_queue}]")
    print(f"Waiting Queue RMS: [{rms_queue}]")
    for processor in processors:
        print(f"CPU{processor.processor_id + 1}:")
        print(f"CPU Utilization: {(processor.utilization / 1.0) * 100:.2f}%")
        ready_queue = [f"{t.name}:{t.repeat_count}" for t in list(processor.ready_queue.queue)]
        print(f"Ready Queue[ {', '.join(ready_queue)} ]")
        print(f"Running Task: {processor.running_task.name if processor.running_task else 'idle'}")

tasks = [
        Task('T1', 50, 2, {'R1': 1, 'R2': 0, 'R3': 0}, 0, 4),
        Task("T1", 50, 2, {'R1': 1, 'R2': 0, 'R3': 0}, 0, 4),
        Task("T2", 70, 3, {'R1': 0, 'R2': 2, 'R3': 0}, 1, 5),
        Task("T3", 30, 1, {'R1': 0, 'R2': 0, 'R3': 1}, 2, 6),
        Task("T4", 50, 2, {'R1': 1, 'R2': 1, 'R3': 0}, 0, 3),
        Task("T5", 60, 3, {'R1': 0, 'R2': 2, 'R3': 1}, 1, 2),
    ]
alg = 'EDF'
resources = list(map(int, input("Enter Resources: ").split()))

for index, resource in enumerate(resources):
    resource_name = f"R{index + 1}"
    resource_mutexes[resource_name] = threading.Lock()
    resource_availability[resource_name] = resource

processors = [Processor(i) for i in range(3)]

assign_tasks(tasks, processors, alg)

for task in tasks:
    deadlines = [task.period * i for i in range(1, task.repeat_count + 1)]
    print(f"{task.name} Deadlines: {', '.join(map(str, deadlines))}")

stop_event = threading.Event()
scheduler_thread = threading.Thread(target=main_thread, args=(processors, stop_event, alg))
scheduler_thread.start()

try:
    while scheduler_thread.is_alive():
        display_status(processors)
        time.sleep(1)
except KeyboardInterrupt:
    stop_event.set()

scheduler_thread.join()

display_status(processors)