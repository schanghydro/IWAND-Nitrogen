'''
Users can expand IWAND-Nitrogen by extracting additional forcings or applying the workflow to new watersheds. The function below demonstrates how to:
1. Read a watershed shapefile.
2. Reproject to the correct coordinate system as needed.
3. Compute zonal statistics (e.g., mean) of any raster forcing dataset.
4. Export a dataframe with watershed attributes and basin-averaged forcing values.
'''
import pandas as pd
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
import os 
import warnings

os.chdir("./data")
def extract_watershed_stats(watershed_path, raster_path, var_name, save_path=None):
    # Load watershed boundaries
    wshd = gpd.read_file(watershed_path)

    # Get raster CRS (may be None)
    with rasterio.open(raster_path) as src:
        raster_crs = src.crs

    # Handle CRS logic
    if wshd.crs is None and raster_crs is None:
        raise ValueError("Neither watershed nor raster has a CRS defined. Please assign a CRS before running.")
    elif raster_crs is None:
        warnings.warn("Raster has no CRS. Assuming it matches watershed CRS.", UserWarning)
    elif wshd.crs is None:
        raise ValueError("Watershed file has no CRS defined. Please define a CRS before running.")
    elif wshd.crs != raster_crs:
        wshd = wshd.to_crs(raster_crs)

    # Prepare base dataframe without geometry
    df_wshd = wshd.drop(columns=["geometry"])
    
    # Compute zonal statistics
    stats = zonal_stats(wshd, raster_path, stats="mean")
    stats_df = pd.DataFrame(stats)
    df_wshd[var_name] = stats_df["mean"].values
    
    if save_path:
        df_wshd.to_csv(save_path, index=False)
    return(df_wshd)
        
    
watershed_path="./IWAND-Nitrogen/Watershed_Boundary_Simplified.gpkg"
raster_path="./Forcing/Human_2017.tif"
df_wshd=extract_watershed_stats(watershed_path, raster_path, "Human_2017", save_path=None)