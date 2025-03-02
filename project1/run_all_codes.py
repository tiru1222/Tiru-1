import subprocess
import sys

def run_code(file_name):
    """Run a Python script and capture its output."""
    try:
        print(f"\nRunning {file_name}...")
        # Run the script
        result = subprocess.run(
            [sys.executable, file_name],  # Use the current Python interpreter
            check=True,                   # Raise an error if the script fails
            capture_output=True,          # Capture the output
            text=True                     # Decode the output as text
        )
        print(result.stdout)  # Print the output for visibility
        print(f"\n{file_name} completed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"\nError running {file_name}: {e.stderr}")
        sys.exit(1)  # Exit if any code fails

# Run the codes in sequence
run_code("autologin.py")
run_code("previous_day.py")
run_code("present_day.py")
run_code("final_order.py")
run_code("slm.py")

