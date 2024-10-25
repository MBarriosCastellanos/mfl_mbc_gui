import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Parameters
window_size = 200
num_signals = 30
min_value = 1200
max_value = 4096
update_interval = 10  # Number of frames between each plot update

# Initialize data window
data_window = np.empty((0, num_signals))

# Flags to control the data generation
running = True

# Function to generate random row
def generate_random_row():
  return np.random.randint(min_value, max_value + 1, size=(1, num_signals))

# Function to update data window
def update_data_window(data_window):
  new_row = generate_random_row()
  data_window = np.vstack([data_window, new_row])  # Add new row
  if data_window.shape[0] > window_size:
    data_window = data_window[1:, :]  # Keep window size <= 1500
  return data_window

# Function to handle toggle button
def toggle_data():
  global running
  if running:
    running = False
    toggle_button.config(text="Desconectar")
  else:
    running = True
    toggle_button.config(text="Stop")

# Create figure and axes for plotting
fig, axes = plt.subplots(3, 1, figsize=(10, 8))  # 3 subplots

# Initialize line objects for each axis
lines = []
for i in range(3):
  line, = axes[i].plot([], [], lw=1)  # Empty line object
  lines.append(line)
  axes[i].set_ylim(min_value, max_value)  # Set fixed Y-axis range for clarity

# Function to update the line data
def init():
  for ax in axes:
    ax.set_xlim(0, window_size)  # Set X-axis limits

  return lines

def animate(frame):
  global data_window, running
  if running:
    data_window = update_data_window(data_window)

  # Update plot only every 10 frames
  if frame % update_interval == 0:
    # Clear each subplot
    for ax in axes:
      ax.clear()

    # Plot 10 signals in each of the 3 subplots
    for i in range(3):
      for j in range(10):
        axes[i].plot(data_window[:, i * 10 + j], label=f's{j + 1}')
      axes[i].legend(loc='upper right')

# Function to start the animation
def start_animation():
  ani = FuncAnimation(fig, animate, interval=100)
  canvas.draw()

# Create tkinter window
root = tk.Tk()
root.title("Data Generator Control")

# Add matplotlib figure to tkinter window
canvas = FigureCanvasTkAgg(fig, master=root)  # A tk.DrawingArea.
canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

# Create toggle button for start/stop functionality
font_settings = ("Helvetica", 16)  # Font family, size
toggle_button = tk.Button(root, text="Desconectar", 
  command=toggle_data, width=20, height=3, font=font_settings)
toggle_button.pack(side=tk.LEFT)

# Start the animation
start_animation()

# Start the tkinter main loop
root.mainloop()
