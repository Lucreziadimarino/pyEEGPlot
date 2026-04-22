import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pyEEGPlot as pyep
import numpy as np

print("=== Command Line Test ===")
# Test data
X = np.random.randn(128, 4)
sr = 128
sensors = ['Fp1', 'Fp2', 'C3', 'C4']

print("Creating plot...")
fig = pyep.eegplot(X, sr, sensors, fig_size=(600, 600))
print("Plot created successfully!")
