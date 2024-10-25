#%%
import numpy as np
import time
import threading
from queue import Queue

#%%
# Constants
NUM_SENSOR_GROUPS = 3
SENSORS_PER_GROUP = 10
SAMPLE_RATE = 300  # Samples per second per sensor
ACQUISITION_DURATION = 5  # Duration in seconds for simulation

# Define a function to simulate data acquisition for a set of sensors
def simulate_sensor_group(sensor_group_id, sensor_data_queues, stop_event):
    print(f"Starting data acquisition for sensor group {sensor_group_id}")
    
    while not stop_event.is_set():
        for sensor_id in range(SENSORS_PER_GROUP):
            # Simulate data generation for each sensor
            sample = np.random.rand()  # Replace with actual signal generation
            sensor_data_queues[sensor_group_id][sensor_id].put(sample)
        
        # Sleep for the sampling interval (1 / SAMPLE_RATE)
        time.sleep(1 / SAMPLE_RATE)
    
    print(f"Stopping data acquisition for sensor group {sensor_group_id}")

# Main function
def main():
    # Create a queue for each sensor to store data
    sensor_data_queues = [[Queue() for _ in range(SENSORS_PER_GROUP)] for _ in range(NUM_SENSOR_GROUPS)]
    
    # Create an event to stop the acquisition
    stop_event = threading.Event()

    # Create threads for each sensor group
    threads = []
    for group_id in range(NUM_SENSOR_GROUPS):
        thread = threading.Thread(target=simulate_sensor_group, args=(group_id, sensor_data_queues, stop_event))
        threads.append(thread)
        thread.start()

    # Run the acquisition for the specified duration
    time.sleep(ACQUISITION_DURATION)
    
    # Stop the acquisition
    stop_event.set()

    # Wait for all threads to finish
    for thread in threads:
        thread.join()

    # Retrieve and print the acquired data (for demonstration purposes)
    for group_id in range(NUM_SENSOR_GROUPS):
        print(f"\nSensor group {group_id}:")
        for sensor_id in range(SENSORS_PER_GROUP):
            # Fetch data from the queue
            sensor_data = []
            while not sensor_data_queues[group_id][sensor_id].empty():
                sensor_data.append(sensor_data_queues[group_id][sensor_id].get())
            print(f"  Sensor {sensor_id}: {sensor_data[:5]} ...")  # Show the first 5 samples for brevity

if __name__ == "__main__":
    main()
