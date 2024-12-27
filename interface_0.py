#%% import numpy as np
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import numpy as np
import matplotlib.pyplot as plt
from tkinter import font
from tkinter import ttk

#%%
def create_interface():
  root = tk.Tk()
  root.title("Adquisición de Datos MFL")

  # Set default font size
  default_font = font.nametofont("TkDefaultFont")
  default_font.configure(size=28)
  root.option_add("*Font", default_font)
  large_font = ('Helvetica', 14)  # Change to any font and size you prefer

  def toggle_button(btn, text_active, text_inactive):
    if btn.config('text')[-1] == text_inactive:
      btn.config(text=text_active, bg="green", fg=hex_color)
    else:
      btn.config(text=text_inactive, bg=hex_color, fg="black")

  def update_plot():
    t = np.linspace(0, time_scale.get(), num=time_scale.get()*sampling_rate) 
    signals = np.random.randn(10, len(t))*(4000-1000) + 1000 
    for axis in ax:
      while axis.lines:
        axis.lines[0].remove()
      axis.plot(t, signals.T)
      if auto_scale==1:
        axis.set_ylim([signals.min(), signals.max()])
      else:
        axis.set_ylim([mag_min.get(), mag_max.get()])
    axis.set_xlim([0, time_scale.get()])
    canvas.draw()  

  def autoscale_widget(btn, text_active, text_inactive):
    if btn.config('text')[-1] == text_inactive:
      state = 'disabled'
      btn.config(text=text_active, bg="green", fg=hex_color)
      auto_scale = 1
    else:
      btn.config(text=text_inactive, bg=hex_color, fg="black")
      state = 'normal'
      auto_scale = 0
    label2.config(state=state)
    label3.config(state=state)
    label4.config(state=state)
    entry2.config(state=state)
    entry3.config(state=state)

  # Create frames for better layout organization ===========================
  plot_frame = tk.Frame(root)
  plot_frame.pack(side=tk.LEFT, padx=10, pady=10)

  right_frame = tk.Frame(root)
  right_frame.pack(side=tk.RIGHT, padx=8, pady=8)

  plot_data_frame = tk.Frame(plot_frame)
  plot_data_frame.pack(side=tk.TOP, pady=3)

  plot_graf_frame = tk.Frame(plot_frame)
  plot_graf_frame.pack(side=tk.TOP, pady=7)

  image_frame = tk.Frame(right_frame)
  image_frame.pack(side=tk.TOP, pady=5)

  control_frame = tk.Frame(right_frame)
  control_frame.pack(side=tk.TOP, pady=5)

  # Variables for entries ===================================================
  time_scale = tk.IntVar(value=5)
  mag_min = tk.DoubleVar(value=0)
  mag_max = tk.DoubleVar(value=6000)
  plot_type = tk.StringVar()
  sampling_rate = 300
  hex_color = f"#{205:02x}{205:02x}{205:02x}"  # Format: #RRGGBB
  auto_scale = 1  # Por defecto está desactivado (1)

  # plot frame data =========================================================
  
  combobox = ttk.Combobox(plot_data_frame, textvariable=plot_type, 
    values=["Señales", "Colormap"], state="readonly")
  combobox.set("Señales")  # Default selection
  combobox.grid(row=0, column=0, columnspan=2, padx=5)

  label1 = tk.Label(plot_data_frame, text="Ventana de tiempo")
  label1.grid(row=1, column=0, padx=5, columnspan=2, sticky='ew')
  entry1 = tk.Entry(plot_data_frame, width=10, textvariable=time_scale)
  entry1.grid(row=2, column=0, padx=5, columnspan=2, sticky='ew')
  
  auto_scale_button = tk.Button(plot_data_frame, text="Ajustar Escala", bg=hex_color,
     command=lambda: autoscale_widget(auto_scale_button , "Ajustar Escala", "Autoescala"), 
     )
  auto_scale_button.grid(row=0, column=2, columnspan=2, padx=5, sticky='w')

  btn_apply = tk.Button(plot_data_frame, text="Aplicar", 
                        command=update_plot,
                        bg=hex_color)
  btn_apply.grid(row=0, column=4, columnspan=2, padx=5, sticky='ew')

  label2 = tk.Label(plot_data_frame, text="Limites flujo magnetico [Gauss]")
  label2.grid(row=1, column=2, columnspan=4, padx=5, sticky='ew')
  label4 = tk.Label(plot_data_frame, text="Min")
  label4.grid(row=2, column=2, padx=5)
  entry2 = tk.Entry(plot_data_frame, width=10, textvariable=mag_min)
  entry2.grid(row=2, column=3, padx=5)
  label3 = tk.Label(plot_data_frame, text="Max")
  label3.grid(row=2, column=4, padx=5)
  entry3 = tk.Entry(plot_data_frame, width=10, textvariable=mag_max)
  entry3.grid(row=2, column=5, padx=5)

  state = 'disable'
  label2.config(state=state)
  label3.config(state=state)
  label4.config(state=state)
  entry2.config(state=state)
  entry3.config(state=state)

  # plot frame graphical interface =============================================
  fig, ax = plt.subplots(3, 1, figsize=(6, 4), dpi=150, sharex=True,
                          #constrained_layout=True
                          )
  fig.subplots_adjust(left=0.12, right=0.86, top=0.93, bottom=0.1, hspace=0.07)  
  #plt.subplots_adjust(vspace=0.1) 
  ax[0].set_title("Densididad de flujo magnetico [Gauss]")


  t = np.linspace(0, time_scale.get(), num=time_scale.get()*sampling_rate)
  signals = np.random.randn(10, len(t))*(4000-1000) + 1000  # Generate random signals
    
  ax[2].set_xlabel("tiempo [s]")
  for i in range(3):
    ax[i].plot(t, signals.T)
    ax[i].set_ylabel(f"Cuerpo {i+1}")
    ax[i].set_ylim([mag_min.get(), mag_max.get()])
  ax[0].set_xlim([0, time_scale.get()])
  labels = [f's{i+1}' for i in range(10)]
  # Adding legend to axis 0, one label per row
  legend = ax[0].legend(labels, loc='upper right', 
               bbox_to_anchor=(1.19, 0.5),  ncol=1, )

  for axis in ax:
    axis.set_ylim([mag_min.get(), mag_max.get()])

  canvas = FigureCanvasTkAgg(fig, master=plot_graf_frame)
  canvas.draw()
  canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

  
  # control frame ============================================================
  btn_conectar = tk.Button(control_frame, text="Conectar", bg=hex_color,
    command=lambda: toggle_button(btn_conectar, "Conectado", "Conectar"),
    width=13,)
  btn_conectar.grid(row=0, column=0, padx=5, columnspan=3, sticky='ew')
  # alarm --------------------------------------------------------------------
  btn_alarma = tk.Button(control_frame, text="Alarma", bg=hex_color,
    command=lambda: toggle_button(btn_alarma, "Alarma Activa", "Alarma"),
    width=13, )
  btn_alarma.grid(row=1, column=0, padx=5)

  label0 = tk.Label(control_frame, text="Umbral")
  label0.grid(row=1, column=1, padx=5)
  entry0 = tk.Entry(control_frame, width=15)
  entry0.grid(row=1, column=2, padx=5)
  # save data ----------------------------------------------------------------
  btn_guardar = tk.Button(control_frame, text="Guardar", bg=hex_color,
    command=lambda: toggle_button(btn_guardar, "Guardando", "Guardar"),
    width=13,)
  btn_guardar.grid(row=2, column=0, padx=5)

  text_label = tk.Label(control_frame, text="Archivo")
  text_label.grid(row=2, column=1, padx=5)
  text_entry = tk.Entry(control_frame, width=15)
  text_entry.grid(row=2, column=2, pady=5)

  # mostrar figura esquematica ===============================================
  img_path = "mfl_sup.png"  # Make sure this path is correct
  img = Image.open(img_path)
  # Resize the image while maintaining aspect ratio
  base_width = 730  # Adjust this value as needed
  w_percent = (base_width / float(img.size[0]))
  h_size = int((float(img.size[1]) * float(w_percent)))
  img = img.resize((base_width, h_size), Image.Resampling.LANCZOS)
  img = ImageTk.PhotoImage(img)
  img_label = tk.Label(image_frame, image=img)
  img_label.pack(side=tk.TOP, pady=2)
  img_label.image = img

  root.mainloop()
if __name__ == "__main__":
  create_interface()