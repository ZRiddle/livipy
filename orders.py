import os
import re
import shutil

from dataclasses import dataclass
from functools import cached_property
from typing import Optional

from const import Sizes
from dirmap import DirMap


@dataclass
class Order:
    # `Item Name` in csv
    deal_name: str
    # `Size` in csv - todo - is this always filled for non-custom orders?
    size: str
    # `Design` in csv - helps us find file
    design: str
    # `Quantity` in csv
    quantity: int
    # `SKU` in csv
    sku: Optional[str] = None

    # Additional internal states
    _is_copied: bool = False

    def __post_init__(self):
        assert self.size in Sizes.all, f"Bad `size` field. Got {self.size}, expected one of {Sizes.all}"

    def copy_to_temp(self):
        for _ in range(self.quantity):
            self._copy_once()

    def _copy_once(self):
        """Copies the file to the temp folder"""
        i = 0
        filename = os.path.join(self.temp_folder, self.design)
        extension = ".pdf"
        while os.path.exists(filename + "_" + str(i) + extension):
            i += 1

        base_filename = self.guess_filename()
        shutil.copy(base_filename, filename + "_" + str(i) + extension)
        return

    @cached_property
    def temp_folder(self) -> str:
        return os.path.join(DirMap.TEMP_DIR, self.size)

    @cached_property
    def dir(self):
        """
        Returns the directory that the file should be in
        Assumes the format is {DealPath}/{SIZE}/files...
        """
        deal_path = DirMap.get_deal_path(self.deal_name)
        assert self.size in os.listdir(deal_path), f"Error: size folder `{self.size}` not found for deal {self.deal_name}"
        return os.path.join(deal_path, self.size)

    def guess_filename(self) -> str:
        """
        Guess file name based on design name.
        Assumes we already have a working deal folder to look in.

        We're going to use the number to find the file
        Ex: design = `90-Chalkboard Noel`
        We're going to look for a `90-` in the filenames
        """
        if self.design[:3] == "Set":
            return self.design
        design_number = self.design.split("-")[0]
        dir_files = os.listdir(self.dir)

        matches = []
        print(f"Finding matches for design={self.design}")
        for f in dir_files:
            if f" {design_number}-" in f or f"-{design_number}-" in f:
                matches.append(f)
                print(f"  Found match: {f}")

        if len(matches) == 0:
            print(f"Failed. No matches found...")
            return ""
        if len(matches) > 1:
            print(f"Too many matches found: {matches}")

        return matches[0]


if __name__ == "__main__":
    order = Order(
        deal_name="Vintage Christmas Art Prints",
        size="8x10",
        design="16-Forest",
        quantity=2
    )

    files = os.listdir(order.dir)
    print(f"{files=}")

    design_number = order.design.split("-")[0]
    print(f"{design_number=}")

    print(order.guess_filename())
