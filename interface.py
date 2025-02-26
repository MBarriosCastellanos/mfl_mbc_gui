#%% ========================================================================
# Importación de librerías principales
# ==========================================================================
import tkinter as tk                # GUI toolkit
from tkinter import font, ttk       # Fonts and combobox    
# Integración de matplotlib en Tkinter
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg 
from PIL import Image, ImageTk      # Manejo de imágenes
import numpy as np                  # Procesamiento numérico
from tkinter import font, ttk
# procesamiento de datos
import multiprocessing
from multiprocessing import Process, Queue, Event, Manager
from queue import Empty  # Para capturar la excepción en get(timeout=...)
from objects import DataAdquisition, DataSaver, DataAlarm
from functions import *


#%% ========================================================================
# Interface Principal
# ==========================================================================
class MainInterFace:
  """Clase principal para la interfaz gráfica de usuario"""
  def __init__(self, root):
    # Initialize main window and configure fonts
    self.root = root                            # Ventana principal
    self.root.title("Adquisición de Datos MFL") # Título de la ventana
    self.setup_fonts()                          # Configurar fuentes

    # inicialización de colas, eventos y procesos
    self.queue_save = None        # Cola para guardar datos
    self.queue_plot = None        # Cola para graficar datos
    self.queue_process = None     # Cola para alarama de datos
    self.stop_event = None        # Evento de parada
    self.data_adquisition = None  # Proceso de adquisición de datos
    self.data_saver = None        # Proceso de guardado de datos
    self.data_plot = None         # Datos para graficar
    self.data_process = None      # Proceso de alarma de datos

    # banderas para ejecutar Procesos
    self.enable_save = Event()    # Activar/desactivar guardado
    self.enable_plot = Event()    # Activar/desactivar gráficos
    self.enable_process = Event() # Activar/desactivar alarma

    # Memoria compartida para alarmas en multiproceso
    self.manager = Manager()      # Variable compartida entre procesos
    self.shared_alarms = self.manager.dict()  # Estatus alamra de los 30 sensores
    self.shared_alarms.update({ i:np.array([[0]] * 10) for i in range(3) })              

    # Initialize variables de los gráficos
    self.time_scale = tk.IntVar(value=4)    # Ventana de tiempo inicial  
    self.mag_min = tk.DoubleVar(value=2000) # Límite inferior inicial
    self.mag_max = tk.DoubleVar(value=3000) # Límite superior inicial
    self.file_name = tk.StringVar(value="") # Nombre de archivo para guardar
    self.plot_type = tk.StringVar(value="Scan A") # Tipo de gráfico inicial

    # Bind the Combobox selection change event to the switching method
    self.plot_type.trace_add("write", self.switch_plot)

    # Bind the time_scale variable to the validate_time_scale method
    self.time_scale.trace_add("write", self.validate_time_scale)

    # Configuraciones iniciales
    self.sampling_rate = 300      # Frecuencia de muestreo de los sensores
    self.auto_scale = 1           # Autoescala activada por defecto
    self.hex_color = "#CDCDCD"    # color default de botón desactivado
    
    # Reemplazar la variable Tkinter con una compartida
    self.alarm_threshold = multiprocessing.Value('d', 40.0)
    self.alarm_threshold_tk = tk.DoubleVar(value=40.0)  # Usar StringVar en lugar de DoubleVar
    
    # Configuración inicial de la GUI
    self.create_frames()          # Crear estructura de la interfaz
    self.create_plot_controls()   # Crear Controles del gráfico
    self.create_plot_main()       # Crear Gráfico principal
    self.create_plot_alarm()      # Crear Gráfico de alarmas
    self.create_control_buttons() # Botones de control
    self.create_image_display()   # Imagen estática

    # Start the data acquisition and plot update
    self.update_plot_real_time()  # Update every 100 ms for smooth real-time effect

  def setup_fonts(self):
    """Configura la fuente predeterminada para todos los widgets."""
    default_font = font.nametofont("TkDefaultFont")
    default_font.configure(size=28)
    self.root.option_add("*Font", default_font)

  def validate_time_scale(self, *args):
    """Valida el valor de time_scale y lo ajusta si es necesario."""
    max_time = 10 if self.plot_type.get() == "Scan A" else 4
    if self.time_scale.get() > max_time:
      self.time_scale.set(max_time)

  def create_frames(self):
    """Organiza la GUI en frames contenedores.
    Relación de Contenedores:
    root
    ├── plot_frame (LEFT)
    │   ├── plot_data_frame (TOP) -> Controles gráfico
    │   ├── plot_graf_frame (LEFT) -> Gráfico principal
    │   └── plot_graf_alarm (RIGHT) -> Alarmas
    └── right_frame (RIGHT)
        ├── control_frame (TOP) -> Botones de control
        └── image_frame (TOP) -> Imagen estática
    """
    # ---------------------------------------------------------------------
    # Estructura Jerárquica de la GUI (root = Ventana principal)
    # ---------------------------------------------------------------------
    # | +-----------------------------------+ +----------------- ------+ |
    # | |      self.plot_frame              | |    self.right_frame    | |
    # | | +-------------------------------+ | |------------------------+ |
    # | |    self.plot_data_frame           | |    self.control_frame    | 
    # | | +-----------------+ +-----------+ | | +----------------------+ | 
    # | | |plot_graf_frame |plot_graf_alarm | |  self.image_frame        |
    # +----------------------------------------------------------------+ |

    self.plot_frame = tk.Frame(self.root)   # Frame principal
    self.plot_frame.pack(side=tk.LEFT, padx=10, pady=10)

    self.right_frame = tk.Frame(self.root)  # frame lado derecho
    self.right_frame.pack(side=tk.RIGHT, padx=8, pady=8)

    self.plot_data_frame = tk.Frame(self.plot_frame)# frame lado izquierdo
    self.plot_data_frame.pack(side=tk.TOP, pady=3)

    self.plot_graf_frame = tk.Frame(self.plot_frame) # grafico de datos
    self.plot_graf_frame.pack(side=tk.LEFT, pady=7, padx=7)

    self.plot_graf_alarm = tk.Frame(self.plot_frame)  # grafico de alarmas
    self.plot_graf_alarm.pack(side=tk.RIGHT, pady=7, padx=3)

    self.control_frame = tk.Frame(self.right_frame) #grafico de control
    self.control_frame.pack(side=tk.TOP, pady=5)

    self.image_frame = tk.Frame(self.right_frame) # imagen estatica
    self.image_frame.pack(side=tk.TOP, pady=5)

  def create_plot_controls(self):
    """" Crea los controles para el gráfico principal """
    # Control para seleccionar el tipo de scan (grafico) a ser usado
    ttk.Combobox(self.plot_data_frame, textvariable=self.plot_type, 
                  values=["Scan A", "Scan C"], state="readonly").grid(
                    row=0, column=0, columnspan=2, padx=5)

    # Control de la ventana de tiempo
    tk.Label(                   # Etiqueta para la ventana de tiempo
      self.plot_data_frame, text="Ventana de tiempo").grid(
      row=1, column=0, padx=5, columnspan=2, sticky='ew')
    tk.Entry(                   # Entrada para la ventana de tiempo
      self.plot_data_frame, width=10, textvariable=self.time_scale).grid(
      row=2, column=0, padx=5, columnspan=2, sticky='ew')

    # Botón para autoescalar el grafico
    self.auto_scale_button = tk.Button(self.plot_data_frame, 
                                       text="Ajustar Escala", bg=self.hex_color,
                                        command=self.toggle_autoscale)
    self.auto_scale_button.grid(
      row=0, column=2, columnspan=2, padx=5, sticky='w')

    # Limites manuales de la escala
    self.scale_widgets_state = 'disabled'
    tk.Label(               # Etiqueta para los limites de la escala
      self.plot_data_frame, text="Limites flujo magnetico [Gauss]"
      ).grid(row=1, column=2, columnspan=4, padx=5, sticky='ew')
    
    # Configuración del limite inferior de la grafica
    tk.Label(                     # Etiqueta para el limite inferior
      self.plot_data_frame, text="Min"  # Texto de la etiqueta
      ).grid(row=2, column=2, padx=5)   # Posición de la etiqueta
    self.entry_ymin = tk.Entry(  # Entrada para el limite inferior
      self.plot_data_frame, width=10,   # Ubicar en el frame
      textvariable=self.mag_min,        # Variable asignada
      state=self.scale_widgets_state)   # Estado de la entrada
    self.entry_ymin.grid(row=2, column=3, padx=5)

    # Configuración del limite superior de la grafica
    tk.Label(                   # Etiqueta para el limite superior
      self.plot_data_frame, text="Max"  # Texto de la etiqueta
      ).grid(row=2, column=4, padx=5)   # Posición de la etiqueta
    self.entry_ymax = tk.Entry( # Entrada para el limite superior
      self.plot_data_frame, width=10,   # Ubicar en el frame
      textvariable=self.mag_max,        # Variable asignada  
      state=self.scale_widgets_state)   # Estado de la entrada
    self.entry_ymax.grid(row=2, column=5, padx=5)

  def create_control_buttons(self):
    """Crea los botones de control en el frame de control"""
    # --------------------------------------------------------------------
    # Estructura Grid de plot_data_frame (6 columnas)
    # +------------------------------------------------------------------+
    # | [Row 0]                                                           |
    # | +----------------+ +----------------+ +-------------------------+ |
    # | |  Combobox      | |                | | Botón Ajustar Escala    | |
    # | | (cols 0-1)     | |      -         | | (cols 2-3)              | |
    # | +----------------+ +----------------+ +-------------------------+ |
    # | [Row 1]                                                           |
    # | +----------------+ +----------------+ +-------------------------+ |
    # | | Label Ventana  | | Label Límites  | |                         | |
    # | | Tiempo         | | Mag (cols 2-5) | |                         | |
    # | | (cols 0-1)     | |                | |                         | |
    # | +----------------+ +----------------+ +-------------------------+ |
    # | [Row 2]                                                           |
    # | +----------------+ +-------+ +-------+ +-------+ +-------+ +-----+ |
    # | | Entry Tiempo   | | Min   | | Entry | | Max   | | Entry | |     | |
    # | | (cols 0-1)     | | (col2)| | (col3)| | (col4)| | (col5)| |     | |
    # | +----------------+ +-------+ +-------+ +-------+ +-------+ +-----+ |
    # Botón de Conección principal ---------------------------------------
    self.btn_conect = tk.Button(self.control_frame, 
                                text="Conectar", bg=self.hex_color,
                                command=self.toggle_conect, width=13,)
    self.btn_conect.grid(row=0, column=0, padx=5, columnspan=6, sticky='ew')
    # Botón para activar la alarma ----------------------------------------
    self.btn_alarm = tk.Button(self.control_frame, 
                                text="Alarma", bg=self.hex_color,
                                command=self.toggle_alarm, width=9, )
    self.btn_alarm.grid(row=1, column=0, padx=3)

    # Configuración de los botones de ajuste de alarma---------------------
    button_configs = [
        {"text": "-5", "delta": -5, "column": 1, },
        {"text": "-1", "delta": -1, "column": 2, },
        {"text": "+1", "delta": +1, "column": 4, },
        {"text": "+5", "delta": +5, "column": 5, }
    ]

    # Crear todos los botones de ajuste de la alarma------------------------
    for config in button_configs:
      btn = tk.Button( self.control_frame, text=config["text"],
        bg=self.hex_color,
        command=lambda delta=float(config["text"]): self.adj_alarm(delta),
        width=4,
      )
      btn.grid(row=1, column=config["column"], padx=0)

    # Configuración de la entrada de la alarma ------------------------------
    self.entry_alarm = tk.Entry(self.control_frame, width=5, 
                                textvariable=self.alarm_threshold_tk)
    # Añadir un trace para actualizar la variable compartida
    self.alarm_threshold_tk.trace_add("write",  # Modificar la variable compartida
                                      self.update_alarm_threshold)
    self.entry_alarm.grid(row=1, column=3, padx=5)  # Ubicar en el frame
    self.entry_alarm.config(state="disable")        # Desactivar la entrada

    # save data ----------------------------------------------------------------
    self.btn_save = tk.Button(self.control_frame, text="Guardar", 
                              bg=self.hex_color, command=self.toggle_save, width=9)
    self.btn_save.grid(row=2, column=0, padx=5)

    self.label_save = tk.Label(self.control_frame, text="Archivo")
    self.label_save.grid(row=2, column=1, padx=5, columnspan=2)
    self.save_entry = tk.Entry(self.control_frame, 
                               width=15, textvariable=self.file_name)
    self.save_entry.grid(row=2, column=3, pady=5, columnspan=3)

  def toggle_autoscale(self):
    """Activa o desactiva la autoescala del gráfico principal."""
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
    """Activa o desactiva la adquisición de datos."""
    # Conectar datps
    if self.btn_conect.config('text')[-1] == "Conectar":
      # configurar el botón de conexión
      self.btn_conect.config(text="Conectado", bg="green", fg="white")
      # Crear nuevas colas y evento
      self.queue_save = Queue()       # Cola para guardar datos
      self.queue_plot = Queue()       # Cola para graficar datos
      self.queue_process = Queue()    # Cola para alarma de datos  
      self.stop_event = Event()       # Evento de parada
      self.enable_plot.set()          # Activar gráficos
      
      # Crear nuevas instancias de procesos
      self.data_adquisition = DataAdquisition( # Proceso de adquisición de datos
          self.queue_save,    # Cola para guardar datos
          self.queue_plot,    # Cola para graficar datos
          self.queue_process, # Cola para alarma de datos
          self.stop_event,    # Evento de parada
          enable_plot=self.enable_plot,       # Activar/desactivar gráficos
          enable_process=self.enable_process, # Activar/desactivar alarma
          enable_save=self.enable_save        # Activar/desactivar guardado
      )

      # Iniciar procesos
      self.data_adquisition.start() # Iniciar proceso de adquisición de datos

    # Desconectar datos
    else:
      # Configurar el botón de conexión
      self.btn_conect.config(text="Conectar", bg=self.hex_color, fg="black")

      ## Detener procesos de alarma y guardado si están activos
      #if self.enable_process.is_set():
      #  self.btn_alarm.invoke()  # Simula la pulsación del botón de alarma
      #if self.enable_save.is_set():
      #  self.btn_save.invoke()   # Simula la pulsación del botón de guardado

      # Detener procesos
      self.enable_plot.clear() # Señalar a DataAdquisition parar de plotear
      self.stop_event.set()
      
      # Esperar a que terminen
      if self.data_adquisition is not None:
          self.data_adquisition.join()
      
      # Limpiar referencias
      self.data_adquisition = None    # Proceso de adquisición de datos
      self.data_saver = None          # Proceso de guardado de datos
      self.queue_save = None          # Cola para guardar datos
      self.queue_plot = None          # Cola para graficar datos
      self.queue_process = None       # Cola para alarma de datos
      self.stop_event = None          # Evento de parada

  def toggle_alarm(self):
    """ Activa o desactiva la alarma de datos."""
    if self.btn_alarm.config('text')[-1] == "Alarma":
      self.btn_alarm.config(text="Al. Activa", bg="green", fg="white")
      self.enable_process.set()   # Activar proceso de alarma de datos
      self.data_process = DataAlarm(  # Proceso de alarma de datos
                                    self.queue_process,   # Cola para alarma de datos
                                    self.enable_process,  # Evento de inicio/parada
                                    self.alarm_threshold, # Umbral de alarma
                                    self.shared_alarms    # Variable compartida
                                    )
      self.data_process.start()     # Iniciar proceso de alarma de datos
    else:
      self.btn_alarm.config(text="Alarma", bg=self.hex_color, fg="black")
      self.enable_process.clear()       # Señala a DataSaver que debe salir
      while not self.queue_process.empty():
        self.queue_process.get_nowait()
      if self.data_process is not None: # Si el proceso existe
        self.data_process.join()        # Espera a que finalice
        self.data_process = None        # Limpiar referencia
      #self.manager.shutdown()  # Cerrar el Manager al detener el proceso

  def toggle_save(self):
    """Activa o desactiva el guardado de datos."""
    if self.btn_save.config('text')[-1] == "Guardar": # Guardar datos
      self.btn_save.config(text="Guardando", bg="green", fg="white")  # Configurar botón
      self.enable_save.set()        # Activar proceso de guardado
      self.data_saver = DataSaver(self.queue_save,  # Proceso de guardado de datos
        self.enable_save, name=str(self.file_name.get())  # Nombre de archivo
      )
      self.data_saver.start()     # Iniciar proceso de guardado
    else:
      self.btn_save.config(text="Guardar", bg=self.hex_color, fg="black")
      self.enable_save.clear()  # Señala a DataSaver que debe salir
      if self.data_saver is not None: # Si el proceso existe
        self.data_saver.join()        # Espera a que finalice
        self.data_saver = None        # Limpiar referencia

  def create_plot_main(self, scan_type="Scan A"):
    """crea el gráfico principal en el frame plot_graf_frame"""
    if scan_type == "Scan A":  # Seleccionar el tipo de gráfico
      create_plot = ScanA_create  # Crear gráfico Scan A
    else:
      create_plot = ScanC_create  # Crear gráfico Scan C

    time_scale = verify_empty(self.time_scale, 4)  # Obtener la escala de tiempo
    mag_min = verify_empty(self.mag_min, 2000)     # Obtener el límite inferior
    mag_max = verify_empty(self.mag_max, 3000)     # Obtener el límite superior

    # Obtener la ventana de tiempo, Configuración de la figura y ejes
    self.fig, self.ax = create_plot(mag_min,  mag_max, time_scale)

    self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_graf_frame)
    self.canvas.draw()
    self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

  def create_plot_alarm(self):
    """Crea el gráfico de alarmas en el frame plot_graf_alarm"""
    # Configuración de la figura y ejes
    self.fig2, self.ax2, self.X_alarm, self.Y_alarm = Alarm_create()

    # Crear el gráfico de alarmas
    self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.plot_graf_alarm)
    self.canvas2.draw() # Dibujar el gráfico
    self.canvas2.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

  def update_plot_main(self):
    """Actualiza el gráfico principal con los datos de la cola."""
    # verificación de la escala de tiempo	

    time_scale = verify_empty(self.time_scale, 4)  # Obtener la escala de tiempo
    mag_min = verify_empty(self.mag_min, 2000)     # Obtener el límite inferior
    mag_max = verify_empty(self.mag_max, 3000)     # Obtener el límite superior

    # Actualizar el gráfico principal con los datos de la cola
    if self.queue_plot is not None: # Si hay datos en la cola
      while True:             # Mientras haya datos en la cola
        try:                # Intentar obtener datos de la cola 
          data = self.queue_plot.get_nowait()   # Obtener datos de la cola
          data_array = np.column_stack(         # Convertir datos a array
              [np.array(data[key])[-10:] for key in sorted(data.keys())]
          )
          
          # Calcular en numero e muestras en el eje del tiempo
          max_samples = time_scale * self.sampling_rate

          # Actualizar los datos del gráfico
          if self.data_plot is None:  # Si no hay datos, asignar los nuevos
            self.data_plot = data_array
          else:                       # Si hay datos, apilarlos
            self.data_plot = np.vstack((self.data_plot, data_array))

          # Limitar el número de muestras en el eje del tiempo
          if len(self.data_plot) > max_samples:
            self.data_plot = self.data_plot[-max_samples:]
          
          #Seleccionar el tipo de gráfico
          if self.plot_type.get() == "Scan A":
            update_plot = ScanA_update  # Actualizar gráfico Scan A
          else:
            update_plot = ScanC_update  # Actualizar gráfico Scan C
          
          # Actualizar el gráfico principal
          self.fig, self.ax = update_plot(self.fig, self.ax, 
            mag_min, mag_max, time_scale, 
            self.data_plot, self.sampling_rate, self.auto_scale
          )
        except Empty:   # Si no hay datos en la cola, salir del bucle
          break         # Salir del bucle while
    self.canvas.draw() 

  def update_plot_alarm(self):
    """Actualiza el gráfico de alarmas con los datos de la cola."""
    try:      # Intentar obtener datos del manager
      self.ax2 = Alarm_update(self.ax2, self.X_alarm, self.Y_alarm,
        self.shared_alarms) # Actualizar el gráfico de alarmas
      self.canvas2.draw()   # Dibujar el gráfico de alarmas
    except Empty:
      pass  # No hay datos en la cola, no hacer nada  
    except Exception as e: 
      print(f"Error en update_plot_alarm: {e}")
      

  def update_plot_real_time(self):
    """Actualiza los gráficos en tiempo real."""
    self.update_plot_main() # Actualizar el gráfico principal
    if self.enable_process.is_set():  # Si la alarma está activada
      self.update_plot_alarm()        # Actualizar el gráfico de alarmas
    self.root.after(33,               # Actualizar cada 33 ms (30 Hz)   
                    self.update_plot_real_time)  

  def update_alarm_threshold(self, *args):
    """Actualiza el valor de la alarma en la variable compartida."""
    try: # Intentar obtener el nuevo valor de la alarma
      new_value = float(self.alarm_threshold_tk.get())  # Obtener el nuevo valor
      self.alarm_threshold.value = new_value            # Actualizar la variable compartida
    except ValueError:                  # Si hay un error
      pass  # Ignora valores inválidos 
      
  def create_image_display(self):
    """Crea un marco para mostrar una imagen estática."""
    img_path = "figures/mfl_sup.jpg"  # Ensure this path is correct
    img = Image.open(img_path)        # Open the image
    img = img.resize((730,            # Resize the image
                      int((730 / float(img.size[0])) * img.size[1])), 
                      Image.Resampling.LANCZOS)
    img = ImageTk.PhotoImage(img)     # Convert the image to PhotoImage
    
    img_label = tk.Label(self.image_frame, image=img) # Create a label
    img_label.pack(side=tk.TOP, pady=2)               # Pack the label
    img_label.image = img                             # Save a reference

  def adj_alarm(self, delta):
    """Ajusta el valor de la alarma en la entrada de la alarma."""
    current_value = self.alarm_threshold_tk.get()       # Obtener el valor actual
    self.alarm_threshold_tk.set(current_value + delta)  # Ajustar el valor   

  def switch_plot(self, *args):
    """Switch between ScanA and ScanC plots based on Combobox selection."""
    plot_type = self.plot_type.get()                  # Obtener el tipo de gráfico

    # Parar la actualización de los gráficos
    if self.data_adquisition is not None:             # Si hay datos de adquisición
      self.enable_plot.clear()                        # Detener la actualización
    
    # Limpieza de los gráficos anteriores
    for ax in self.ax:                                # Limpiar los ejes
      ax.clear()
    self.fig.clear()                                  # Limpiar la figura

    # Destruir el widget de la figura
    if hasattr(self, 'canvas'):
        self.canvas.get_tk_widget().destroy()
    
    # Crear un nuevo gráfico principal basado en el tipo de gráfico
    if plot_type == "Scan A":
        self.create_plot_main(scan_type="Scan A")
    elif plot_type == "Scan C":
        time_scale = min(self.time_scale.get(), 4)
        self.time_scale.set(time_scale)
        self.create_plot_main(scan_type="Scan C")

    # Reinicio de la actualización de los gráficos
    if self.data_adquisition is not None:
      self.enable_plot.set()


if __name__ == "__main__":  # Si se ejecuta el script principal
  multiprocessing.freeze_support()    # Congelar soporte para Windows
  root = tk.Tk()                      # Crear la ventana principal  
  app = MainInterFace(root)           # Crear la interfaz principal  
  root.mainloop()                     # Iniciar el bucle principal
