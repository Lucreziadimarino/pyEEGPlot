import numpy as np
import pyEEGPlot as pyep

# Force CairoMakie backend for static plots
from julia import Main
Main.eval("using CairoMakie; CairoMakie.activate!()")

# Basic test
X = np.random.randn(128*4, 4)
sr = 128
sensors = ['Fp1', 'Fp2', 'C3', 'C4']
fig = pyep.eegplot(X, sr, sensors, fig_size=(600, 300))

# Save to file (optional)
# Main.eval("save('plot.png', fig)")
# print("Static plot created successfully!")

# Passiamo la variabile 'fig' da Python alla memoria di Julia
Main.fig = fig 

# Diciamo a Julia di salvare usando i doppi apici per il nome del file
Main.eval('save("plot.png", fig)')

print("Static plot created successfully!")