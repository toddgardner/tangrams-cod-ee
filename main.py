import csv
from collections import OrderedDict
from typing import Dict, Callable, Tuple, Sequence, Optional
from glob import glob
from os.path import basename, splitext
from PIL import Image, ImageDraw

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

MappingDict = Dict[int, str]
WzTangrams = Dict[int, str]
CodmTangrams = Dict[str, str]


class ValidationException(Exception):
    pass


def read_tangram_file(filename) -> str:
    with open(filename, 'r') as f:
        return "".join(f.read().split())


def read_mapping_file() -> MappingDict:
    with open('tandata/mapping.csv', newline='') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)
        return OrderedDict((int(row[0]), row[1]) for row in reader if row[0])


def read_tandata() -> Tuple[WzTangrams, CodmTangrams]:
    wz_tangrams = {}
    for file in glob(f'tandata/wz/*.txt'):
        tan_name, _ = splitext(basename(file))
        wz_tangrams[int(tan_name)] = read_tangram_file(file)

    codm_tangrams = {}
    for file in glob(f'tandata/codm/*.txt'):
        tan_name, _ = splitext(basename(file))
        codm_tangrams[tan_name] = read_tangram_file(file)

    return wz_tangrams, codm_tangrams


def is_color(letter):
    return letter in "RYB"


def is_arrow(letter):
    return letter in ARROW_OPPOSITES


def validate_tangram(tangram: str):
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


def validate_tangram_pair(tangram1: str, tangram2: str):
    for i, (l1, l2) in enumerate(zip(tangram1, tangram2)):
        if is_color(l1):
            if not is_color(l2):
                raise ValidationException(f"Arrow color mismatch, index {i}: {l1} {l2}")
        else:
            if not is_arrow(l2):
                raise ValidationException(f"Arrow color mismatch, index {i}: {l1} {l2}")

            if ARROW_OPPOSITES[l1] != l2:
                raise ValidationException(f"Non-matching arrows, index {i}: {l1} {l2}")


def validate_tangrams(wz_tangrams: WzTangrams, codm_tangrams: CodmTangrams, mapping: MappingDict):
    for tangram_set, tangram_list in (('wz', wz_tangrams), ('codm', codm_tangrams)):
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


BORDER_COLOR = (0, 0, 0)
BORDER_WIDTH = 10
TANGRAM_SQUARE_SIZE = 10
TANGRAM_SQUARE_BORDER = 1
TANGRAM_SQUARE_BORDER_COLOR = (0, 0, 0)
BETWEEN_TANGRAM_PAIR_BORDER = 10
BETWEEN_TANGRAM_PAIR_BORDER_COLOR = (235, 52, 223)

COLORS = {
    "R": (255, 0, 0),
    "B": (0, 0, 255),
    "Y": (255, 255, 0),
}


def draw_tangram(draw: ImageDraw, x: int, y: int, tangram: str):
    for i, letter in enumerate(tangram):
        row = int(i / 3)
        col = i % 3

        square_x_start = x + col*TANGRAM_SQUARE_SIZE
        square_y_start = y + row*TANGRAM_SQUARE_SIZE
        square_x_end = square_x_start+TANGRAM_SQUARE_SIZE
        square_y_end = square_y_start+TANGRAM_SQUARE_SIZE
        if is_color(letter):
            draw.rectangle([
                square_x_start,
                square_y_start,
                square_x_end,
                square_y_end],
                fill=COLORS[letter],
                outline=(0, 0, 0),
                width=TANGRAM_SQUARE_BORDER
            )
        else:
            draw.rectangle([
                square_x_start,
                square_y_start,
                square_x_end,
                square_y_end],
                fill=(255, 255, 255),
                outline=(0, 0, 0),
                width=1
            )
            square_coords = [
                (square_x_start+TANGRAM_SQUARE_BORDER, square_y_start+TANGRAM_SQUARE_BORDER),
                (square_x_start+TANGRAM_SQUARE_BORDER, square_y_end-TANGRAM_SQUARE_BORDER),
                (square_x_end-TANGRAM_SQUARE_BORDER, square_y_end-TANGRAM_SQUARE_BORDER),
                (square_x_end-TANGRAM_SQUARE_BORDER, square_y_start+TANGRAM_SQUARE_BORDER),
            ]
            if letter == "U":
                square_coords.pop(3)
            elif letter == "S":
                square_coords.pop(2)
            elif letter == "D":
                square_coords.pop(1)
            else:
                square_coords.pop(0)
            draw.polygon(square_coords, fill=(0, 0, 0))


