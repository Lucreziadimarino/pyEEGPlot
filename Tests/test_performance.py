import time
import numpy as np
import pyEEGPlot as pyep

def test_performance():
    print("=== Performance Test ===")
    
    # Test data
    X = np.random.randn(256, 4)
    sr = 128
    sensors = ['Fp1', 'Fp2', 'C3', 'C4']
    
    # First call (includes initialization)
    print("1. First call (with initialization)...")
    start_time = time.time()
    fig1 = pyep.eegplot(X, sr, sensors, fig_size=(600, 300))
    first_call_time = time.time() - start_time
    print(f"   First call took: {first_call_time:.2f} seconds")
    
    # Second call (should be faster)
    print("2. Second call (cached backend)...")
    start_time = time.time()
    fig2 = pyep.eegplot(X, sr, sensors, fig_size=(600, 300))
    second_call_time = time.time() - start_time
    print(f"   Second call took: {second_call_time:.2f} seconds")
    
    # Third call (should be similar to second)
    print("3. Third call (cached backend)...")
    start_time = time.time()
    fig3 = pyep.eegplot(X, sr, sensors, fig_size=(600, 300))
    third_call_time = time.time() - start_time
    print(f"   Third call took: {third_call_time:.2f} seconds")
    
    print(f"\nPerformance improvement: {first_call_time/second_call_time:.1f}x faster after initialization")

if __name__ == "__main__":
    test_performance()
