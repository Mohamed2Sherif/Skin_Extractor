import asyncio
from sqlmodel import select, SQLModel, create_engine,Session
from sqlalchemy.orm import selectinload
from models.models import Champion,engine  # Assuming Champion is defined in models
import logging
from aiohttp import ClientSession, ClientTimeout

bugged_skins = []
# Configure logging
logging.basicConfig(
    level=logging.ERROR,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='skin_errors.log',
    filemode='a'
)
logger = logging.getLogger(__name__)


async def check_skin_exists(session: ClientSession, champ_name: str, skin_name: str):
    skin_path = f"skins/{champ_name}/{skin_name.replace('/', ' ').replace(':', '')}.zip"
    url = f"https://raw.githubusercontent.com/darkseal-org/lol-skins/main/{skin_path}"

    try:
        async with session.head(url, allow_redirects=True) as response:
            if response.status != 200:
                bugged_skins.append((champ_name,skin_name))
                return False
            return True
    except Exception as e:
        logger.error(f"{champ_name} - {skin_name} - Error: {str(e)}")
        return False


async def process_skins(champions, http_session):
    tasks = []
    for champ in champions:
        for skin in champ.skins:
            if skin.skin_name != "default":
                tasks.append(
                    check_skin_exists(
                        http_session,
                        champ.champ_name,
                        skin.skin_name
                    )
                )
    await asyncio.gather(*tasks)


async def main():
    # Load all data synchronously (better for SQLite)
    with Session(engine) as db:
        champions = db.exec(
            select(Champion)
            .options(selectinload(Champion.skins))
        ).all()

    # Process HTTP requests asynchronously
    async with ClientSession(
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=ClientTimeout(total=10)
    ) as http_session:
        await process_skins(champions, http_session)
