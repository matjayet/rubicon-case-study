import rasterio
import matplotlib.pyplot as plt
from datetime import timedelta, datetime
from sentinelhub.geo_utils import bbox_to_dimensions

def display_geotiff(tiff_path, ncols=2, cmap='Greens'):
    with rasterio.open(tiff_path) as tiff:

        nrows = (tiff.count // ncols) + (1 if tiff.count % ncols != 0 else 0)

        fig, ax = plt.subplots(ncols=ncols, nrows=nrows, figsize=(10, 5 * nrows))
        axes = ax.flatten()
        
        # Loop through each band and plot it
        for i in range(tiff.count):
            # Read the data for the current band
            band_data = tiff.read(i + 1)
            
            # Retrieve the acquisition date for the current band
            band_metadata = tiff.tags(i + 1)
            acquisition_date = band_metadata.get("DATE", "No date available")
            
            # Plot the current band in the corresponding subplot
            axes[i].imshow(band_data, cmap=cmap)  # Use imshow for displaying the band
            axes[i].set_title(f"NDVI Index in AOI on {acquisition_date}", fontsize=10)    
            axes[i].axis('off')  # Turn off the axis

        plt.tight_layout()    
        plt.show()


def find_nearest_available_date(catalog, data_collection, geometry, target_date, max_days=30, cloud_cover_limit=20):
    # Start by searching in the past (starting from the target date)
    time_window = 0
    target_date = datetime.strptime(target_date, "%Y-%m-%d")
    while time_window <= max_days:
        for delta in [time_window, -time_window]:  # Check both future (positive) and past (negative)
            search_date = target_date + timedelta(days=delta)
            search_time = (search_date.strftime("%Y-%m-%d"), search_date.strftime("%Y-%m-%d"))
            
            # Perform the search query to check if there are images for the date
            search_iterator = catalog.search(
                data_collection,
                geometry=geometry,
                time=search_time,
                filter=f'eo:cloud_cover < {cloud_cover_limit}',
                fields={"include": ["properties.datetime"], "exclude": []}
            )
            
            # If the search finds results, return the date
            results = list(search_iterator)
            if results:
                return results[0]["properties"]["datetime"][:10]  # Return the date in yyyy-mm-dd format
        time_window += 1  # Increase the window and try again

    # If no results are found after searching ±max_days, raise an exception
    raise Exception(f"No valid acquisitions found within ±{max_days} days of {target_date.strftime('%Y-%m-%d')}")

def get_scaled_dimensions(geometry, max_dim=2500):
    """
    Compute scaled image dimensions if original size exceeds max_dim.
    """
    width, height = bbox_to_dimensions(geometry.bbox, (10, 10))
    if width > max_dim or height > max_dim:
        scale_factor = max_dim / max(width, height)
        width *= scale_factor
        height *= scale_factor
    return int(width), int(height)