def print_reference_image(wz_tangrams: WzTangrams, codm_tangrams: CodmTangrams, mapping: MappingDict):
    """Prints an image of each pair to make sure the tandata files are correct."""

    tangram_pair_vertical_size = (2*TANGRAM_SQUARE_SIZE) + (2*BETWEEN_TANGRAM_PAIR_BORDER)
    tangram_pair_horizontal_size = (6*TANGRAM_SQUARE_SIZE) + (2*BETWEEN_TANGRAM_PAIR_BORDER)
    vertical_image_size = (2*BORDER_WIDTH) + 6*tangram_pair_vertical_size
    horizontal_image_size = (2*BORDER_WIDTH) + 6*tangram_pair_horizontal_size

    with Image.new("RGB", (horizontal_image_size, vertical_image_size)) as im:
        draw = ImageDraw.Draw(im)
        draw.rectangle(
            [0, 0, horizontal_image_size, vertical_image_size],
            fill=(255, 255, 255), outline=BORDER_COLOR, width=BORDER_WIDTH
        )

        for i, (wz_tangram_name, codm_tangram_name) in enumerate(mapping.items()):
            row = i % 6
            col = int(i/6)

            wz_tangram = wz_tangrams.get(wz_tangram_name, None)
            codm_tangram = codm_tangrams.get(codm_tangram_name, None)

            tangram_pair_vertical_start = BORDER_WIDTH + row*tangram_pair_vertical_size
            tangram_pair_horizontal_start = BORDER_WIDTH + col*tangram_pair_horizontal_size

            draw.rectangle(
                [tangram_pair_horizontal_start, tangram_pair_vertical_start,
                 tangram_pair_horizontal_start+tangram_pair_horizontal_size,
                 tangram_pair_vertical_start+tangram_pair_vertical_size],
                fill=(255, 255, 255),
                outline=BETWEEN_TANGRAM_PAIR_BORDER_COLOR,
                width=BETWEEN_TANGRAM_PAIR_BORDER
            )

            draw_tangram(
                draw,
                tangram_pair_horizontal_start+BETWEEN_TANGRAM_PAIR_BORDER,
                tangram_pair_vertical_start+BETWEEN_TANGRAM_PAIR_BORDER,
                wz_tangram
            )
            if codm_tangram:
                draw_tangram(
                    draw,
                    tangram_pair_horizontal_start + BETWEEN_TANGRAM_PAIR_BORDER + 3*TANGRAM_SQUARE_SIZE,
                    tangram_pair_vertical_start + BETWEEN_TANGRAM_PAIR_BORDER,
                    codm_tangram
                )

        im.save("output/reference.png", "PNG")


def print_translated_tangrams(draw: ImageDraw,
                              x: int, y: int,
                              square_size: int,
                              wz_tangrams: WzTangrams,
                              codm_tangrams: CodmTangrams,
                              mapping: MappingDict,
                              tangram_order: Sequence[Sequence[int]],
                              color_translation: Callable[[str, Optional[str]], Tuple[int, int, int]]):
    """Prints tangrams according to a layout in tangram_order, with the translation function."""
    cols = len(tangram_order[0])

    tangram_vertical_size = 2 * square_size
    tangram_horizontal_size = 3 * square_size

    for row_index, row in enumerate(tangram_order):
        if len(row) != cols:
            raise Exception("tangram_order must be square")
        tangram_y = y + (row_index*tangram_vertical_size)

        for col_index, wz_tangram_number in enumerate(row):
            wz_tangram = wz_tangrams[wz_tangram_number]
            codm_tangram = codm_tangrams.get(mapping[wz_tangram_number], None)
            tangram_x = x + (col_index*tangram_horizontal_size)

            for i, wz_letter in enumerate(wz_tangram):
                square_row = int(i/3)
                square_col = i % 3
                square_x = tangram_x + (square_col * square_size)
                square_y = tangram_y + (square_row * square_size)
                codm_letter = None
                if codm_tangram:
                    codm_letter = codm_tangram[i]

                color = color_translation(wz_letter, codm_letter)
                draw.rectangle(
                    [square_x,
                     square_y,
                     square_x+square_size,
                     square_y+square_size],
                    fill=color,
                    outline=(0, 0, 0),
                    width=1
                )


def tangram_grid_size(square_size: int, tangram_order: Sequence[Sequence[int]]) -> Tuple[int, int]:
    rows = len(tangram_order)
    cols = len(tangram_order[0])

    for row in tangram_order:
        if len(row) != cols:
            raise Exception("tangram_order must be square")

    return cols*3*square_size, rows*2*square_size


