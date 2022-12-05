import glob
import os

from const import Sizes

_MAP_FILE = "mapping.txt"
TEMP_FOLDERS = Sizes.all


def _build_map_from_file(map_file: str = _MAP_FILE):
    with open(map_file, "r") as f:
        _map_txt = f.read()

    rows = _map_txt.split("\n")
    rows_split = [row.split("=") for row in rows if "=" in row]
    return {deal: path_ for deal, path_ in rows_split}


class DirMap:
    PRINTABLES: str = "Documents/Liviloudes PH/Printables"
    BASE_DIR = os.path.join(os.path.expanduser("~"), PRINTABLES)
    TEMP_DIR = os.path.join(BASE_DIR, "_temp")
    _mapping = _build_map_from_file()

    @classmethod
    def get_deal_path(cls, deal_name: str) -> str:
        """
        return a full path to the deal_name folder.
        print out mapping instructions if not exists.

        :param deal_name:
        :return:
        """
        if deal_name in cls._mapping:
            return os.path.join(cls.BASE_DIR, cls._mapping[deal_name])

        # Check deal_name exists in base dir
        deal_path_exists = deal_name in os.listdir(cls.BASE_DIR)
        assert deal_path_exists, (
            f"\n\nDeal path `{deal_name}/` not found in {cls.PRINTABLES}/\n"
            f"Run this to add a new row in the mapping\n> ct map '{deal_name}=path_to_dealname'"
        )

        return os.path.join(cls.BASE_DIR, deal_name)

    @classmethod
    def append_to_map(cls, row_str: str):
        assert "=" in row_str, f"new row needs a `=`, got {row_str}"
        name, path = row_str.split("=")
        full_path = os.path.join(cls.BASE_DIR, path)
        # Make sure the path exists
        assert os.path.exists(full_path), f"Folder doesn't exist: {full_path}"

        with open(_MAP_FILE, "a") as f:
            f.write(row_str + "\n")

    @classmethod
    def downloads_folder(cls) -> str:
        return os.path.join(os.path.expanduser("~"), "Downloads")

    @classmethod
    def get_latest_file(cls, folder: str, filetype: str = "pdf") -> str:
        filetype = filetype.replace(".", "")  # remove any `.`
        list_of_files = glob.glob(f"{folder}/*.{filetype}")
        return max(list_of_files, key=os.path.getmtime)

    @classmethod
    def setup_temp_folders(cls):
        if not os.path.exists(cls.TEMP_DIR):
            print(f"temp dir not found. Creating temp dir at: {cls.TEMP_DIR}")
            os.mkdir(cls.TEMP_DIR)

        for tmp in TEMP_FOLDERS:
            dir = os.path.join(cls.TEMP_DIR, tmp)
            if not os.path.exists(dir):
                os.mkdir(dir)

    @classmethod
    def clear_temp_folders(cls, verbose: bool = True):
        cls.setup_temp_folders()
        for tmp in TEMP_FOLDERS:
            dir = os.path.join(cls.TEMP_DIR, tmp)
            if verbose:
                print(f"{dir}\t - deleting {len(os.listdir(dir))} files")
            for f in os.listdir(dir):
                os.remove(os.path.join(dir, f))


if __name__ == "__main__":
    print(DirMap._mapping)
