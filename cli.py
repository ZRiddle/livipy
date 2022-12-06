#!/usr/bin/env python
import os
import time
from typing import Optional

import click

from dirmap import DirMap
from orders import OrderList


@click.group()
def cli():
    pass


def get_time_diff_string(download_time: float) -> str:
    secs = time.time() - download_time
    days, rem = divmod(secs, 86400)  # Get days (without [0]!)
    hours, rem = divmod(rem, 3600)  # Use remainder of days to calc hours
    minutes, rem = divmod(rem, 60)  # Use remainder of hours to calc minutes
    seconds, rem = divmod(rem, 1)

    output = ""
    if days:
        output += f"{int(days)}d "
    if days or hours:
        output += f"{int(hours)}h "
    if days or hours or minutes:
        output += f"{int(minutes)}m "
    output += f"{int(seconds)}s ago"
    return output


@cli.command("clear")
@click.option("--verbose", "-v", is_flag=True)
def clear_temp_folders(verbose: bool):
    """Clear out the temp folders"""
    if not click.confirm("\nDelete ALL temp files?", default=True):
        print(f"Aborting...\n")
        return
    print(f"Clearing temp folders...")
    DirMap.clear_temp_folders()  # TODO - add verbose
    print(f"All folders cleared in {DirMap.TEMP_DIR}")
    print(f"\nSuccess!\n")


@cli.command("copy")
@click.option("--filename", "-f", default=None)
@click.option("--filetype", "-t", default="pdf")
def copy_files(filename: Optional[str], filetype: str):
    """Copy files based on a pdf in the Downloads/ folder.
    Currently, assume the file is in the Downloads folder.
    If nothing is specified then get the latest .csv file"""
    if not filename:
        filename = DirMap.get_latest_file(DirMap.downloads_folder(), filetype=filetype)
        base_filename = filename.split("/")[-1]
        print(
            f"No filename specified. Using latest {filetype} file in Downloads/\n"
            f"   {base_filename} - Downloaded {get_time_diff_string(os.path.getmtime(filename))}"
        )
    if not os.path.exists(filename):
        filename = os.path.join(DirMap.downloads_folder(), filename)
    print(f"Copying files to temp folders based on {filename}")

    order_list = OrderList.from_file(filename)
    order_list.print_orders()

    print(f"\nConfirming filenames")
    error_count = order_list.confirm_filenames()
    if not click.confirm(f"\nContinue with {error_count} errors", default=True):
        print(f"Aborting...\n")
        return
    print("\nCopying files to temp folder...")
    order_list.copy_all()
    print(f"\nSuccess!\n")


@cli.command("map")
@click.argument("row")
def add_map(row: str):
    """Add a mapping of a deal name to a folder from Printables/"""
    print(f"Adding row to mapping")
    DirMap.append_to_map(row)
    print(f"\nSuccess!\n")


if __name__ == "__main__":
    cli()
