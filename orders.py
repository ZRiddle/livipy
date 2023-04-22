from __future__ import annotations

import os
import re
import shutil
import string
from dataclasses import dataclass, field
from functools import cached_property
from typing import List, Optional

import pandas as pd
from tabula import read_pdf

from const import Sizes
from dirmap import TEMP_FOLDERS, DirMap


def get_set_size(set_str: str) -> int:
    """
    Extracts the set size from a given string containing the pattern 'Set Of <number>'.
    If it can't find anything then just returns 1.

    Args:
        set_str (str): A string containing the set size in the format 'Set Of <number>'.
                       Additional characters or text may be present before or after the pattern.

    Returns:
        int: The set size as an integer.
    """
    match = re.search(r"Set Of (\d+)", set_str, re.IGNORECASE)
    if match:
        return int(match.group(1))
    else:
        return 1


def filename_lookup(filename: str, dir_list: List[str]) -> Optional[str]:
    """
    Checks if a filename prefix exists in a list of filenames and returns the full filename if found.

    Args:
        filename (str): The filename prefix to search for in the list.
        dir_list (List[str]): A list of filenames.

    Returns:
        Optional[str]: The full filename with the extension if the prefix is found, None otherwise.

    Examples:
        >>> filename_lookup("red", ["red.png", "blue.jpg", "yellow.jpeg"])
        "red.png"
        >>> filename_lookup("blue", ["red.png", "blue.jpg", "yellow.jpeg"])
        "blue.jpg"
        >>> filename_lookup("green", ["red.png", "blue.jpg", "yellow.jpeg"])
        None
    """
    for file in dir_list:
        if os.path.splitext(file)[0] == filename:
            return file
    return None


@dataclass
class Order:
    # `Item Name` in file
    item_name: str
    # `Deal Name` in file
    deal_name: str
    # `Size` in csv - TODO - is this always filled for non-custom orders?
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
    set_size: int = 1
    is_valid: bool = False
    filenames: List[str] = field(default_factory=list)

    def __post_init__(self):
        assert (
            self.size in Sizes.all
        ), f"Bad `size` field. Got {self.size}, expected one of {Sizes.all}"
        self.set_size = get_set_size(self.item_name)
        self.is_set = self.set_size > 1

    @classmethod
    def from_pdf_row(cls, row: pd.Series) -> Order:
        item_name = row.item_name
        deal_name, other = item_name.split("(")
        size, design = other.split(",")
        size = re.sub("\)", "", size.split("Size:")[-1]).strip()
        design = re.sub("\)", "", design.split("Design:")[-1]).strip()

        return cls(
            item_name=item_name.strip(),
            deal_name=deal_name.strip(),
            size=size.strip(),
            design=design.strip(),
            quantity=row.quantity,
            sku=row.sku,
        )

    def copy_to_temp(self):
        if not self.is_valid:
            print(
                f" ❌ [SKIP] {self.quantity}x  {self.size} {self.sku} {self.design}, missing files!"
            )
            return
        print(f" ✅ [COPY] {self.quantity}x  {self.size} {self.sku} {self.design}")
        for _ in range(self.quantity):
            self._copy_once()

    def _copy_once(self):
        """Copies the file to the temp folder"""
        for f in self.filenames:
            i = 1
            fname, ext = f.split(".")
            while os.path.exists(
                os.path.join(self.temp_folder, fname + f"_{str(i)}." + ext)
            ):
                i += 1
            shutil.copy(
                os.path.join(DirMap.SKU_DIR, f),
                os.path.join(self.temp_folder, fname + f"_{str(i)}." + ext),
            )
        return

    @cached_property
    def temp_folder(self) -> str:
        return os.path.join(DirMap.TEMP_DIR, self.size)

    def _print_valid(self, filename: Optional[str]):
        valid_str = "✅" if filename is not None else "❌"
        print(f" {valid_str} {self.sku} = {filename}")

    def _print_valid_set(self, valid_list: List[Optional[str]]):
        valid_str = " ".join(
            ["✅" if filename is not None else "❌" for filename in valid_list]
        )
        print(f" {valid_str} {self.sku} Set Of {self.set_size}")

    def confirm_filename(self) -> bool:
        """Look for filename(s) in dir"""
        # TODO - this logic should work without splitting on self.is_set
        if self.is_set:
            for i in range(self.set_size):
                self.filenames.append(
                    filename_lookup(
                        self.sku + string.ascii_lowercase[i], DirMap.SKU_DIR_FILENAMES
                    )
                )
            self._print_valid_set(self.filenames)
        else:
            self.filenames.append(filename_lookup(self.sku, DirMap.SKU_DIR_FILENAMES))
            self._print_valid(self.filenames[0])

        self.is_valid = all(self.filenames)
        return all(self.filenames)

    def __repr__(self):
        return f"<Order> Q={self.quantity}\tS={self.size}\t  {self.deal_name} | {self.design}"

    # def guess_set_filenames(self, verbose: bool = False) -> List[str]:
    #     """
    #     Guess filenames for a set of 3.
    #     Assumes they are of the form `* {SET_NUMBER}{a|b|c}*`
    #     """
    #     design_number = self.design.split(" ")[-1].strip()
    #     dir_files = os.listdir(self.dir)
    #     matches: List[str] = []
    #     for f in dir_files:
    #         if (
    #             f" {design_number}a" in f
    #             or f" {design_number}b" in f
    #             or f" {design_number}c" in f
    #             or f" {design_number}.jpg" in f
    #             or f" {design_number}.pdf" in f
    #         ):
    #             matches.append(f)
    #             if verbose:
    #                 print(f"  Found match: {f}")
    #     return matches

    # def guess_filenames(self, verbose: bool = False) -> List[str]:
    #     """
    #     Guess file name based on design name.
    #     Assumes we already have a working deal folder to look in.
    #
    #     We're going to use the number to find the file
    #     Ex: design = `90-Chalkboard Noel`
    #     We're going to look for a `90-` in the filenames
    #     """
    #     if self.design[:3] == "Set":
    #         return self.guess_set_filenames(verbose)
    #     design_number = self.design.split("-")[0]
    #     dir_files = os.listdir(self.dir)
    #
    #     matches: List[str] = []
    #     if verbose:
    #         print(f"Finding matches for design={self.design}")
    #     for f in dir_files:
    #         match_str = f"{design_number}"
    #         if (
    #             f" {match_str}-" in f
    #             or f"-{match_str}-" in f
    #             or f[: len(match_str)] == match_str
    #             or f" {match_str}.jpg" in f
    #             or f" {match_str}.pdf" in f
    #             or f"-{match_str}.jpg" in f
    #             or f"-{match_str}.pdf" in f
    #         ):
    #             matches.append(f)
    #             if verbose:
    #                 print(f"  Found match: {f}")
    #
    #     if len(matches) == 0:
    #         if verbose:
    #             print(f"Failed. No matches found...")
    #         return matches
    #     if len(matches) > 1 and not self.is_set:
    #         if verbose:
    #             print(f"Too many matches found: {matches}")
    #
    #     return matches


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
                item_name=row["Item Name"],
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
        item_name="Vintage Christmas Art Prints",
        deal_name="Vintage Christmas Art Prints",
        size="8x10",
        design="16-Forest",
        quantity=2,
        sku="BOHOMD77",
    )

    files = os.listdir(DirMap.SKU_DIR)
    print(f"{files=}")

    design_number = order.design.split("-")[0]
    print(f"{design_number=}")

    # print(order.guess_filenames())
