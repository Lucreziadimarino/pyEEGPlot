import os
import sys
import numpy as np
import time

# Lazy initialization of Julia to avoid overhead on import
_jl = None
_backend_configured = False
_current_backend = None
_warmup_done = False
_static_warmup_done = False
_configure_attempted = False

def get_julia():
    global _jl
    if _jl is None:
        try:
            import subprocess
            # Dynamically find Julia's bin directory to fix DLL loading issues on Windows
            try:
                res = subprocess.run(["julia", "-e", "print(Sys.BINDIR)"], 
                                     capture_output=True, text=True, check=True)
                julia_bin = res.stdout.strip()
                if os.path.isdir(julia_bin):
                    os.environ["PATH"] = julia_bin + os.pathsep + os.environ["PATH"]
                    if hasattr(os, "add_dll_directory"):
                        # This is critical for Python 3.8+ on Windows to find Julia's DLLs
                        os.add_dll_directory(julia_bin)
                    
                    # Also add Julia's lib directory to PATH for OpenSSL DLLs
                    julia_lib = os.path.join(julia_bin, "..", "lib")
                    if os.path.isdir(julia_lib):
                        os.environ["PATH"] = julia_lib + os.pathsep + os.environ["PATH"]
                        if hasattr(os, "add_dll_directory"):
                            os.add_dll_directory(julia_lib)
            except Exception:
                pass

            # Enable compiled modules for better performance after initial setup
            from julia import Julia
            _jl = Julia(compiled_modules=True) 
        except Exception as e:
            error_msg = str(e).lower()
            error_type = type(e).__name__.lower()

            # For statically linked Python builds (Linux or other Conda based Python)
            if "unsupportedpythonerror" in error_type or "statically linked" in error_msg:
                # Avoid an infinite loop if python-jl also fails
                if os.environ.get("PYJULIA_RELAUNCHED") == "1": 
                    print("Reboot with python-jl failed. Impossibile to use compiled_modules=True.")
                    raise e
                
                print("\nPython Statically Linked")
                print("Automatic reboot with 'python-jl'...\n")

                # Set an environment variable before attempting the relaunch
                os.environ["PYJULIA_RELAUNCHED"] = "1"
                try: 
                    # Replace the current process with python-jl
                    import sys
                    os.execvp("python-jl", ["python-jl"] + sys.argv)
                except FileNotFoundError:
                    print("Error: command 'python-jl' not found. Make sure PyJulia is installed in your environment.")
                    raise e
            else:
                print(f"Error initializing PyJulia: {e}")
                raise
    return _jl


def _get_julia_env_path():
    base = os.path.join(os.path.expanduser("~"), ".pyEEGPlot")
    env = os.path.join(base, "jl_env")
    os.makedirs(env, exist_ok=True)
    return env

def configure(dev_path=None):
    """
    Manually trigger Julia setup and dependency installation.
    If dev_path is provided, it links a local copy of EEGPlot.jl.
    Otherwise, it fetches a stable release from GitHub.
    """
    import julia

    print("Initializing Julia setup, be patient initialization will take a while...")
    julia.install()

    get_julia()
    from julia import Main
    Main.eval("using Pkg")

    # 1. Create and activate an isolated Julia environment in the user's home directory
    # This prevents version conflicts with the user's global Julia environment
    env_path = _get_julia_env_path()
    jl_env_path = env_path.replace("\\", "\\\\")
    Main.eval(f'Pkg.activate("{jl_env_path}")')
    print(f"Julia environment activated at: {env_path}")

    # 2. Add standard dependencies
    print("Installing base dependencies...")
    Main.eval('Pkg.add(["Eegle", "Makie", "CairoMakie", "GLMakie"])')
    # 3. Handle EEGPlot.jl (Local development path or from GitHub)
    if dev_path is not None:
        print(f"Linking local EEGPlot.jl from {dev_path}...")
        jl_path = os.path.abspath(dev_path).replace("\\", "\\\\")
        Main.eval(f'Pkg.develop(path="{jl_path}")')
    else:
        print("Fetching stable EEGPlot.jl from GitHub...")
        # NOTE: Add rev="vX.Y.Z" with the actual release tag (e.g., "v0.1.7") or a commit hash to download a specific version!
        Main.eval('Pkg.add(url="https://github.com/marco-congedo/EEGPlot.jl.git")')

    # 4. Finalize and precompile
    Main.eval("Pkg.instantiate()")
    print("Precompiling Julia packages (this will take a while, but saves time later)...")
    Main.eval("Pkg.precompile()")
    
    print("pyEEGPlot configured successfully! 🎉")


