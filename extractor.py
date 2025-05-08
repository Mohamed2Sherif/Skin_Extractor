import logging
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
logger = logging.getLogger(__name__)
import json
import shutil
from sys import api_version
from typing import Dict, Any, Optional, List
from models.models import getApiVersion
from dotenv import load_dotenv
from concurrent.futures import as_completed

load_dotenv("./.env")
api_version = getApiVersion()
api_version = api_version[:-2]


def get_script_dir():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    return script_dir


def executer() -> str:
    if os.environ.get("Environment") == "Development":
        return ""
    else:
        return "wine"

def run_process(cmd: List[str], timeout: float = 30.0):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
        if proc.returncode != 0:
            raise subprocess.CalledProcessError(proc.returncode, cmd, output=stdout, stderr=stderr)
        return stdout
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning(f"Force killing process {cmd}")
            proc.kill()
            proc.wait()
        raise RuntimeError(f"Process timed out: {cmd}")
    except Exception as e:
        proc.kill()
        proc.wait()
        raise e

def run_ritobin(scriptdir: str, filename: str, output_extension: str):
    cmd = [os.path.join(scriptdir, "ritobin.exe"), filename, "-o", output_extension]
    exe = executer()
    if exe:
        cmd.insert(0, exe)
    run_process(cmd)


def read_json_file(filename: str) -> Dict[str, Any]:
    """Read and parse a JSON file."""
    try:
        with open(f"{filename}.json", "r") as file:
            return json.load(file)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error reading JSON file: {e}")
        raise


def write_json_file(filename: str, data: Dict[str, Any]) -> None:
    """Write data to a JSON file."""
    with open(f"{filename}.json", "w") as writefile:
        json.dump(data, writefile, indent=2)


def get_resource_resolver(data: Dict[str, Any]) -> Optional[str]:
    """Extract the ResourceResolver key from skin data."""
    items = data["entries"]["value"]["items"]
    if items[-1]["value"]["name"] == "ResourceResolver":
        return items[-1]["key"]

    for obj in items:
        if obj["value"]["name"] == "ResourceResolver":
            return obj["key"]
    return None


def process_skin_folder_wrapper(args: tuple) -> None:
    """Wrapper for skin folder processing. using multithreading"""
    scriptdir, champion_key, folder_path, skin_number = args
    process_skin_folder(scriptdir, champion_key, folder_path, skin_number)


def process_skin_folder(scriptdir: str, championkey: str, folder_path: str, skin_number: str) -> None:
    """Process a skin folder containing skin and animation files."""
    base_skin = 0
    os.path.join(folder_path, )
    # Process base skin first if it exists
    if not os.path.exists(os.path.join(folder_path, "skinbase.json")
                          ) and os.path.exists(os.path.join(folder_path, f"skin{base_skin}.bin")
                                               ):
        try:
            run_ritobin(scriptdir, os.path.join(folder_path, f"skin{base_skin}.bin")
                        , "json")
            shutil.copy(os.path.join(folder_path, f"skin{base_skin}.json"), os.path.join(folder_path, "skinbase.json"))
        except subprocess.CalledProcessError as e:
            logger.error(f"Error processing base skin: {e}")
            return
    # Load base data
    base_data = (
        read_json_file(os.path.join(folder_path, "skinbase"))
        if os.path.exists(os.path.join(folder_path, "skinbase.json"))
        else read_json_file(os.path.join(folder_path, f"skin{base_skin}"))
    )
    base_skin_title = base_data["entries"]["value"]["items"][0]["key"]
    base_skin_resources = get_resource_resolver(base_data)
    original_skin_number = skin_number

    try:
        logger.info(f"Processing {os.path.basename(os.getcwd())}/{skin_number}...")
        if os.path.exists(os.path.join(folder_path, f"skin{skin_number}.bin")):
            run_ritobin(scriptdir, os.path.join(folder_path, f"skin{skin_number}.bin"), "json")

            # Load and modify skin data
            json_file = os.path.join(folder_path, f"skin{skin_number}.json")
            if os.path.exists(json_file):
                skin_data = read_json_file(json_file[:-5])  # Remove .json extension
                skin_data["entries"]["value"]["items"][0]["key"] = base_skin_title

                if base_skin_resources:
                    items = skin_data["entries"]["value"]["items"]
                    if items[-1]["value"]["name"] == "ResourceResolver":
                        items[-1]["key"] = base_skin_resources
                    else:
                        for obj in items:
                            if obj["value"]["name"] == "ResourceResolver":
                                obj["key"] = base_skin_resources

                # Write modified data to base skin and convert back to bin
                write_json_file(os.path.join(folder_path, f"skin{base_skin}"), skin_data)
                run_ritobin(scriptdir, os.path.join(folder_path, f"skin{base_skin}.json"), "bin")
                os.remove(json_file)
                os.remove(os.path.join(folder_path, "skin0.json"))
                parent_dir_name = os.path.basename(folder_path)

        write_modified_skin_to_output_dir(
            scriptdir, championkey, parent_dir_name, original_skin_number, folder_path
        )
        # Clean up temporary files

    except (
            FileNotFoundError,
            json.JSONDecodeError,
            subprocess.CalledProcessError,
    ) as e:
        logger.error(f"Error processing {skin_number}: {e}")


