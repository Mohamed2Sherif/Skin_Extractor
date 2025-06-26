import datetime
import os
import pickle
import asyncio
from test_skin_exist import main, bugged_skins
from typing import Dict, Tuple
import requests
from sqlalchemy.orm import selectinload
from bs4 import BeautifulSoup
from extractor import process_character_directory, get_script_dir
from models.models import getApiVersion, seed_database, Champion
from sqlmodel import Session, select
import logging

logger = logging.getLogger(__name__)
from skin_file_fetcher import download_skin
import concurrent.futures


class CDNSkinHashSet:
    def __init__(self):
        self.binary_data = os.path.join(os.path.dirname(__file__), "cache.bin")
        try:
            with open(self.binary_data, "rb") as f:
                self.skin_Version_LastUpdateMap: Dict[
                    str, Tuple[str, datetime.datetime]
                ] = pickle.load(f)
        except (pickle.UnpicklingError, EOFError, FileNotFoundError):
            self.skin_Version_LastUpdateMap: Dict[
                str, Tuple[str, datetime.datetime]
            ] = {}

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

    # def start_updating_cdn(self):
    #     self.Champions_list = self.db.exec(select(Champion).options(selectinload(Champion.skins))).all()
    #     map = self.cdnMap.get_skinSet()
    #     script_dir = get_script_dir()
    #     pool = concurrent.futures.ThreadPoolExecutor(max_workers=8)
    #     for champ in self.Champions_list:
    #         # Check if at least one skin is unprocessed
    #         unprocessed_skins = [
    #             skin for skin in champ.skins
    #             if skin.id != "0" and (
    #                     (entry := map.get(f"{champ.id}_{skin.id}")) is None or entry[0] != self.apiVersion
    #             )
    #         ]
    #
    #         limit = 10
    #         if unprocessed_skins:
    #             # Process all skins for this champion
    #             for skin in unprocessed_skins:
    #                 if limit > 0:
    #                     pool.submit(self.extract_remote_skin,champ, script_dir, skin)
    #                     # limit -= 1 #comment this if you want to update all the files
    #                 else:
    #                     break
    #             #break  # Stop after processing one champion
    #     self.cdnMap.save_skinSet()
    async def start_updating_cdn(self):
        await main()  # Run the async check first
        map = self.cdnMap.get_skinSet()

        script_dir = get_script_dir()
        # Use a proper session context
        print(bugged_skins)
        for champ_name, skin_name in bugged_skins:
            # Get champion with skins eagerly loaded
            print(champ_name)
            champion = self.db.exec(
                select(Champion)
                .where(Champion.champ_name == champ_name)
                .options(selectinload(Champion.skins))
            ).first()

            if champion:
                for skin_record in champion.skins:
                    if skin_record.skin_name == skin_name and (
                        (entry := map.get(f"{champion.id}_{skin_record.id}")) is None
                        or entry[0] != self.apiVersion
                    ):  # Fixed comparison
                        self.extract_remote_skin(champion, script_dir, skin_record)
                        break
                else:
                    logger.warning(f"Skin not found: {champ_name} - {skin_name}")
            else:
                logger.warning(f"Champion not found: {champ_name}")
        self.cdnMap.save_skinSet()

    def extract_remote_skin(self, champ, script_dir, skin):
        download_skin(champ.id, skin.id)
        process_character_directory(script_dir, champ.id, skin.id, self.apiVersion)
        self.cdnMap.update_cdn_entry(champ.id, skin.id, self.apiVersion)


class HashUpdateManager:
    def __init__(self):
        self.url = "https://raw.communitydragon.org/data/hashes/lol/"

    def update_hashes(self):
        # Stream the HTML response to avoid buffering large content in memory
        with requests.get(self.url) as response:
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")  # use raw stream

        script_dir = get_script_dir()
        hashes_dirs = [
            os.path.join(script_dir, "linux_binaries", "hashes"),
            os.path.join(script_dir, "hashes"),
        ]
        for dir_path in hashes_dirs:
            os.makedirs(dir_path, exist_ok=True)

        hashes_list = [
            self.url + link.get("href")
            for link in soup.find_all("a")
            if link.get("href") and not link.get("href").startswith("..")
        ]

        for hash_file_link in hashes_list:
            file_name = hash_file_link.split("/")[-1]
            with requests.get(hash_file_link, stream=True) as file_response:
                file_response.raise_for_status()
                file_content = b""
                for chunk in file_response.iter_content(chunk_size=8192):
                    if chunk:
                        file_content += chunk
                file_text = file_content.decode("utf-8")
                for dir_path in hashes_dirs:
                    dest_path = os.path.join(dir_path, file_name)
                    with open(dest_path, "w", encoding="utf-8") as hash_file:
                        hash_file.write(file_text)
