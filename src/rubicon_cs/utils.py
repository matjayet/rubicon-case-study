import rasterio
import matplotlib.pyplot as plt
from datetime import timedelta, datetime
from sentinelhub.geo_utils import bbox_to_dimensions
import torch
import torch.nn.functional as F
import math

def display_geotiff(tiff_path, ncols=2, cmap='Greens'):
    """
    Display the individual bands of a GeoTIFF file using matplotlib.

    Parameters:
        tiff_path (str): Path to the GeoTIFF file.
        ncols (int): Number of columns in the subplot layout. Default is 2.
        cmap (str): Matplotlib colormap used to render the bands. Default is 'Greens'.

    Notes:
        - Displays each band in a subplot.
        - Tries to retrieve the acquisition date from the band's metadata and uses it in the title.
    """
    with rasterio.open(tiff_path) as tiff:

        nrows = (tiff.count // ncols) + (1 if tiff.count % ncols != 0 else 0)

        fig, ax = plt.subplots(ncols=ncols, nrows=nrows, figsize=(10, 5 * nrows))
        axes = ax.flatten()

        im = None

        # Loop through each band and plot it
        for i in range(tiff.count):
            # Read the data for the current band
            band_data = tiff.read(i + 1)
            
            # Retrieve the acquisition date for the current band
            band_metadata = tiff.tags(i + 1)
            acquisition_date = band_metadata.get("DATE", "No date available")
            
            im = axes[i].imshow(band_data, cmap=cmap, vmin=-1, vmax=1)
            axes[i].set_title(f"NDVI Index in AOI on {acquisition_date}", fontsize=10)    
            axes[i].axis('off')  # Turn off the axis
            fig.colorbar(im, ax=axes[i], orientation='horizontal', shrink=0.7, pad=0.05)

        plt.tight_layout()    
        plt.show()


def find_nearest_available_date(catalog, data_collection, geometry, target_date, max_days=30, cloud_cover_limit=20):
    """
    Find the nearest available date with imagery that meets cloud cover requirements.

    Parameters:
        catalog: A STAC catalog or API object with a `.search()` method.
        data_collection: The dataset or collection to search (e.g., Sentinel-2).
        geometry (dict or shapely geometry): The area of interest (AOI).
        target_date (str): The preferred date in "YYYY-MM-DD" format.
        max_days (int): The maximum number of days before/after the target date to search. Default is 30.
        cloud_cover_limit (int): The maximum allowed cloud cover percentage. Default is 20%.

    Returns:
        str: The nearest valid acquisition date as "YYYY-MM-DD".

    Raises:
        Exception: If no valid imagery is found within ±`max_days`.
    """
    time_window = 0
    target_date = datetime.strptime(target_date, "%Y-%m-%d")
    while time_window <= max_days:
        for delta in [time_window, -time_window]:  # Check both future and past
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
            
            results = list(search_iterator)
            if results:
                return results[0]["properties"]["datetime"][:10]  # Return the date in yyyy-mm-dd format
        time_window += 1  # Increase the window and try again

    # If no results are found after searching ±max_days
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


#The following functions are used to cut my image in 512x512 tiles to feed my model
# --- Padding ---
def pad_to_multiple(image, multiple=512):
    """Pad the image (C, H, W) to the next multiple of `multiple`."""
    _, h, w = image.shape
    pad_h = (math.ceil(h / multiple) * multiple) - h
    pad_w = (math.ceil(w / multiple) * multiple) - w
    return F.pad(image, (0, pad_w, 0, pad_h)), pad_h, pad_w  # (left, right, top, bottom)

# --- Patch Extraction ---
def extract_patches(image, patch_size=512):
    """Extract non-overlapping patches from image (C, H, W)."""
    _, h, w = image.shape
    patches = []
    for i in range(0, h, patch_size):
        for j in range(0, w, patch_size):
            patch = image[:, i:i+patch_size, j:j+patch_size]
            patches.append(((i, j), patch))
    return patches

# --- Stitch Patches Back ---
def stitch_patches(patches, original_shape, patch_size=512):
    """Reconstruct the full mask from patch predictions."""
    C, H, W = original_shape
    output = torch.zeros((C, H, W))
    for (i, j), patch in patches:
        output[:, i:i+patch_size, j:j+patch_size] = patch
    return output
