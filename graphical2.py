import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
import numpy as np
import matplotlib.pyplot as plt

def create_interface():
    root = tk.Tk()
    root.title("Custom Interface")
    
    # Create frames for better layout organization
    plot_frame = tk.Frame(root)
    plot_frame.pack(side=tk.LEFT, padx=10, pady=10)
    
    right_frame = tk.Frame(root)
    right_frame.pack(side=tk.RIGHT, padx=8, pady=8)
    
    entry_frame = tk.Frame(right_frame)
    entry_frame.pack(side=tk.TOP, pady=5)
    
    control_frame = tk.Frame(right_frame)
    control_frame.pack(side=tk.TOP, pady=5)
    
    image_frame = tk.Frame(right_frame)
    image_frame.pack(side=tk.TOP, pady=5)
    
    # Variables for entries
    num_samples = tk.IntVar(value=1500)
    mag_min = tk.DoubleVar(value=0)
    mag_max = tk.DoubleVar(value=5000)
    
    # Add entries for numerical variables
    label0 = tk.Label(entry_frame, text="Umbral")
    label0.grid(row=0, column=0, padx=5)
    entry0 = tk.Entry(entry_frame, width=10)
    entry0.grid(row=0, column=1, padx=5)
    
    label1 = tk.Label(entry_frame, text="Ventana de tiempo")
    label1.grid(row=1, column=0, padx=5)
    entry1 = tk.Entry(entry_frame, width=10, textvariable=num_samples)
    entry1.grid(row=1, column=1, padx=5)
    
    label2 = tk.Label(entry_frame, text="Flujo Magnetico Minimo")
    label2.grid(row=2, column=0, padx=5)
    entry2 = tk.Entry(entry_frame, width=10, textvariable=mag_min)
    entry2.grid(row=2, column=1, padx=5)
    
    label3 = tk.Label(entry_frame, text="Flujo Magnetico Maximo")
    label3.grid(row=3, column=0, padx=5)
    entry3 = tk.Entry(entry_frame, width=10, textvariable=mag_max)
    entry3.grid(row=3, column=1, padx=5)
    
    # Add entry for text variable
    text_label = tk.Label(entry_frame, text="nombre del archivo")
    text_label.grid(row=6, column=0, padx=5)
    text_entry = tk.Entry(entry_frame, width=20)
    text_entry.grid(row=6, column=1, pady=5)
    
    # Define button actions with toggle feature
    def toggle_button(btn, text_active, text_inactive):
        if btn.config('text')[-1] == text_inactive:
            btn.config(text=text_active, bg="green", fg="white")
        else:
            btn.config(text=text_inactive, bg="SystemButtonFace", fg="black")
    
    def update_plot():
        t = np.linspace(0, num_samples.get(), num=num_samples.get()) / 10
        for axis in ax:
            axis.cla()  # Clear the current axes
            axis.set_ylim([mag_min.get(), mag_max.get()])
        ax[0].plot(t, np.sin(t) * 4000 + 2000)
        ax[1].plot(t, np.cos(t) * 4000 + 2000)
        ax[2].plot(t, np.tan(t) * 4000 + 2000)
        canvas.draw()
    
    # Add push buttons
    btn_conectar = tk.Button(control_frame, text="conectar", command=lambda: toggle_button(btn_conectar, "Conectado", "conectar"))
    btn_conectar.grid(row=0, column=0, padx=5)
    
    btn_alarma = tk.Button(control_frame, text="alarma", command=lambda: toggle_button(btn_alarma, "Alarma Activa", "alarma"))
    btn_alarma.grid(row=0, column=1, padx=5)
    
    btn_guardar = tk.Button(control_frame, text="guardar", command=lambda: toggle_button(btn_guardar, "Guardando", "guardar"))
    btn_guardar.grid(row=0, column=2, padx=5)
    
    # Add apply button to update the plot with new parameters
    btn_apply = tk.Button(control_frame, text="Aplicar", command=update_plot)
    btn_apply.grid(row=2, column=0, columnspan=3, pady=5)
    
    # Add radio buttons
    radio_var = tk.IntVar()
    radio_btn0 = tk.Radiobutton(control_frame, text="señales", variable=radio_var, value=0)
    radio_btn0.grid(row=1, column=0, padx=5)
    
    radio_btn1 = tk.Radiobutton(control_frame, text="mapa de calor", variable=radio_var, value=1)
    radio_btn1.grid(row=1, column=1, padx=5)
    
    # Add matplotlib graph
    fig, ax = plt.subplots(3, 1, figsize=(6, 4), dpi=150)
    t = np.linspace(0, num_samples.get(), num=num_samples.get()) / 10
    ax[0].plot(t, np.sin(t) * 4000 + 2000)
    ax[1].plot(t, np.cos(t) * 4000 + 2000)
    ax[2].plot(t, np.tan(t) * 4000 + 2000)
    for axis in ax:
        axis.set_ylim([mag_min.get(), mag_max.get()])
    
    canvas = FigureCanvasTkAgg(fig, master=plot_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)
    
    # Display picture1.png
    img_path = "picture1.png"  # Make sure this path is correct
    img = Image.open(img_path)
    img = ImageTk.PhotoImage(img)
    img_label = tk.Label(image_frame, image=img)
    img_label.pack(side=tk.TOP, pady=5)
    img_label.image = img
    
    root.mainloop()

if __name__ == "__main__":
    create_interface()
