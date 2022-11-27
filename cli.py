#!/usr/bin/env python
from typing import Optional
from dirmap import DirMap

import click


@click.group()
def cli():
    pass


@cli.command("clear")
@click.option("--verbose", "-v", is_flag=True)
def clear_temp_folders(verbose: bool):
    print(f"Clearing temp folders...")
    DirMap.clear_temp_folders()  # TODO - add verbose
    print(f"All folders cleared in {DirMap.TEMP_DIR}")


@cli.command("copy")
@click.option("--filename", "-f", default=None)
def copy_files(filename: Optional[str]):
    """Currently assume the file is in the Downloads folder.
    If nothing is specified then get the latest .csv file"""
    if not filename:
        print(f"No filename passed in. Using latest .csv file in Downloads/")
        filename = DirMap.get_latest_file(DirMap.downloads_folder())
    print(f"Copying files to temp folder based on {filename}")


if __name__ == "__main__":
    cli()
