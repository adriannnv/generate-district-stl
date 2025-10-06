from fastapi import FastAPI, UploadFile, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os, tempfile, shutil, zipfile
from script import generate_stl_models

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
def hello():
	return {"message": "Hello world!"}

@app.post("/generate")
async def generate_stl(geojson: UploadFile, dem: UploadFile, exaggeration: float = Form(10)):
	#save uploaded files temporarily
	with tempfile.TemporaryDirectory() as temp_dir:
		geojson_path = os.path.join(temp_dir, geojson.filename)
		dem_path = os.path.join(temp_dir, dem.filename)

		with open(geojson_path, "wb") as f:
			shutil.copyfileobj(geojson.file, f)
		with open(dem_path, "wb") as f:
			shutil.copyfileobj(dem.file, f)
		
		# generate stls
		output_folder = os.path.join(temp_dir, "stl_output")
		generate_stl_models(
			districts_file=geojson_path,
			dem_file=dem_path,
			output_folder=output_folder,
			vertical_exaggeration=exaggeration
		)

		# zip the output folder
		zip_path = os.path.join(temp_dir, "terrain.zip")
		with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
			for root, _, files in os.walk(output_folder):
				for file in files:
					file_path = os.path.join(root, file)
					arcname = os.path.relpath(file_path, output_folder)
					zipf.write(file_path, arcname)

		#return zip
		return FileResponse(
			path=zip_path,
			media_type='application/zip',
			filename='terrain.zip'
		)

			