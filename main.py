import os
import logging
logger = logging.getLogger(__name__)
from fastapi import FastAPI
from fastapi.responses import FileResponse

from extractor import process_skin_folder, process_character_directory,get_script_dir
from models.models import create_db_and_tables, SessionDep, seed_database,getApiVersion
from skin_file_fetcher import download_skin
app = FastAPI()


@app.on_event("startup")
async def startup_event():
    logger.info("Starting database initialization")
    create_db_and_tables()
    logger.info("Starting database seeding")
    seed_database()
    logger.info("Startup complete")

@app.get("/health")
async def root():
    return {"Hello World"}

@app.get("/skin/{champId}/{skinId}")
async def get_skin(champId: str,skinId:str):
    file_path=""
    script_dir = get_script_dir()
    api_version = getApiVersion()[:-2]
    if os.path.exists(os.path.join(script_dir,"cdn",champId,f"{skinId}.wad.client")):
        file_path = os.path.join(script_dir,"cdn",champId,f"{skinId}.wad.client")
        return FileResponse(
            path=file_path,
            filename=f"{skinId}.wad.client",  # name user sees when saving
            media_type='application/octet-stream'  # generic binary type
        )
    else:
        download_skin(champId, skinId)
        process_character_directory(
            script_dir, champId, skinId, api_version
        )
        file_path = os.path.join(script_dir,"cdn",champId,f"{skinId}.wad.client")
        return FileResponse(
            path=file_path,
            filename=f"{skinId}.wad.client",  # name user sees when saving
            media_type='application/octet-stream'  # generic binary type
        )
@app.get("party/accessToken/{rooomId}")
async def join_party(roomId:str):
    return "sdfsdf"