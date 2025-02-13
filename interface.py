#%%
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import numpy as np
import matplotlib.pyplot as plt
from tkinter import font, ttk
# procesamiento de datos
import multiprocessing
from multiprocessing import Process, Queue, Event
from queue import Empty  # Para capturar la excepción en get(timeout=...)
from objects import DataAdquisition, DataSaver, DataAlarm
from matplotlib.colors import LinearSegmentedColormap
colors = [(0,    (1, 1, 1)),       # Green
          (1,    (0.5,     0, 0))]      # red
cmap1 = LinearSegmentedColormap.from_list('custom_cmap', colors, 
                                          N=2
                                          )

def generate_random_row():
  sample1 = np.random.rand(1, 10)*(4096 - 1024) + 1024
  sample2 = np.random.rand(1, 10)*(4096 - 1024) + 1024
  sample3 = np.random.rand(1, 10)*(4096 - 1024) + 1024
  return np.c_[sample1, sample2, sample3]

#%%
class MainInterFace:
  def __init__(self, root):
    # Initialize main window and configure fonts
    self.root = root
    self.root.title("Adquisición de Datos MFL")
    self.setup_fonts()

    # inicialización de colas, eventos y procesos
    self.queue_save = None
    self.queue_plot = None
    self.queue_process = None
    self.stop_event = None
    self.data_adquisition = None
    self.data_saver = None
    self.data_plot = None

    # banderas para ejecutar Procesos
    self.enable_save = Event()
    self.enable_plot = Event()
    self.enable_process = Event()

    self.data_buffers = None
    
    # Initialize variables
    self.time_scale = tk.IntVar(value=5)
    self.mag_min = tk.DoubleVar(value=0)
    self.mag_max = tk.DoubleVar(value=6000)
    self.file_name = tk.StringVar(value="")
    self.plot_type = tk.StringVar(value="Señales")
    self.sampling_rate = 300
    self.auto_scale = 1
    self.hex_color = "#CDCDCD"  # Default button color
    self.labels = [f's{i+1}' for i in range(10)]
    
    # Set up the main GUI layout
    self.create_frames()
    self.create_plot_controls()
    self.create_plot_area()
    self.create_alarm_area()
    self.create_control_buttons()
    self.create_image_display()

    # Initialize the data matrix to accumulate samples
    self.start_iteration = 0 # Empty matrix with 10 columns for 10 signals

    # Start the data acquisition and plot update
    self.update_plot_real_time()# Update every 100 ms for smooth real-time effect

  def setup_fonts(self):
    # Configure the default font size and style
    default_font = font.nametofont("TkDefaultFont")
    default_font.configure(size=28)
    self.root.option_add("*Font", default_font)

  def create_frames(self):
    # Define layout frames for organized widget arrangement
    self.plot_frame = tk.Frame(self.root)
    self.plot_frame.pack(side=tk.LEFT, padx=10, pady=10)

    self.right_frame = tk.Frame(self.root)
    self.right_frame.pack(side=tk.RIGHT, padx=8, pady=8)

    self.plot_data_frame = tk.Frame(self.plot_frame)
    self.plot_data_frame.pack(side=tk.TOP, pady=3)

    self.plot_graf_frame = tk.Frame(self.plot_frame)
    self.plot_graf_frame.pack(side=tk.LEFT, pady=7, padx=7)

    self.plot_graf_alarm = tk.Frame(self.plot_frame)
    self.plot_graf_alarm.pack(side=tk.RIGHT, pady=7, padx=3)

    self.image_frame = tk.Frame(self.right_frame)
    self.image_frame.pack(side=tk.TOP, pady=5)

    self.control_frame = tk.Frame(self.right_frame)
    self.control_frame.pack(side=tk.TOP, pady=5)

  def create_plot_controls(self):
    # Control for selecting plot type
    ttk.Combobox(self.plot_data_frame, textvariable=self.plot_type, 
                  values=["Señales", "Colormap"], state="readonly").grid(
                    row=0, column=0, columnspan=2, padx=5)

    # Time window control
    tk.Label(self.plot_data_frame, text="Ventana de tiempo").grid(row=1, column=0, padx=5, columnspan=2, sticky='ew')
    tk.Entry(self.plot_data_frame, width=10, textvariable=self.time_scale).grid(row=2, column=0, padx=5, columnspan=2, sticky='ew')

    # Button for autoscaling toggle
    self.auto_scale_button = tk.Button(self.plot_data_frame, text="Ajustar Escala", bg=self.hex_color,
                                        command=self.toggle_autoscale)
    self.auto_scale_button.grid(row=0, column=2, columnspan=2, padx=5, sticky='w')

    # Manual scale limits
    self.scale_widgets_state = 'disabled'
    tk.Label(self.plot_data_frame, text="Limites flujo magnetico [Gauss]"
             ).grid(row=1, column=2, columnspan=4, padx=5, sticky='ew')
    tk.Label(self.plot_data_frame, text="Min"
            ).grid(row=2, column=2, padx=5)
    self.entry_ymin = tk.Entry(self.plot_data_frame, width=10, textvariable=self.mag_min, 
             state=self.scale_widgets_state)
    self.entry_ymin.grid(row=2, column=3, padx=5)

    tk.Label(self.plot_data_frame, text="Max"
            ).grid(row=2, column=4, padx=5)
    self.entry_ymax = tk.Entry(self.plot_data_frame, width=10, textvariable=self.mag_max, 
             state=self.scale_widgets_state)
    self.entry_ymax.grid(row=2, column=5, padx=5)

  def toggle_autoscale(self):
    # Toggle autoscale for plot
    if self.auto_scale_button.config('text')[-1] == "Ajustar Escala":
      self.auto_scale_button.config(text="Autoescala")
      self.auto_scale = 0
      self.scale_widgets_state = 'normal'
    else:
      self.auto_scale_button.config(text="Ajustar Escala")
      self.auto_scale = 1
      self.scale_widgets_state = 'disable'
    
    # Enable or disable manual scale entries based on autoscale state
    self.entry_ymin.config(state=self.scale_widgets_state)
    self.entry_ymax.config(state=self.scale_widgets_state)
    #self.update_scale_widgets_state()

  def toggle_conect(self):
    # Toggle autoscale for plot
    if self.btn_conect.config('text')[-1] == "Conectar":
      self.btn_conect.config(text="Conectado", bg="green", fg="white")
      # Crear nuevas colas y evento
      self.queue_save = Queue()
      self.queue_plot = Queue()
      self.queue_process = Queue()
      self.stop_event = Event()

      self.enable_plot.set()
      
      # Crear nuevas instancias de procesos
      self.data_adquisition = DataAdquisition(
          self.queue_save, 
          self.queue_plot,
          self.queue_process,
          self.stop_event,
          enable_plot=self.enable_plot,
          enable_process=self.enable_process,
          enable_save=self.enable_save
      )

      # Iniciar procesos
      self.data_adquisition.start()

    else:
      self.btn_conect.config(text="Conectar", bg=self.hex_color, fg="black")

      # Detener procesos
      self.data_adquisition.enable_plot.clear()
      self.stop_event.set()
      
      # Esperar a que terminen
      if self.data_adquisition is not None:
          self.data_adquisition.join()
      
      # Limpiar referencias
      self.data_adquisition = None
      self.data_saver = None
      self.queue_save = None
      self.queue_plot = None
      self.queue_process = None
      self.stop_event = None

  def toggle_alarm(self):
    # Toggle autoscale for plot
    if self.btn_alarm.config('text')[-1] == "Alarma":
      self.btn_alarm.config(text="Alarma Activa", bg="green", fg="white")
    else:
      self.btn_alarm.config(text="Alarma", bg=self.hex_color, fg="black")

  def toggle_save(self):
    # Toggle autoscale for plot
    if self.btn_save.config('text')[-1] == "Guardar":
      self.btn_save.config(text="Guardando", bg="green", fg="white")
      self.enable_save.set()
      self.data_adquisition.enable_save.set()
      self.data_saver = DataSaver(self.queue_save, 
        self.enable_save, name=str(self.file_name.get())
      )
      self.data_saver.start()
    else:
      self.btn_save.config(text="Guardar", bg=self.hex_color, fg="black")
      self.data_adquisition.enable_save.clear()
      self.data_saver.run_event.clear()
      if self.data_saver is not None:
        self.enable_save.clear()  # Señala a DataSaver que debe salir
        self.data_saver.join()       # Espera a que finalice
        self.data_saver = None

  def create_plot_area(self):
    # Setup plot area with subplots
    self.fig, self.ax = plt.subplots(3, 1, 
                                     figsize=(6, 4), dpi=150, sharex=True)
    self.fig.subplots_adjust(left=0.12, right=0.86, top=0.93, 
                             bottom=0.1, hspace=0.07)
    
    self.ax[2].set_xlabel("tiempo [s]")
    for i in range(3):
      #self.ax[i].plot(t, signals.T)
      self.ax[2-i].set_ylabel(f"Cuerpo {i+1}")
      self.ax[2-i].set_ylim([self.mag_min.get(), self.mag_max.get()])
    self.ax[0].set_xlim([0, self.time_scale.get()])
    # Adding legend to axis 0, one label per row
    self.ax[0].legend(self.labels, loc='upper right', 
                bbox_to_anchor=(1.19, 0.5),  ncol=1, )

    self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_graf_frame)
    self.canvas.draw()
    self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

  def create_alarm_area(self):
    # Configuración de la figura y ejes
    self.fig2, self.ax2 = plt.subplots(3, 1, figsize=(1, 4), 
                                      dpi=150, sharex=True)
    self.fig2.subplots_adjust(left=0.3, right=0.9, top=0.93, 
                              bottom=0.1, hspace=0.007)

    # Preparación de datos para pcolormesh (necesitan ser 2D)
    x_edges = np.array([0.8, 1.2])  # Bordes en X (debe tener 1 elemento más que la dimensión de los datos)
    y_edges = np.linspace(0.3, 10.8, 11)  # 11 bordes para 10 celdas verticales
    X, Y = np.meshgrid(x_edges, y_edges)  # Crear mallas para pcolormesh
    Z = np.array([[0],[0],[0],[0],[1],[1],[0],[0],[1],[0]])

    for i in range(3):
      # Crear el gráfico de mapa de colores
      mesh = self.ax2[i].pcolormesh(X, Y, Z, shading='flat', cmap=cmap1)
      
      # Configuración de ejes (similar al original)
      self.ax2[i].set_ylabel(f"Cuerpo {i+1}")
      self.ax2[i].set_ylim([0.3, 10.8])
      self.ax2[i].set_yticks(np.linspace(1, 10, 10))  # Centros de las celdas
      self.ax2[i].set_yticklabels(self.labels, fontsize=8)
    self.ax2[i].set_xlim([0.8, 1.2])
    self.ax2[i].set_xticks([1])  # Centros de las celdas
    self.ax2[i].set_xticklabels([])  # Centros de las celdas
    self.ax2[i].set_xlabel("Alarmas")  # Centros de las celdas

    #self.ax2[i].set_yticklabels(self.labels, fontsize=8)


    self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.plot_graf_alarm)
    self.canvas2.draw()
    self.canvas2.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

  def update_plot(self):
    labels = [f's{i+1}' for i in range(10)]
    if self.queue_plot is not None:
      while True:
          try:
            data = self.queue_plot.get_nowait()
            data_array = np.column_stack(
                [np.array(data[key])[-10:] for key in sorted(data.keys())]
            )
            max_samples = self.time_scale.get() * self.sampling_rate
            if self.data_plot is None:
              self.data_plot = data_array
            else:
              self.data_plot = np.vstack((self.data_plot, data_array))
            if len(self.data_plot) > max_samples:
              self.data_plot = self.data_plot[-max_samples:]
            len_data = len(self.data_plot)
            t = np.linspace(0, len_data-1, num=len_data)/self.sampling_rate
            for i in range(3):
              while self.ax[2-i].lines:
                self.ax[2-i].lines[0].remove()
              self.ax[2-i].plot(t, self.data_plot[:, i*10: (i+1)*10])
              self.ax[2-i].set_xlim([0, self.time_scale.get()])
              if self.auto_scale==1:
                self.ax[2-i].set_ylim([self.data_plot.min(), self.data_plot.max()])
              else:
                self.ax[2-i].set_ylim([self.mag_min.get(), self.mag_max.get()])
            self.ax[0].legend(labels, loc='upper right', 
              bbox_to_anchor=(1.19, 0.5),  ncol=1, )
          except Empty:
            break
    self.canvas.draw() 
  
  def update_plot_real_time(self):
    self.update_plot()
    self.root.after(33, self.update_plot_real_time)  # Update every 33 ms for smooth real-time effect

  def create_control_buttons(self):
    # Button toggles for various control actions
    self.btn_conect = tk.Button(self.control_frame, text="Conectar", bg=self.hex_color,
      command=self.toggle_conect, width=13,)
    self.btn_conect.grid(row=0, column=0, padx=5, columnspan=3, sticky='ew')
    # alarm --------------------------------------------------------------------
    self.btn_alarm = tk.Button(self.control_frame, text="Alarma", bg=self.hex_color,
      command=self.toggle_alarm, width=13, )
    self.btn_alarm.grid(row=1, column=0, padx=5)

    self.label_alarm = tk.Label(self.control_frame, text="Umbral")
    self.label_alarm.grid(row=1, column=1, padx=5)
    self.entry_alarm = tk.Entry(self.control_frame, width=15)
    self.entry_alarm.grid(row=1, column=2, padx=5)

    # save data ----------------------------------------------------------------
    self.btn_save = tk.Button(self.control_frame, text="Guardar", bg=self.hex_color,
      command=self.toggle_save, width=13)
    self.btn_save.grid(row=2, column=0, padx=5)

    self.label_save = tk.Label(self.control_frame, text="Archivo")
    self.label_save.grid(row=2, column=1, padx=5)
    self.save_entry = tk.Entry(self.control_frame, width=15, textvariable=self.file_name)
    self.save_entry.grid(row=2, column=2, pady=5)

  def toggle_button(btn, text_active, text_inactive):
    if btn.config('text')[-1] == text_inactive:
      btn.config(text=text_active, bg="green", fg="white")
    else:
      btn.config(text=text_inactive, bg=self.hex_color, fg="black")
      
  def create_image_display(self):
    # Display static image in the right frame
    img_path = "mfl_sup.jpg"  # Ensure this path is correct
    img = Image.open(img_path)
    img = img.resize((730, int((730 / float(img.size[0])) * img.size[1])), Image.Resampling.LANCZOS)
    img = ImageTk.PhotoImage(img)
    
    img_label = tk.Label(self.image_frame, image=img)
    img_label.pack(side=tk.TOP, pady=2)
    img_label.image = img

if __name__ == "__main__":
  multiprocessing.freeze_support()
  root = tk.Tk()
  app = MainInterFace(root)
  root.mainloop()
