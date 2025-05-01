import os.path
import logging
logger = logging.getLogger(__name__)
from bs4 import BeautifulSoup
from models.models import getApiVersion, Champion, engine
from sqlmodel import select, Session
from typing import List
import requests
from pathlib import Path

def get_filtered_community_dragon_links(api_version: str) -> List[str]:
    """Get filtered list of character directories from Community Dragon"""
    base_url = f"https://raw.communitydragon.org/{api_version}/game/data/characters/"
    response = requests.get(base_url)
    response.raise_for_status()  # Raise exception for bad status codes

    soup = BeautifulSoup(response.text, 'html.parser')

    # Filters to exclude unwanted directories
    exclude_filters = (
        'tft/', 'teamfighttactics', 'teamfight_tactics', "tft", "tutorial",
        "https", "test", "strawberry", "sru", "slime", "poro", "pet",
        "perk", "ultbook", "nexus", "urf", "turret", "srx", "sr_infernal",
        "spellbook", "sonadjg", "npc", "ha_ap_", "durian", "crepe",
        "cherry_", "bw_"
    )

    return [
        link.get('href') for link in soup.find_all('a')
        if link.get('href') and not any(
            filter_word in link.get('href').lower()
            for filter_word in exclude_filters
        )
    ]



def write_to_disk(skin_url:str,skin_dir:str):
    try:
        # Download the skin file
        response = requests.get(skin_url)
        response.raise_for_status()

        # Save to disk
        with open(skin_dir, 'wb') as f:
            f.write(response.content)

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch skin data: {str(e)}")
    except IOError as e:
        logger.error(f"Failed to save file: {str(e)}")
def save_skin_to_disk(champ_id: str, skin_num: str, api_version: str, champ_dir: str) -> None:
    """Download and save skin file to organized directory structure"""
    # Create base directory if it doesn't exist
    skin_dir = Path(f"base_skinsfiles/{api_version}/{champ_id}/{champ_dir}")
    skin_dir.mkdir(parents=True, exist_ok=True)

    # Construct paths
    skin_url = f"https://raw.communitydragon.org/{api_version}/game/data/characters/{champ_dir}/skins/skin{skin_num}.bin"
    base_skin_url= f"https://raw.communitydragon.org/{api_version}/game/data/characters/{champ_dir}/skins/skin0.bin"
    save_path = skin_dir / f"skin{skin_num}.bin"

    logger.info(f"Attempting to fetch skin data from: {skin_url}")
    logger.info(f"Saving to: {save_path}")
    if not os.path.exists(f"{skin_dir}/skin0.bin"):
        write_to_disk(base_skin_url,f"{skin_dir}/skin0.bin")
    write_to_disk(skin_url,save_path)
    logger.info(f"Successfully saved skin {skin_num} for champion {champ_id}")

# Modified version of your function
def get_skin_file(champ_key: str, skin_num: str, db: Session) -> None:
    """Get and save skin files for a specific champion"""
    # Get champion from database
    champ = db.exec(
        select(Champion).where(Champion.id == champ_key)
    ).first()

    if not champ:
        logger.error(f"No champion found with ID {champ_key}")
        return

    # Get API version and adjust format
    api_version = getApiVersion()
    if not api_version:
        logger.error("Could not retrieve API version")
        return

    api_version = api_version[0:-2]  # Remove patch suffix if needed

    # Get filtered character directories
    character_dirs = get_filtered_community_dragon_links(api_version)
    logger.info(len(character_dirs))
    # Find matching champion directory (case-insensitive)
    champ_dirictories =[ d for d in character_dirs if champ.champ_code.lower() in d.lower()]
    if not champ_dirictories:
        logger.error(f"No directory found for champion {champ.champ_code}")
        return

    # Save the skin file
    for champ_dir in champ_dirictories:

        save_skin_to_disk(
            champ_id=champ.id,
            skin_num=skin_num,
            api_version=api_version,
            champ_dir=champ_dir
        )


# Example usage
def download_skin(champ_key:str,skin_num:str):
    with Session(engine) as db:
        get_skin_file(champ_key, skin_num, db)