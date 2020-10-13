import csv
from collections import defaultdict
from typing import Dict, DefaultDict
from glob import glob
from os.path import basename, splitext

# Tangrams are encoded with RYB for colors, and white triangles are:
# PU
# DS
# With the "point" of the white triangle indicating which letter it is.
# (Mnemonic is rotate counterclockwise 45 degrees, and you have up, starboard, down, port)

ARROW_OPPOSITES = {
    "P": "S",
    "U": "D",
    "S": "P",
    "D": "U"
}


class ValidationException(Exception):
    pass


def read_tangram_file(filename) -> str:
    with open(filename, 'r') as f:
        return "".join(f.read().split())


MappingDict = Dict[str, str]
def read_mapping_file() -> MappingDict:
    with open('tandata/mapping.csv', newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)
        return {row[0]: row[1] for row in reader if row[0]}


TangramDict = Dict[str, Dict[str, str]]
def read_tandata() -> TangramDict:
    result: DefaultDict[str, DefaultDict[str, str]] = defaultdict(lambda: defaultdict(str))
    for directory in ('codm', 'wz'):
        for file in glob(f'tandata/{directory}/*.txt'):
            tan_name, _ = splitext(basename(file))
            result[directory][tan_name] = read_tangram_file(file)

    return result


def is_color(letter):
    return letter in "RYB"


def is_arrow(letter):
    return letter in ARROW_OPPOSITES


def validate_tangram(tangram):
    if len(tangram) != 6:
        raise ValidationException("Tangram size incorrect")

    color_count = 0
    arrow_count = 0
    for letter in tangram:
        if is_color(letter):
            color_count += 1
        elif is_arrow(letter):
            arrow_count += 1
        else:
            raise ValidationException(f"Invalid tangram letter {letter}")

    if color_count != 4:
        raise ValidationException(f"Incorrect color count {color_count}")

    if arrow_count != 2:
        raise ValidationException(f"Incorrect arrow count {arrow_count}")


def validate_tangram_pair(tangram1, tangram2):
    for i, (l1, l2) in enumerate(zip(tangram1, tangram2)):
        if is_color(l1):
            if not is_color(l2):
                raise ValidationException(f"Arrow color mismatch, index {i}: {l1} {l2}")
        else:
            if not is_arrow(l2):
                raise ValidationException(f"Arrow color mismatch, index {i}: {l1} {l2}")

            if ARROW_OPPOSITES[l1] != l2:
                raise ValidationException(f"Non-matching arrows, index {i}: {l1} {l2}")


def validate_tangrams(tangrams: TangramDict, mapping: MappingDict):
    for tangram_set, tangram_list in tangrams.items():
        if tangram_set == 'wz':
            mapping_tangram_names = mapping.keys()
        else:
            mapping_tangram_names = mapping.values()

        for tangram_name, tangram in tangram_list.items():
            try:
                validate_tangram(tangram)
            except ValidationException as e:
                raise ValidationException(f"Bad solo {tangram_set}/{tangram_name}") from e

            if tangram_name not in mapping_tangram_names:
                raise ValidationException(f"Tangram not in mapping.csv: {tangram_set}/{tangram_name}")

    wz_tangrams = tangrams['wz']
    codm_tangrams = tangrams['codm']

    for wz_tangram_name, codm_tangram_name in mapping.items():
        # We're currently missing some CODM tangrams:
        if not codm_tangram_name:
            continue

        wz_tangram = wz_tangrams.get(wz_tangram_name, None)
        if wz_tangram is None:
            raise ValidationException(f"Missing wz tangram {wz_tangram_name}")

        codm_tangram = codm_tangrams.get(codm_tangram_name, None)
        if codm_tangram is None:
            raise ValidationException(f"Missing codm tangram {codm_tangram_name}")

        try:
            validate_tangram_pair(wz_tangram, codm_tangram)
        except ValidationException as e:
            raise ValidationException(f"Bad pair {wz_tangram_name} {codm_tangram_name}") from e


def main():
    tangrams = read_tandata()
    mapping = read_mapping_file()
    validate_tangrams(tangrams, mapping)


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