def process_character_directory(scriptdir: str, champion_key: str, skin_number: str, apiVersion: str) -> None:
    """Process a character directory containing skin and animation folders."""
    char_dir = f"{scriptdir}/base_skinsfiles/{apiVersion}/{champion_key}"
    if not os.path.exists(char_dir):
        logger.error("Path does not exist!")
    skin_folders = [
        os.path.join(char_dir, folder)
        for folder in os.listdir(char_dir)
        if os.path.isdir(os.path.join(char_dir, folder))
    ]
    args_list = [(scriptdir, champion_key, folder, skin_number) for folder in skin_folders]

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(process_skin_folder_wrapper, args) for args in args_list]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error in processing skin folder: {e}")
    archive_source = os.path.join(
        scriptdir,
        "output",
        api_version,
        champion_key,
        skin_number,
    )
    info = os.path.join(archive_source, "Meta")
    if not os.path.exists(info):
        os.makedirs(info)
    shutil.copy(os.path.join(scriptdir, "info.json"), info)
    write_to_server_cdn(scriptdir, archive_source, champion_key, skin_number)


def write_modified_skin_to_output_dir(scriptdir: str, champ_key: str, champ_name: str, skin_num: str, folder_path: str):
    try:
        output_dir = os.path.join(
            scriptdir,
            "output",
            api_version,
            champ_key,
            skin_num,
            "data",
            "characters",
            champ_name
            , "skins"
        )
        # archive_source = os.path.join(
        #     scriptdir,
        #     "output",
        #     api_version,
        #     champ_key,
        #     skin_num,
        # )
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        if not os.path.exists(os.path.join(folder_path, f"skin0.bin")):
            logger.error(f"Error: Could not find skin0.bin in {folder_path}")
            return
        if not os.path.exists(os.path.join(output_dir, f"skin0.bin")):
            shutil.copy(
                os.path.join(folder_path, f"skin0.bin"), os.path.join(output_dir, f"skin0.bin")
            )
        # info = os.path.join(archive_source, "Meta")
        # if not os.path.exists(info):
        #     os.makedirs(info)
        # shutil.copy(os.path.join(scriptdir, "info.json"), info)
        # write_to_server_cdn(scriptdir, archive_source, champ_key, skin_num)
        return
    except Exception as error:
        logger.error(error)


def write_to_server_cdn(base_dir: str, dir: str, champKey: str, skinNum: str):
    output_path = os.path.join(base_dir, "cdn", champKey, skinNum)
    wadmake_path = os.path.join(base_dir, "wad-make.exe")
    output_file = f"{output_path}.wad.client"

    cmd = [wadmake_path, dir, output_file]
    exe = executer()
    if exe:
        cmd.insert(0, exe)
    run_process(cmd)