import asyncio
import os
import logging
import subprocess

from sqlmodel import Session
from UpdateManager import UpdateManager, HashUpdateManager
logger = logging.getLogger(__name__)
from fastapi import FastAPI, BackgroundTasks
from fastapi.responses import FileResponse
from extractor import process_skin_folder, process_character_directory, get_script_dir
from models.models import create_db_and_tables, SessionDep, seed_database, getApiVersion, engine
from skin_file_fetcher import download_skin
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from fastapi import FastAPI
from contextlib import asynccontextmanager

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting database initialization")
    create_db_and_tables()
    logger.info("Starting database seeding")
    seed_database()
    if os.environ.get("Environment") != "Development":
        subprocess.Popen(["wineserver", "-p"])
    await background_hashes_update()
    # Configure scheduler with persistent jobstore
    jobstores = {
        'default': SQLAlchemyJobStore(
            url=os.getenv("SCHEDULER_DATABASE_URL")
        )
    }

    # Create scheduler with jobstore configuration
    scheduler = AsyncIOScheduler(jobstores=jobstores)

    # Add the hourly job
    scheduler.add_job(
        background_update_process,
        trigger=IntervalTrigger(minutes=4),
        id='hourly_api_update',  # Unique ID for the job
        replace_existing=True,  # Will replace existing job with same ID
        max_instances=1
    )
    scheduler.add_job(
        background_hashes_update,
        trigger=IntervalTrigger(days=1),
        id='daily_hashes_update',  # Unique ID for the job
        replace_existing=True,  # Will replace existing job with same ID
        max_instances=1
    )
    # Start scheduler
    scheduler.start()
    logger.info("Scheduler started with persistent job storage")

    yield

    # Shutdown
    scheduler.shutdown(wait=False)
    if os.environ.get("Environment") != "Development":
        subprocess.run(["wineserver", "-k"])

    logger.info("Scheduler stopped")


app = FastAPI(lifespan=lifespan)


async def background_hashes_update():
    try:
        logger.info("Starting scheduled Hashes update process...")

        hash_updater = HashUpdateManager()
        hash_updater.update_hashes()
    except Exception as e:
        logger.error(f"Error in Hashes update process: {e}")


async def background_update_process():
    try:
        logger.info("Starting scheduled update process...")

        with Session(engine) as db:
            try:
                update_manager = UpdateManager(db)
                update_manager.pull_changes_from_riot_api()
                update_manager.start_updating_cdn()
            except Exception as db_error:
                logger.error(f"Database operation failed: {db_error}")
                raise

        logger.info("Update completed successfully")

    except Exception as e:
        logger.error(f"Error in update process: {e}")
        # The scheduler will retry at next interval


@app.get("/health")
async def root():
    return {"service is running in healty state ........"}


@app.get("/skin/{champId}/{skinId}")
async def get_skin(champId: str, skinId: str):
    file_path = ""
    script_dir = get_script_dir()
    api_version = getApiVersion()[:-2]
    if os.path.exists(os.path.join(script_dir, "cdn", champId, f"{skinId}.wad.client")):
        file_path = os.path.join(script_dir, "cdn", champId, f"{skinId}.wad.client")
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
        file_path = os.path.join(script_dir, "cdn", champId, f"{skinId}.wad.client")
        return FileResponse(
            path=file_path,
            filename=f"{skinId}.wad.client",  # name user sees when saving
            media_type='application/octet-stream'  # generic binary type
        )


@app.get("party/accessToken/{rooomId}")
async def join_party(roomId: str):
    return "sdfsdf"
