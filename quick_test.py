#!/usr/bin/env python3
"""
Quick test script for pyEEGPlot
Run this to verify the wrapper is working correctly.
"""

import numpy as np
import pyEEGPlot as pyep

def quick_test():
    print("=== Quick Test for pyEEGPlot ===")
    
    # Configure the environment (only needed on first run)
    print("1. Configuring pyEEGPlot...")
    pyep.configure()
    
    # Test 1: Basic plot
    print("2. Testing basic EEG plot...")
    X = np.random.randn(256, 4)  # 256 samples, 4 channels
    sr = 128
    sensors = ["Fp1", "Fp2", "C3", "C4"]
    
    fig = pyep.eegplot(X, sr, sensors, fig_size=(800, 400))
    print("   [OK] Basic plot created successfully!")
    
    # Test 2: Plot with event markers
    print("3. Testing plot with event markers...")
    stim = np.zeros(256, dtype=np.int32)
    stim[50:100] = 1  # Event 1
    stim[150:200] = 2  # Event 2
    
    fig2 = pyep.eegplot(X, sr, sensors, 
                       stim=stim,
                       stim_labels=["event1", "event2"],
                       X_title="Test with Events")
    print("   [OK] Event markers plot created successfully!")
    
    print("\n[SUCCESS] All tests passed! pyEEGPlot is working correctly.")
    return True

if __name__ == "__main__":
    try:
        quick_test()
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