def eegplot(X, sr, X_labels=None, block=True, **kwargs):
    """
    Python wrapper for EEGPlot.eegplot
    
    Parameters:
    -----------
    X : numpy.ndarray
        EEG data matrix (samples x channels)
    sr : int or float
        Sampling rate in Hz
    X_labels : list of str, optional
        Channel labels
    block : bool, default=True
        If True and using GLMakie, blocks until window is closed.
        If False, plot closes when script ends.
    **kwargs : additional keyword arguments
        Passed to Julia eegplot function
    
    Returns:
    --------
    fig : Julia Figure object
    """
    global _backend_configured
    
    get_julia()
    from julia import Main
    
    if not _backend_configured:
        init_plotting(backend="dynamic", do_warmup=False) 
    

    # Handle X_labels (None -> Nothing in Julia)
    if X_labels is None:
        X_labels = Main.eval("nothing")
    
    # Convert numpy arrays to proper Julia types
    processed_kwargs = {}
    for key, value in kwargs.items():
        if isinstance(value, np.ndarray):
            if value.dtype == np.int32:
                # Convert int32 to int64 for Julia compatibility
                processed_kwargs[key] = value.astype(np.int64)
            else:
                processed_kwargs[key] = value
        else:
            processed_kwargs[key] = value
    
    # Create the figure
    jl_eegplot = Main.eegplot
    fig = jl_eegplot(X, sr, X_labels, **processed_kwargs)
    
    # If blocking is requested and GLMakie is active, keep a reference to the figure
    # and notify the user that the window must be closed before continuing.
    backend = str(Main.eval("string(Makie.current_backend())"))
    if block and backend == "GLMakie":
        try:
            print("Interactive plot created. CLOSE WINDOW to continue...")
            Main.fig_to_display = fig 
        except Exception as e:
            print(f"Interaction warning: {e}")
    
    return fig

def init_plotting(backend="dynamic", do_warmup=True, progressbar_cb=None):
    """
    Initialize Julia, configure the selected backend,
    and optionally run warm-up only once.
    """
    global _backend_configured, _current_backend, _warmup_done, _static_warmup_done, _configure_attempted

    _report(progressbar_cb, 5, "Initializing Julia runtime...")
    get_julia()
    from julia import Main

    # Control to load EEGPlot and Makie only once per session
    if not _backend_configured:
        _report(progressbar_cb, 15, "Loading EEGPlot and Makie...")
        
        env_path = _get_julia_env_path()
        jl_env_path = env_path.replace("\\", "\\\\") 
        
        try:
            Main.eval("using Pkg")
            Main.eval(f'Pkg.activate("{jl_env_path}")') 
            Main.eval("using EEGPlot, Makie")
        except Exception as e:
            error_msg = str(e)
            
            if "InitError" in error_msg or "could not load library" in error_msg:
                raise RuntimeError(f"Critical library conflict between Python and Julia. See terminal for details")
            # Run one-time dependency setup
            if not _configure_attempted:
                _configure_attempted = True
                _report(progressbar_cb, 20, "Julia dependencies not ready. Running first-time setup...")
                configure()
                _report(progressbar_cb, 30, "Retrying EEGPlot and Makie import...")
                try:
                    Main.eval(f'Pkg.activate("{jl_env_path}")')
                    Main.eval("using EEGPlot, Makie")
                except Exception as e2:
                    raise RuntimeError("Julia dependencies could not be loaded even after setup.") from e2
            else:
                raise RuntimeError(f"Failed to load Julia dependencies: {e}")

        _backend_configured = True

    # Activate the requested backend. 
    if backend == "dynamic":
        _report(progressbar_cb, 40, "Activating dynamic backend (GLMakie)...")
        Main.eval("using GLMakie; GLMakie.activate!()")
        _current_backend = "GLMakie"

        if do_warmup and not _warmup_done:
            _report(progressbar_cb, 50, "Starting GPU warm-up, it might take a while...")
            
            warmup(progressbar_cb=progressbar_cb)
            _warmup_done = True
        else:
            _report(progressbar_cb, 100, "Dynamic backend ready.")

    elif backend == "static":
        _report(progressbar_cb, 40, "Activating static backend (CairoMakie)...")
        Main.eval("using CairoMakie; CairoMakie.activate!()")
        _current_backend = "CairoMakie"

        if do_warmup and not _static_warmup_done:
            _report(progressbar_cb, 60, "Preparing static plotting pipeline...")
            warmup_static(progressbar_cb=progressbar_cb)
            _static_warmup_done = True

        _report(progressbar_cb, 100, "Static backend ready.")

    else:
        raise ValueError(f"Unsupported backend: {backend}")

