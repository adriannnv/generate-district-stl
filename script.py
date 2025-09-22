import os
import argparse
import geopandas as gpd
import rasterio
import rasterio.mask
import numpy as np
import pyvista as pv
from shapely.geometry import mapping

def generate_stl_models(
    districts_file: str,
    dem_file: str,
    output_folder: str = "stl_districts", # default value, if not specified program creates "stl_districts" in the folder it was run in.
    vertical_exaggeration: float = 10,
    target_size_mm: float = 180,	
):
    # create folder for output, if exists, dont create.
    os.makedirs(output_folder, exist_ok=True)

	# 
    gdf = gpd.read_file(districts_file).to_crs("EPSG:4026")
 
    with rasterio.open(dem_file) as src:
        if src.crs.to_string() != "EPSG:4026":
            raise ValueError("DEM must be reprojected to EPSG:4026")

    for idx, row in gdf.iterrows():
        name = row.get("shapeName", f"district_{idx}")
        geom = [mapping(row["geometry"])]

        with rasterio.open(dem_file) as src:
            out_image, _ = rasterio.mask.mask(src, geom, crop=True)
            arr = out_image[0]

            arr = np.where(arr == src.nodata, np.nan, arr)
            arr = np.nan_to_num(arr, nan=np.nanmin(arr))

            nrows, ncols = arr.shape
            xres, yres = src.res
            X, Y = np.meshgrid(
                np.arange(ncols) * xres,
                np.arange(nrows) * yres
            )

        Z = arr * vertical_exaggeration

        max_dim_m = max(ncols * xres, nrows * yres)
        scale = target_size_mm / (max_dim_m * 1000.0)
        X *= scale * 1000
        Y *= scale * 1000
        Z *= scale * 1000

        grid = pv.StructuredGrid(X, Y, Z)
        mesh = grid.extract_surface().triangulate()

        stl_path = os.path.join(output_folder, f"{name}.stl")
        mesh.save(stl_path)
        print(f"Saved {stl_path}")


def parse_args():
    parser = argparse.ArgumentParser(description="Generate STL models from DEM and district polygons.")
    parser.add_argument("districts_file", nargs="?", default="your_file_name.geojson", help="Path to districts GeoJSON")
    parser.add_argument("dem_file", nargs="?", default="your_file_name.tif", help="Path to DEM file (EPSG:4026)")
    parser.add_argument("--output", "-o", default="stl_districts", help="Output folder for STL files")
    parser.add_argument("--exaggeration", "-e", type=float, default=5, help="Vertical exaggeration factor")
    parser.add_argument("--scale", "-s", type=float, default=180, help="Target size in mm for longest side")
    parser.add_argument("--epsg", "-c", type=int, default=None,
                    help="EPSG code to reproject DEM and districts to (optional)")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    generate_stl_models(
        districts_file=args.districts_file,
        dem_file=args.dem_file,
        output_folder=args.output,
        vertical_exaggeration=args.exaggeration,
        target_size_mm=args.scale,
    )
