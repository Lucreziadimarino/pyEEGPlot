import numpy as np
import pyEEGPlot as pyep

# Force CairoMakie backend for static plots that don't disappear
from julia import Main
Main.eval("using CairoMakie; CairoMakie.activate!()")

# Basic test
X = np.random.randn(128*4, 4)
sr = 128
sensors = ['Fp1', 'Fp2', 'C3', 'C4']
fig = pyep.eegplot(X, sr, sensors, fig_size=(600, 600))

print("Static plot created! The plot will persist after script ends.")
print("You can save it or interact with it in your IDE's plot viewer.")

# Optional: Save to file
# Main.eval("save('eeg_plot.png', fig)")
print("Plot saved successfully!")
