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
import subprocess

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

	processed_dem_file = dem_file
	if target_epsg is not None:
		target_crs = f"EPSG:{target_epsg}"
		
		# Check DEM's current CRS
		with rasterio.open(dem_file) as src:
			dem_crs = src.crs
		
		if dem_crs.to_string() != target_crs:
			print(f"Reprojecting DEM to {target_crs} using gdalwarp...")
			
			# Construct the gdalwarp command with variables
			temp_dem_name = f"reprojected_dem_{target_epsg}.tif"
			command = ["gdalwarp", "-t_srs", target_crs, dem_file, temp_dem_name]
			
			# Execute the command
			try:
				subprocess.run(command, check=True, capture_output=True, text=True)
				processed_dem_file = temp_dem_name
				print("Reprojection successful.")
			except subprocess.CalledProcessError as e:
				print(f"Error during gdalwarp execution: {e.stderr}")
				return # Exit if reprojection fails

	# Load and reproject districts file to desired crs.
	gdf = gpd.read_file(districts_file)
	if target_epsg is not None:
		target_crs = f"EPSG:{target_epsg}"
		gdf = gdf.to_crs(target_crs)
	# iterate over districts. main loop
	for idx, row in gdf.iterrows():
		# assigns name of district, tries finding column "shapeName", change if different.
		name = row.get("shapeName", f"district_{idx}")
		# convert from shapely object to dictionary.
		geom = [mapping(row["geometry"])]

		# open the DEM (digital elevation model)
		with rasterio.open(processed_dem_file) as src:
			if target_epsg is not None and src.crs.to_string() != f"EPSG:{target_epsg}":
				# crop DEM(src) to the boundaries of the districts geometry(geom).
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
					resampling=Resampling.bilinear
				)
				arr = dst_array[0]
			else: # no reprojection is needed.
				out_image, _ = rasterio.mask.mask(src, geom, crop=True)
				arr = out_image[0]

		# find no data pixels and replace with NaN, then replace NaN with the lowest point of elevation.
		arr = np.where(arr == src.nodata, np.nan, arr)
		arr = np.nan_to_num(arr, nan=np.nanmin(arr))

		# create mesh for this district
		nrows, ncols = arr.shape
		xres, yres = src.res
		# create 2 2d arrays, x and y. they represent coords of each pixel in the grid.
		X, Y = np.meshgrid(np.arange(ncols) * xres, np.arange(nrows) * yres)
		# add vertical exageration.
		Z = arr * vertical_exaggeration

		# scaling. model is now in milimeters.
		max_dim_m = max(ncols * xres, nrows * yres)
		scale = target_size_mm / (max_dim_m * 1000.0)
		X *= scale * 1000
		Y *= scale * 1000
		Z *= scale * 1000

		grid = pv.StructuredGrid(X, Y, Z)
		# create triangle mesh
		mesh = grid.extract_surface().triangulate()

		stl_path = os.path.join(output_folder, f"{name}.stl")
		mesh.save(stl_path)
		print(f"Saved {stl_path}")

		
	 # clean up the temporary DEM file
	if processed_dem_file != dem_file:
		os.remove(processed_dem_file)
		print(f"Removed temporary file: {processed_dem_file}")


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