def stripped_chunks(l, n):
    """Yield n number of striped chunks from l."""
    for i in range(0, n):
        yield l[i::n]


def sequential_chunks(l, n):
    """Yield n number of sequential chunks from l."""
    d, r = divmod(len(l), n)
    for i in range(n):
        si = (d+1)*(i if i < r else r) + d*(0 if i < r else i - r)
        yield l[si:si+(d+1 if i < r else d)]


def print_translated_reference(wz_tangrams: WzTangrams, codm_tangrams: CodmTangrams, mapping: MappingDict):
    """Prints an image of each pair to make sure the tandata files are correct."""

    border_size = 5
    square_size = 10

    tangram_order = list(stripped_chunks(range(1, 37), 6))

    x_grid_size, y_grid_size = tangram_grid_size(square_size, tangram_order)
    x_image_size = x_grid_size+(2*border_size)
    y_image_size = y_grid_size+(2*border_size)
    with Image.new("RGB", (x_image_size, y_image_size)) as im:
        draw = ImageDraw.Draw(im)
        draw.rectangle(
            [0, 0, x_image_size, y_image_size],
            fill=(255, 255, 255), outline=BORDER_COLOR, width=border_size
        )

        translated_pairs = {
            "BR": (255, 0, 255),
            "BY": (47, 255, 0),
            "RY": (255, 123, 0),
        }

        def translated_ref_colors(wz, codm):
            if not codm or is_arrow(wz):
                return None
            if wz == codm:
                return COLORS[wz]
            return translated_pairs["".join(sorted((wz, codm)))]

        print_translated_tangrams(
            draw,
            border_size,
            border_size,
            square_size,
            wz_tangrams,
            codm_tangrams,
            mapping,
            tangram_order,
            translated_ref_colors
        )

        im.save("output/translated_reference.png", "PNG")


def print_test_grid(filename: str, stripped: bool, rows: int, wz_tangrams: WzTangrams, codm_tangrams: CodmTangrams, mapping: MappingDict):
    """Prints an image of each pair to make sure the tandata files are correct."""

    border_size = 5
    square_size = 10

    base_order = range(1, 37)
    if stripped:
        sorted_order = stripped_chunks(base_order, rows)
    else:
        sorted_order = sequential_chunks(base_order, rows)
    tangram_order = list(sorted_order)

    x_grid_size, y_grid_size = tangram_grid_size(square_size, tangram_order)
    y_grid_size_with_border = y_grid_size+(2*border_size)
    x_image_size = x_grid_size+(2*border_size)
    y_image_size = 64*y_grid_size_with_border
    with Image.new("RGB", (x_image_size, y_image_size)) as im:
        draw = ImageDraw.Draw(im)

        draw.rectangle(
            [0, 0, x_image_size, y_image_size],
            fill=(255, 255, 255), outline=BORDER_COLOR, width=border_size
        )

        for i in range(64):
            binary_str = f"{i:06b}"
            colors_codes = [
                "YY",
                "RR",
                "BB",
                "BR",
                "BY",
                "RY"
            ]
            color_translation = {}
            for color_code, setting in zip(colors_codes, binary_str):
                if setting == "1":
                    color_translation[color_code] = (0, 0, 0)
                else:
                    color_translation[color_code] = (255, 255, 255)

            def translated_colors(wz, codm):
                if not codm or is_arrow(wz):
                    return 127, 127, 127
                return color_translation["".join(sorted((wz, codm)))]

            print_translated_tangrams(
                draw,
                border_size,
                y_grid_size_with_border*i,
                square_size,
                wz_tangrams,
                codm_tangrams,
                mapping,
                tangram_order,
                translated_colors
            )

        im.save(filename, "PNG")


def main():
    wz_tangrams, codm_tangrams = read_tandata()
    mapping = read_mapping_file()
    validate_tangrams(wz_tangrams, codm_tangrams, mapping)
    print_reference_image(wz_tangrams, codm_tangrams, mapping)
    print_translated_reference(wz_tangrams, codm_tangrams, mapping)
    print_test_grid("output/grid_6_by_6_stripped.png", True, 6, wz_tangrams, codm_tangrams, mapping)
    print_test_grid("output/grid_6_by_6_sequential.png", False, 6, wz_tangrams, codm_tangrams, mapping)
    print_test_grid("output/grid_18_by_2_stripped.png", True, 2, wz_tangrams, codm_tangrams, mapping)
    print_test_grid("output/grid_18_by_2_sequential.png", False, 2, wz_tangrams, codm_tangrams, mapping)


if __name__ == '__main__':
    main()
