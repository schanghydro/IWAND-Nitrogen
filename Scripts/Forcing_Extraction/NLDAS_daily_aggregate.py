from datetime import datetime, timedelta
import glob
import os

import numpy as np
import rasterio
from rasterio.enums import Resampling

###------INPUTS START------###

# set your variable here
nldas_var = 'PEVAP'

nldas_hourly_folder_path = f'/NLDAS2_download/{nldas_var}'
nldas_daily_folder_path = f'/NLDAS2_download/daily/{nldas_var}'


###------INPUTS END------###



# Define the folder containing the .tif files
folder_path = nldas_hourly_folder_path
output_folder = nldas_daily_folder_path

# List all .tif files
tif_files = glob.glob(os.path.join(folder_path, '*.tif'))

# Make sure output folder exists
os.makedirs(output_folder, exist_ok=True)


# Function to extract the date from a filename
def extract_date(filename):
    basename = os.path.basename(filename)
    # Assuming the date is in the format YYYYMMDD.HHMM and is right before the first '.'
    date_str = basename[18:31]
    return date_str[:8]  # Return only the date part


# Group files by date
files_by_date = {}
for file in tif_files:
    date = extract_date(file)
    if date not in files_by_date:
        files_by_date[date] = []
    files_by_date[date].append(file)

# Process each day
for date, files in files_by_date.items():
    daily_data = []
    for file in files:
        with rasterio.open(file) as src:
            # Read the first band
            data = src.read(1).astype(np.float32)

            # Prefer using the file's nodata value if present
            if src.nodata is not None:
                data[data == src.nodata] = np.nan

            # Handle extremely large sentinel values (replace with NaN)
            data[np.abs(data) > 1e10] = np.nan

            # Collect data for averaging
            daily_data.append(data)

    # Calculate the daily average (NaN-aware). For precipitation/evap we sum hourly values.
    if len(daily_data) == 0:
        print(f"No files for date {date}, skipping")
        continue

    stacked = np.stack(daily_data, axis=0)  # shape: (hours, rows, cols)
    if nldas_var == 'TMP':
        # Convert from Kelvin to Celsius
        stacked -= 273.15  
    if nldas_var in ['PEVAP', 'APCP']:
        daily_average = np.nansum(stacked, axis=0)
    else:
        daily_average = np.nanmean(stacked, axis=0)
    # Define the output filename
    output_filename = f'NLDAS_FORA0125_H.A{date}.0000.002.grb.SUB.tif'
    output_path = os.path.join(output_folder, output_filename)

    # Write the daily averaged data to a new .tif file
    with rasterio.open(files[0]) as src:  # Open the first file to copy metadata
        profile = src.profile.copy()
        # Choose a sensible nodata for output and ensure dtype is float32
        out_nodata = -9999.0
        profile.update(dtype='float32', nodata=out_nodata, count=1)

        # Replace NaNs with the output nodata value before writing
        out_arr = daily_average.astype(np.float32)
        out_arr[np.isnan(out_arr)] = out_nodata

        with rasterio.open(output_path, 'w', **profile) as dst:
            dst.write(out_arr, 1)

print("Daily averaging complete.")

