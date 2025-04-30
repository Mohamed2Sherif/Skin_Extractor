from fastapi import FastAPI
from fastapi.responses import FileResponse

from models.models import create_db_and_tables, SessionDep, seed_database

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
    file_path = "cdn/22/76.wad.client"
    return FileResponse(
        path=file_path,
        filename="76.wad.client",  # name user sees when saving
        media_type='application/octet-stream'  # generic binary type
    )
@app.get("party/accessToken/{rooomId}")
async def join_party(roomId:str):
    return "sdfsdf"