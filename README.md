## STL generator of districts within a country.

This Python script generates 3D printable **STL files** of geographical districts from a Digital Elevation Model (DEM) and a GeoJSON file. It's designed to create physical terrain models for visualization, education, or personal projects.

-----

### Requirements

The script relies on some Python libraries. Install them via `pip`:

```sh
pip install geopandas rasterio numpy pyvista shapely
```

-----

### Usage

Run the script from the command line, providing the paths to your district boundaries and DEM files.

**Basic Command**

```sh
python your_script_name.py path/to/districts.geojson path/to/dem.tif
```

**Optional Arguments**

Customize the output with the following flags:

  * `-o, --output <folder_name>`: Specifies the output directory for the STL files. Defaults to `stl_districts`.
  * `-e, --exaggeration <factor>`: Sets the vertical exaggeration for terrain features. A higher value makes mountains appear taller. The default is `5`.
  * `-s, --scale <mm>`: Defines the target size of the model's longest side in millimeters. Defaults to `180`.
  * `-c, --epsg <code_number>`: Reprojects input files to a specified EPSG coordinate system. This is crucial if your GeoJSON and DEM files use different systems. For example, use `4326` for WGS 84.

**Example**

This command generates a model with a vertical exaggeration of 10 and a longest side of 200 mm, reprojecting the data to EPSG 32633.

```sh
python your_script_name.py data/districts.geojson data/elevation.tif -o output_models -e 10 -s 200 -c 32633
```

-----

### Input Files

**Districts File (`.geojson`)**

A **GeoJSON** file containing the district polygons. The script processes each polygon to create a separate STL file. By default, it uses the `"shapeName"` property for naming the output files; otherwise, it assigns a generic name like `district_0`.

**DEM File (`.tif`)**

A **GeoTIFF** file containing elevation data. The resolution of this file dictates the detail of the final 3D model.
