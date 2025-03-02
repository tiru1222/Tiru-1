import pandas as pd

# Specify the Excel file path
file_path = "previous_day_data.xlsx"  # Change this to your actual file path

# Read the Excel file
df = pd.read_excel(file_path)

# Print the data
print(df)
