import os
import numpy as np
import rasterio
import torch
from PIL import Image

from sentinelhub import (
    CRS, DataCollection, Geometry, MimeType,
    SentinelHubCatalog, SentinelHubRequest, SHConfig
)

from rubicon_cs.evalscripts import INDEX_DICT
from rubicon_cs.utils import (
    extract_patches, find_nearest_available_date,
    get_scaled_dimensions, pad_to_multiple, stitch_patches
)

def geotiff_for_veg_index(AOI, date_range, veg_index='ndvi', cloud_cover_limit=20):
    """
    Generate a multi-band GeoTIFF file containing vegetation index images
    for a given area and date range.

    Parameters:
        AOI (dict): Area of interest in GeoJSON format.
        date_range (tuple): Tuple of (start_date, end_date) in 'YYYY-MM-DD' format.
        veg_index (str): Vegetation index to use, default is 'ndvi'.
        cloud_cover_limit (int): Max allowed cloud cover percentage.
    """

    geometry = Geometry.from_geojson(AOI, crs=CRS.WGS84)

    # Set up config
    config = SHConfig()
    config.sh_client_id = os.environ["SH_CLIENT_ID"]
    config.sh_client_secret = os.environ["SH_CLIENT_SECRET"]

    # Catalog to find acquisition dates
    catalog = SentinelHubCatalog(config=config)

    search_iterator = catalog.search(
        DataCollection.SENTINEL2_L2A,
        geometry=geometry,
        time=(date_range[0], date_range[1]),
        filter=f'eo:cloud_cover < {cloud_cover_limit}',
        fields={"include": ["properties.datetime"], "exclude": []}
    )

    acquisition_dates = sorted({item["properties"]["datetime"][:10] for item in search_iterator})
    if not acquisition_dates:
        raise ValueError("No acquisition dates found within specified date range and cloud cover limit.")

    ndvi_stack = []
    transform = None
    width, height = get_scaled_dimensions(geometry)

    for date in acquisition_dates:
        request = SentinelHubRequest(
            evalscript=INDEX_DICT[veg_index],
            input_data=[SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=(date, date)
            )],
            responses=[SentinelHubRequest.output_response("default", MimeType.TIFF)],
            bbox=geometry.bbox,
            size=(width, height),
            config=config,
        )
        ndvi_img = request.get_data()[0]
        ndvi_stack.append(ndvi_img.squeeze())  # remove extra dimension

        # After retrieving the first image, use it to get metadata
        if transform is None:
            bounds = geometry.bbox
            print(f"Bounding Box: {bounds}")

            height, width = ndvi_img.shape[-2], ndvi_img.shape[-1]
            transform = rasterio.transform.from_bounds(*bounds, width, height)
            crs = geometry.crs.pyproj_crs()

    filename = f"outputs/section_1/{date_range[0]}_{date_range[1]}_{veg_index}.tif"
    # Save as GeoTIFF
    with rasterio.open(
        filename, "w",
        driver="GTiff",
        height=ndvi_stack[0].shape[0],
        width=ndvi_stack[0].shape[1],
        count=len(ndvi_stack),
        dtype=np.float32,
        crs=crs,
        transform=transform
    ) as dst:
        for i, (ndvi, date) in enumerate(zip(ndvi_stack, acquisition_dates), start=1):
            # Write each date of vegetation_index to a band in a GeoTIFF
            dst.write(ndvi.astype(np.float32), i)
            
            # Add the acquisition date as a description for each band
            dst.update_tags(i, DATE=date)


def png_for_target_date(AOI, target_date, cloud_cover_limit=20, rgb_evalscript='rgb_optimized'):
    """
    Generate and save an RGB image as PNG for a specific date or the nearest available one.

    Parameters:
        AOI (dict): Area of interest in GeoJSON format.
        target_date (str): Target date in 'YYYY-MM-DD' format.
        cloud_cover_limit (int): Max allowed cloud cover percentage.
        rgb_evalscript (str): Evalscript key for RGB image generation.
    """

    geometry = Geometry.from_geojson(AOI, crs=CRS.WGS84)

    # Set up config
    config = SHConfig()
    config.sh_client_id = os.environ["SH_CLIENT_ID"]
    config.sh_client_secret = os.environ["SH_CLIENT_SECRET"]

    # Catalog to find acquisition dates
    catalog = SentinelHubCatalog(config=config)
    search_iterator = catalog.search(
                    DataCollection.SENTINEL2_L2A,
                    geometry=geometry,
                    time=target_date,
                    filter=f'eo:cloud_cover < {cloud_cover_limit}',
                    fields={"include": ["properties.datetime"], "exclude": []}
                )
    if list(search_iterator):
        date = target_date
    else:
        date = find_nearest_available_date(
            catalog=catalog,
            data_collection=DataCollection.SENTINEL2_L2A,
            geometry=geometry,
            target_date=target_date,
            max_days=30,
            cloud_cover_limit=cloud_cover_limit  # Search ±30 days from target date
        )

    print(f"Using nearest available date: {date}")

    width, height = get_scaled_dimensions(geometry)
        
    request = SentinelHubRequest(
        evalscript=INDEX_DICT[rgb_evalscript],
        input_data=[SentinelHubRequest.input_data(
            data_collection=DataCollection.SENTINEL2_L2A,
            time_interval=(date, date)
        )],
        responses=[SentinelHubRequest.output_response("default", MimeType.PNG)],
        size=(width, height),
        geometry=geometry,
        config=config,
    )

    img = request.get_data()[0].astype(np.uint8)
    
    # Save the image as a PNG
    Image.fromarray(img).save(f'rgb_{date}.png')
    print(f"Saved RGB image for {date} to rgb_{date}.png")
    return date

# --- Full Inference Function ---
def semantic_segmentation_large_image(image, model, device, patch_size=512):
    """
    image: torch tensor of shape (C, H, W)
    model: segmentation model that takes input of shape (B, C, patch_size, patch_size)
    """
    model.eval()
    image = image.to(device)
    
    # 1. Pad
    padded_image, pad_h, pad_w = pad_to_multiple(image, patch_size)
    
    # 2. Extract patches
    patches = extract_patches(padded_image, patch_size)

    # 3. Predict each patch
    predicted_patches = []
    for (i, j), patch in patches:
        patch = patch.unsqueeze(0).to(device)  # (1, C, H, W)
        with torch.no_grad():
            pred = model(patch)[0]  # (1, num_classes, H, W)
        predicted_patches.append(((i, j), pred.squeeze().cpu()))
    
    # 4. Stitch prediction
    _, H_padded, W_padded = padded_image.shape
    stitched = stitch_patches(predicted_patches, (pred.shape[1], H_padded, W_padded), patch_size)

    # 5. Remove padding
    if pad_h > 0:
        stitched = stitched[:, :-pad_h, :]
    if pad_w > 0:
        stitched = stitched[:, :, :-pad_w]

    return stitched  # (num_classes, H_original, W_original)
