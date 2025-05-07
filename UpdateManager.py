import datetime
import os
import pickle
from typing import Dict, Tuple

from sqlalchemy.orm import selectinload

from extractor import process_character_directory, get_script_dir
from models.models import getApiVersion, seed_database, Champion
from sqlmodel import Session, select

from skin_file_fetcher import download_skin


class CDNSkinHashSet:
    def __init__(self):
        self.binary_data = os.path.join(os.path.dirname(__file__), "cache.bin")
        try:
            with open(self.binary_data, "rb") as f:
                self.skin_Version_LastUpdateMap: Dict[str, Tuple[str, datetime.datetime]] = pickle.load(f)
        except (pickle.UnpicklingError, EOFError, FileNotFoundError):
            self.skin_Version_LastUpdateMap: Dict[str, Tuple[str, datetime.datetime]] = {}

    def get_skinSet(self) -> Dict[str, Tuple[str, datetime.datetime]]:
        return self.skin_Version_LastUpdateMap

    def update_cdn_entry(self, champ_num: str, skin_Num: str, apiVersion: str) -> None:
        key = f"{champ_num}_{skin_Num}"
        self.skin_Version_LastUpdateMap[key] = (apiVersion, datetime.datetime.utcnow())

    def save_skinSet(self) -> None:
        with open(self.binary_data, "wb") as f:
            pickle.dump(self.skin_Version_LastUpdateMap, f)


class UpdateManager:
    def __init__(self, session: Session):
        self.cdnMap = CDNSkinHashSet()
        self.db = session
        self.apiVersion = getApiVersion()[:-2]
    def pull_changes_from_riot_api(self):
        seed_database()
    def start_updating_cdn(self):
        self.Champions_list = self.db.exec(select(Champion).options(selectinload(Champion.skins))).all()
        map = self.cdnMap.get_skinSet()
        script_dir = get_script_dir()

        for champ in self.Champions_list:
            # Check if at least one skin is unprocessed
            unprocessed_skins = [
                skin for skin in champ.skins
                if skin.id != "0" and (
                        (entry := map.get(f"{champ.id}_{skin.id}")) is None or entry[0] != self.apiVersion
                )
            ]

            limit=10
            if unprocessed_skins:
                # Process all skins for this champion
                for skin in unprocessed_skins:
                    if limit>0:
                        download_skin(champ.id, skin.id)
                        process_character_directory(script_dir, champ.id, skin.id, self.apiVersion)
                        self.cdnMap.update_cdn_entry(champ.id,skin.id,self.apiVersion)
                        limit-=1
                    else:break
                break  # Stop after processing one champion
        self.cdnMap.save_skinSet()