def _report(progressbar_cb, value, message):
    if progressbar_cb is not None:
        progressbar_cb(value, message)

def warmup(progressbar_cb=None):
    """
    Warmup of dynamic backend. Automatically uses stimulus configuration
    to compile all necessary graphic elements (lines, markers, text).
    """
    t0 = time.perf_counter()
    get_julia()
    from julia import Main

    _report(progressbar_cb, 50, "Activating GLMakie...")
    Main.eval("using GLMakie; GLMakie.activate!()")
    _report(progressbar_cb, 60, "Loading EEGPlot...")
    Main.eval("using EEGPlot")
    
    # Use minimal data to trigger compilation with low overhead
    _report(progressbar_cb, 75, "Rendering warm-up plot...")
    Xw = np.random.randn(16, 1) * 1e-3
    stim = np.zeros(16, dtype=np.int64)
    stim[4] = 1

    eegplot(
        Xw, 10,
        X_labels=["Cz"],
        stim=stim,
        stim_wl=2,
        fig_size=(10, 10),
        block=False,
        _display=True
    )

    """
    Give GLMakie a brief moment to finalize initialization, 
    then close any warm-up windows that may have been opened.
    """
    _report(progressbar_cb, 90, "Finalizing GPU compilation...")
    try:
        Main.eval("""
            yield()
            sleep(0.2)
            try
                GLMakie.closeall()
            catch
            end
        """)
    except Exception:
        pass
        
    elapsed = time.perf_counter() - t0
    finish_msg = f"Warm-up completed in {elapsed:.2f} seconds."
    
    print(f"\n[TIMER] {finish_msg}")
    _report(progressbar_cb, 100, "Warm-up completed.")


def warmup_static(progressbar_cb=None): 
    """
    Warm-up of the static backend. 
    Compile the basic plotting pipeline once.
    """
    t0 = time.perf_counter()
    get_julia()
    from julia import Main

    _report(progressbar_cb, 50, "Activating CairoMakie...")
    Main.eval("using CairoMakie; CairoMakie.activate!()")
    _report(progressbar_cb, 60, "Loading EEGPlot...")
    Main.eval("using EEGPlot")

    # Use minimal data to trigger compilation with low overhead
    _report(progressbar_cb, 75, "Rendering a small static plot...")
    Xw = np.random.randn(16, 1) * 1e-3

    eegplot(
        Xw, 10,
        X_labels=["Cz"],
        fig_size=(10, 10),
        block=False,
        _display=False
    )

    elapsed = time.perf_counter() - t0
    print(f"\n[TIMER] Static warm-up completed in {elapsed:.2f} seconds.")
    _report(progressbar_cb, 100, "Static backend ready.")


def save_figure(fig, file_path): 
    """
    Save a Julia/Makie figure.
    
    Parameters
    ----------
    fig: Julia Figure
        Figure returned by eegplot.
    file_path: str
        Output image path
    """
    get_julia()
    from julia import Main

    # Expose the figure in Julia's Main namespace before saving it.
    Main.fig_to_save = fig
    # Convert Windows backslashes for Julia string parsing. 
    jl_path = os.path.abspath(file_path).replace("\\", "\\\\")
    Main.eval(f'save("{jl_path}", fig_to_save)')
    



