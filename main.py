from fastapi import FastAPI

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
async def say_hello(champId: str,skinId:str):
    return {"message": f"Hello {champId,skinId}"}
@app.get("party/accessToken/{rooomId}")
async def join_party(roomId:str):
    return "sdfsdf"