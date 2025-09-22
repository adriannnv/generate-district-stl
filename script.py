#!/usr/bin/env python3
import os
import argparse
import geopandas as gpd
import rasterio
import rasterio.mask
import numpy as np
import pyvista as pv
from shapely.geometry import mapping
from rasterio.warp import calculate_default_transform, reproject, Resampling

def generate_stl_models(
	districts_file: str,
	dem_file: str,
	output_folder: str = "stl_districts",  # default value, if not specified program creates "stl_districts" in the folder it was run in.
	vertical_exaggeration: float = 10,
	target_size_mm: float = 180,
	target_epsg: int = None,  # optional EPSG for reprojection
):
	# create folder for output, if exists, don't create
	os.makedirs(output_folder, exist_ok=True)

	# open DEM
	with rasterio.open(dem_file) as src:
		dem_crs = src.crs

	# determine target CRS
	if target_epsg is not None:
		target_crs = f"EPSG:{target_epsg}"
	else:
		target_crs = dem_crs

	# load and reproject districts
	gdf = gpd.read_file(districts_file)
	gdf = gdf.to_crs(target_crs)

	# iterate over districts
	for idx, row in gdf.iterrows():
		name = row.get("shapeName", f"district_{idx}")
		geom = [mapping(row["geometry"])]

		with rasterio.open(dem_file) as src:
			# mask and reproject DEM for this district
			if target_epsg is not None and src.crs.to_string() != f"EPSG:{target_epsg}":
				out_image, out_transform = rasterio.mask.mask(
					src, geom, crop=True, all_touched=True, nodata=src.nodata
				)
				dst_crs = f"EPSG:{target_epsg}"
				dst_array = np.empty_like(out_image)
				reproject(
					source=out_image,
					destination=dst_array,
					src_transform=src.transform,
					src_crs=src.crs,
					dst_transform=out_transform,
					dst_crs=dst_crs,
					resampling=Resampling.nearest
				)
				arr = dst_array[0]
			else:
				out_image, _ = rasterio.mask.mask(src, geom, crop=True)
				arr = out_image[0]

		arr = np.where(arr == src.nodata, np.nan, arr)
		arr = np.nan_to_num(arr, nan=np.nanmin(arr))

		# create mesh for this district
		nrows, ncols = arr.shape
		xres, yres = src.res
		X, Y = np.meshgrid(np.arange(ncols) * xres, np.arange(nrows) * yres)
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
	parser.add_argument("dem_file", nargs="?", default="your_file_name.tif", help="Path to DEM file")
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
		target_epsg=args.epsg
	)
