#%% ========================================================================
# Importación de librerías principales
# ==========================================================================
import tkinter as tk        # Importar librería para crear la interfaz
from interface import MainInterFace  # Importar la clase MainInterFace
from interface import on_closing     # Importar función para cerrar la aplicación
import multiprocessing        # Importar librería para procesos paralelos
#daniel

#%% ========================================================================
# Iniciar la aplicación
# ==========================================================================
if __name__ == "__main__":  # Si se ejecuta el script principal
  multiprocessing.freeze_support()    # Congelar soporte para Windows
  root = tk.Tk()                      # Crear la ventana principal  
  app = MainInterFace(root)           # Crear la interfaz principal 
  root.protocol("WM_DELETE_WINDOW", lambda : on_closing(app))
  root.mainloop()                     # Iniciar el bucle principal
