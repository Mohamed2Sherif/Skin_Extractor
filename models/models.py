import json
from datetime import datetime
from typing import Annotated,Dict,Optional
import logging
logger = logging.getLogger(__name__)
import requests
from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Session, SQLModel, create_engine, select,Relationship

class Champion(SQLModel, table=True):
    id: Optional[str] = Field(default=None, primary_key=True)
    champ_code: str = Field(index=True)
    champ_name: Optional[str] = Field(default=None)
    date_created: datetime = Field(default_factory=datetime.utcnow)  # Auto-set on creation
    date_updated: datetime = Field(default_factory=datetime.utcnow)  # Auto-updated later
    skins: list["Skin"] = Relationship(back_populates="champion")  # Optional: For relationship

class Skin(SQLModel, table=True):
    id: str = Field(primary_key=True)  # No longer Optional for primary key
    champion_id: str = Field(primary_key=True, foreign_key="champion.id")  # Fixed: lowercase + quotes
    skin_name: Optional[str] = Field(default=None, index=True)
    champion: Optional[Champion] = Relationship(back_populates="skins")
    __table_args__ = (

    )
sqlite_file_name = "mistrShifo.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

connect_args = {"check_same_thread": False}
engine = create_engine(sqlite_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)



def get_session():
    with Session(engine) as session:
        yield session
SessionDep = Annotated[Session, Depends(get_session)]

def getApiVersion() -> str:
    response = requests.get("https://ddragon.leagueoflegends.com/api/versions.json")
    apiVersion = json.loads(response.text)[0]
    return apiVersion
def get_champion_data() -> Dict:
    champions_dict = {}
    apiVersion = getApiVersion()
    url = f"https://ddragon.leagueoflegends.com/cdn/{apiVersion}/data/en_US/champion.json"
    championsData_Response = requests.get(url)
    championData = json.loads(championsData_Response.text)
    for champ in championData["data"].items():
        url = f"https://ddragon.leagueoflegends.com/cdn/{apiVersion}/data/en_US/champion/{champ[1]['id']}.json"
        ch_detail_response = requests.get(url)
        champ_details = json.loads(ch_detail_response.text)
        champions_dict[champ_details["data"][champ[0]]["key"]] = champ_details["data"][champ[0]]
    return champions_dict


def seed_database():
    with Session(engine) as db:
        champions_data = get_champion_data()

        for champ_key in champions_data:
            details = champions_data[champ_key]

            # Create or update champion
            champ = Champion(
                id=champ_key,
                champ_code=details["id"],
                champ_name=details["name"],
                date_created=datetime.utcnow(),
                date_updated=datetime.utcnow()
            )
            db.merge(champ)

            # Process skins
            for skin in details["skins"]:
                skin_id = f"{skin['num']}"
                skin_obj = Skin(
                    id=skin_id,
                    champion_id=champ_key,
                    skin_name=skin["name"],
                    champion=champ
                )
                db.merge(skin_obj)
        db.commit()
        logger.info("Database seeded successfully!")

