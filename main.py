import os

from fastapi import FastAPI
from fastapi.responses import FileResponse

from extractor import process_skin_folder, process_character_directory,get_script_dir
from models.models import create_db_and_tables, SessionDep, seed_database,getApiVersion
from skin_file_fetcher import download_skin
script_dir = get_script_dir()
api_version = getApiVersion()[:-2]
app = FastAPI()


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    seed_database()

@app.get("/health")
async def root():
    return {"Hello World"}

@app.get("/skin/{champId}/{skinId}")
async def get_skin(champId: str,skinId:str):

    if os.path.exists(f"cdn/{champId}/{skinId}.wad.client"):
        file_path = f"cdn/{champId}/{skinId}.wad.client"
    else:
        download_skin(champId, skinId)
        process_character_directory(
            script_dir, champId, skinId, api_version
        )
    return FileResponse(
        path=file_path,
        filename=f"{skinId}.wad.client",  # name user sees when saving
        media_type='application/octet-stream'  # generic binary type
    )
@app.get("party/accessToken/{rooomId}")
async def join_party(roomId:str):
    return "sdfsdf"