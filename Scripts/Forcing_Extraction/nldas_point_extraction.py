import pandas as pd
import numpy as np
import os
import geopandas as gpd
import rasterio
from rasterio import sample

## Disclaimer:
# This script extracts NLDAS forcing data at specific point locations defined in a GeoPackage file.
# This script was written for wathershed boundaries smaller than NLDAS2 Grid size (~0.125 degree).
# For larger areas, consider using HydroData (https://github.com/mhpi/hydroData)

##---------------------------INPUT-START---------------------------##
#this is geopackage file with Guage-ID field and Latitude/Longitude fields
gpkg_path = "/data/kas7897/AIforGeo/WQP_US_Sites.gpkg"
points_gdf = gpd.read_file(gpkg_path)

#optional for filtering specific Gauge-IDs, otherwise comment out
points_gdf = points_gdf[points_gdf['Gauge-ID']=='USGS-01193050']


# Path to your TIFF file
nldas2_path = "/data/shared_data/NLDAS/NLDAS2" #daily aggregated
start_date = '1980-01-01'
end_date = '2023-12-31'

forcings = ["APCP", "DLWRF", "DSWRF", "PRES", "TMP", "CONVfrac", "UGRD", "VGRD", "SPFH", "PEVAP", "CAPE"]

# Output directory
output_dir = '/data/kas7897/AIforGeo/shuyu_extra/forcings_test/point_extraction'

##---------------------------INPUT-END---------------------------##




# # Filter the GeoDataFrame based on your list/criteria


date_range = pd.date_range(start=start_date, end=end_date)
formatted_dates = date_range.strftime('%Y%m%d')
dates_array = formatted_dates.to_list()



os.makedirs(output_dir, exist_ok=True)

# Dictionary to hold data for each Gauge-ID: {gauge_id: {date: {forcing: value}}}
gauge_data = {gauge_id: {} for gauge_id in points_gdf['Gauge-ID']}

# Loop over each date and forcing
for i, date in enumerate(dates_array):
    print(f"Processing date: {date_range[i].strftime('%Y-%m-%d')}")
    
    for k in forcings:
        tif_path = f'{nldas2_path}/{k}/NLDAS_FORA0125_H.A{date}.0000.002.grb.SUB.tif'
        
        try:
            # Open the TIFF file
            with rasterio.open(tif_path) as src:
                # Convert point geometries to the CRS of the TIFF
                points_in_crs = points_gdf.to_crs(src.crs)
                
                # Prepare coordinates as list of tuples
                coordinates = [(x, y) for x, y in zip(points_in_crs.Longitude, points_in_crs.Latitude)]
                
                # Sample the raster at each point location
                raster_values = list(sample.sample_gen(src, coordinates))
                
                # Store values for each gauge
                for idx, gauge_id in enumerate(points_gdf['Gauge-ID']):
                    if date_range[i] not in gauge_data[gauge_id]:
                        gauge_data[gauge_id][date_range[i]] = {}
                    
                    # Extract the value (handle potential arrays)
                    val = raster_values[idx]
                    if isinstance(val, np.ndarray):
                        val = val.item()
                    gauge_data[gauge_id][date_range[i]][k] = val
        
        except Exception as e:
            print(f"Error processing {tif_path}: {e}")
            # Fill with NaN for missing data
            for gauge_id in points_gdf['Gauge-ID']:
                if date_range[i] not in gauge_data[gauge_id]:
                    gauge_data[gauge_id][date_range[i]] = {}
                gauge_data[gauge_id][date_range[i]][k] = np.nan

# Create one CSV per Gauge-ID
print("\nWriting CSV files...")
for gauge_id in points_gdf['Gauge-ID']:
    # Build DataFrame: rows=dates, columns=forcings
    rows = []
    for date in date_range:
        if date in gauge_data[gauge_id]:
            row = {'Date': date.strftime('%Y-%m-%d')}
            row.update(gauge_data[gauge_id][date])
            rows.append(row)
    
    if rows:
        df = pd.DataFrame(rows)
        # Ensure column order: Date first, then forcings in order
        column_order = ['Date'] + [f for f in forcings if f in df.columns]
        df = df[column_order]
        
        # Sanitize gauge_id for filename
        safe_gauge_id = str(gauge_id).replace('/', '_').replace('\\', '_').replace(':', '_')
        output_path = os.path.join(output_dir, f'Climate_{safe_gauge_id}.csv')
        
        df.to_csv(output_path, index=False)
        print(f"Wrote: {output_path}")

print("\nProcessing complete!")



