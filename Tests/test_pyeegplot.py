import numpy as np
import pyEEGPlot as pyep
#from julia import Main

def test_static_plot():
    print("Testing Static Plot...")
    # Create dummy data: 1280 samples, 4 channels
    X = np.random.randn(1280, 4)
    sr = 128
    sensors = ["Fp1", "Fp2", "C3", "C4"]
    
    fig = pyep.eegplot(X, sr, sensors, fig_size=(814, 450))
    print("Static plot created.")
    return fig

def test_multiple_datasets():
    print("Testing Multiple Datasets...")
    # Create data
    T = 1280
    N = 4
    X = np.random.randn(T, N)
    sr = 128
    sensors = ["Ch1", "Ch2", "Ch3", "Ch4"]
    
    # Simple PCA-like projection
    u = np.random.randn(N, 1)
    u /= np.linalg.norm(u)
    y = X @ u  # T x 1
    P = y @ u.T # T x N
    
    fig = pyep.eegplot(X, sr, sensors, 
                       fig_size=(814, 614),
                       overlay=P, 
                       Y=y, 
                       Y_size=0.1)
    print("Multiple datasets plot created.")
    return fig

def test_event_markers():
    print("Testing Event Markers...")
    T = 5120
    N = 4
    X = np.random.randn(T, N)
    sr = 256
    
    # Create stimulation vector
    stim = np.zeros(T, dtype=np.int32)
    for i in range(1, 6):
        stim[i * 500 : i * 500 + 768] = (i % 3) + 1
        
    stim_labels = ["right_hand", "feet", "rest"]
    
    fig = pyep.eegplot(X, sr, 
                       stim=stim,
                       stim_labels=stim_labels,
                       stim_wl=1, 
                       X_title="Motor Imagery data (Dummy)")
    print("Event markers plot created.")
    return fig

if __name__ == "__main__":
    # Ensure Julia dependencies for tests are available
    print("Initializing Julia environment for tests (First run will install dependencies)...")
    import pyEEGPlot
    #pyEEGPlot.configure()
    
    try:
        test_static_plot()
        test_multiple_datasets()
        test_event_markers()
        print("\nAll tests passed successfully!")
    except Exception as e:
        print("\nTest failed:")
        import traceback
        traceback.print_exc()
