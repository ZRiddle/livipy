from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from functools import cached_property
from typing import List, Optional

import pandas as pd
from tabula import read_pdf

from const import Sizes
from dirmap import TEMP_FOLDERS, DirMap


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
    is_set: bool = False
    is_valid: bool = False

    def __post_init__(self):
        assert (
            self.size in Sizes.all
        ), f"Bad `size` field. Got {self.size}, expected one of {Sizes.all}"
        self.is_set = self.design[:6].lower() == "set of"

    @classmethod
    def from_pdf_row(cls, row: pd.Series) -> Order:
        item_name = row.item_name
        deal_name, other = item_name.split("(")
        size, design = other.split(",")
        size = re.sub("\)", "", size.split("Size:")[-1]).strip()
        design = re.sub("\)", "", design.split("Design:")[-1]).strip()

        return cls(
            deal_name=deal_name.strip(),
            size=size.strip(),
            design=design.strip(),
            quantity=row.quantity,
            sku=row.sku,
        )

    def copy_to_temp(self):
        if not self.is_valid:
            print(f" ❌ [SKIP] {self.quantity}x  {self.design}, bad filename")
            return
        print(f" ✅ [COPY] {self.quantity}x  {self.design}")
        for _ in range(self.quantity):
            self._copy_once()

    def _copy_once(self):
        """Copies the file to the temp folder"""
        i = 1
        extension = ".pdf"
        while os.path.exists(
            os.path.join(self.temp_folder, self.design + "_" + str(i) + extension)
        ):
            i += 1

        base_filenames = self.guess_filenames()
        for f in base_filenames:
            shutil.copy(
                os.path.join(self.dir, f),
                os.path.join(self.temp_folder, self.design + "_" + str(i) + extension),
            )
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
        assert self.size in os.listdir(
            deal_path
        ), f"\nSize folder `{self.size}` not found in deal folder: `{self.deal_name}/`\n"
        return os.path.join(deal_path, self.size)

    def guess_set_filenames(self, verbose: bool = False) -> List[str]:
        """
        Guess filenames for a set of 3.
        Assumes they are of the form `* {SET_NUMBER}{a|b|c}*`
        """
        design_number = self.design.split(" ")[-1].strip()
        dir_files = os.listdir(self.dir)
        matches: List[str] = []
        for f in dir_files:
            if (
                f" {design_number}a" in f
                or f" {design_number}b" in f
                or f" {design_number}c" in f
            ):
                matches.append(f)
                if verbose:
                    print(f"  Found match: {f}")
        return matches

    def guess_filenames(self, verbose: bool = False) -> List[str]:
        """
        Guess file name based on design name.
        Assumes we already have a working deal folder to look in.

        We're going to use the number to find the file
        Ex: design = `90-Chalkboard Noel`
        We're going to look for a `90-` in the filenames
        """
        if self.design[:3] == "Set":
            return self.guess_set_filenames(verbose)
        design_number = self.design.split("-")[0]
        dir_files = os.listdir(self.dir)

        matches: List[str] = []
        if verbose:
            print(f"Finding matches for design={self.design}")
        for f in dir_files:
            match_str = f"{design_number}-"
            if (
                f" {match_str}" in f
                or f"-{match_str}" in f
                or f[: len(match_str)] == match_str
            ):
                matches.append(f)
                if verbose:
                    print(f"  Found match: {f}")

        if len(matches) == 0:
            if verbose:
                print(f"Failed. No matches found...")
            return matches
        if len(matches) > 1 and not self.is_set:
            if verbose:
                print(f"Too many matches found: {matches}")

        return matches

    def confirm_filename(self) -> bool:
        """Look for filename(s) in dir"""
        filename_guesess = self.guess_filenames(False)
        valid_len = False
        if len(filename_guesess) == 1 and not self.is_set:
            valid_len = True
            self.is_valid = True
        elif len(filename_guesess) == 3 and self.is_set:
            valid_len = True
            self.is_valid = True

        valid_str = "✅" if valid_len else "❌"
        if self.is_set or len(filename_guesess) == 0 or not valid_len:
            print(f" {valid_str} {self.design} = {filename_guesess}")
        else:
            print(f" {valid_str} {self.design} = {filename_guesess[0]}")
        return valid_len

    def __repr__(self):
        return f"<Order> Q={self.quantity}\tS={self.size}\t  {self.deal_name} | {self.design}"


class OrderList:
    def __init__(self, orders: List[Order]):
        self.orders = orders

    @classmethod
    def from_file(cls, filename: str) -> OrderList:
        filetype = filename[-3:]
        if filetype == "pdf":
            return cls.from_pdf(filename)
        if filetype == "csv":
            return cls.from_csv(filename)

    @classmethod
    def from_pdf(cls, filename) -> OrderList:
        orders: List[Order] = []
        cols = ["bin", "quantity", "sku", "item_name", "picked"]
        df = pd.concat(
            read_pdf(
                filename, pages="all", pandas_options={"header": None, "names": cols}
            )
        )
        for i, row in df.iterrows():
            orders.append(Order.from_pdf_row(row))
        return cls(orders)

    @classmethod
    def from_csv(cls, filename) -> OrderList:
        orders: List[Order] = []
        df = pd.read_csv(filename)
        for i, row in df.iterrows():
            new_order = Order(
                deal_name=row["Item Name"],
                size=row["Size"],
                design=row["Design"],
                quantity=row["Quantity"],
                sku=row["SKU"],
            )
            orders.append(new_order)

        return cls(orders)

    def print_orders(self):
        print(f"\nLoaded {len(self.orders)} rows")
        for order in self.orders:
            print(f" {order}")

    def confirm_filenames(self) -> int:
        """Returns a count of rows that are invalid"""
        valid: List[bool] = []
        for order in self.orders:
            valid.append(order.confirm_filename())
        return sum([not v for v in valid])

    def copy_all(self):
        for order in self.orders:
            order.copy_to_temp()

        print(f"\nCurrent temp file counts:")
        for tmp in TEMP_FOLDERS:
            dir = os.path.join(DirMap.TEMP_DIR, tmp)
            print(f" {tmp}\t{len(os.listdir(dir))} files")


if __name__ == "__main__":
    order = Order(
        deal_name="Vintage Christmas Art Prints",
        size="8x10",
        design="16-Forest",
        quantity=2,
    )

    files = os.listdir(order.dir)
    print(f"{files=}")

    design_number = order.design.split("-")[0]
    print(f"{design_number=}")

    print(order.guess_filenames())
