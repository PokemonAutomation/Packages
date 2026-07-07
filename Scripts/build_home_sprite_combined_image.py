"""
Build a combined image that collects all the sprites of all pokemon forms (including shiny and nonshiny).
Also build a JSON file to tell which form's sprite is at which location in the combined image.

A combined image is better than a folder of images: our C++ program will load faster with a single image.

Input files/folders:
- ../../HomeImages/<sprite_size>x<sprite_size>/
    folder of Pokemon Home sprite dump PNG images. The folder is inside repo "HomeImages". The repo is placed next to Arduino-Source/
    repo. The repo is maintained by Zyro, at https://github.com/zyro670/HomeImages. 
    Each file inside is named like poke_capture_<dex_id>_<form_id>_<gender>_<gmax>_<subform_id>_<f/b>_<n/r>.png
    The commit of the repo this script uses is: 08048a0ca180b3682dfef9d29f6291a2e1083927
    The sprite_size is controlled by the variable `sprite_size` in this script (currently set to 64).
- Packages/SerialPrograms/Resources/Pokemon/Pokedex/Pokedex-National.json
    national Pokédex — list of all species slugs, used to determine ordering of sprites in the combined image
- Packages/SerialPrograms/Resources/Pokemon/AllFormDisplayMap.json
    maps each species to its visually distinct forms (output of build_all_form_display_map.py)
- Packages/SerialPrograms/Scripts/AllFormHomeSpriteMap.json
    maps each form slug (and shiny variant slug) to its Home sprite image filename
    (filename inside ../../HomeImages/<sprite_size>x<sprite_size>/). This JSON file is the output of
    build_all_form_home_sprite_map.py.

Output files (written to the current working directory):
- AllHomeSprites.png
    combined PNG image with all form sprites (non-shiny first, then shiny) arranged in a grid
- AllHomeSprites.json
    JSON with sprite dimensions (spriteHeight, spriteWidth) and the top-left pixel location of each
    form slug's sprite in AllHomeSprites.png
"""

import os
import math
import json
from pathlib import Path
from typing import List, Dict

import numpy as np

import cv2
import matplotlib.pyplot as plt


def get_git_root_dir(current_path: Path) -> Path:
    """
    Given a path somewhere in the repo Packages, return the absolute path of the parent folder to Packages/
    """
    original_path = current_path
    while current_path.name != 'Packages':
        if str(current_path) == "/":
            raise RuntimeError(f"canot find root Git folder, Packages/ from path {original_path}")
        current_path = current_path.parent
    return current_path.parent


def load_slugs_from_txt(filename: str) -> List[str]:
    """
    Given a txt file path, assume it has a slug per line, load and return the slug list.
    """
    # print(filename)
    with open(filename, "r") as f:
        lines = f.readlines()
    return [l.lower().strip() for l in lines]



def render_image(image):
    plt.figure(figsize=(10,10))
    image = cv2.cvtColor(image, cv2.COLOR_BGRA2RGBA)
    plt.imshow(image)
    plt.axis('on')
    plt.show()


# sprite_size = 128
sprite_size = 64

current_path: Path = Path(os.getcwd())

git_root_dir: Path = get_git_root_dir(current_path)
pokemon_folder_path: Path = git_root_dir / "Packages/SerialPrograms/Resources/Pokemon" 
package_script_path: Path = git_root_dir / "Packages/SerialPrograms/Scripts/"
pokedex_json_path: Path = pokemon_folder_path / "Pokedex/Pokedex-National.json"
home_image_dir = git_root_dir / "HomeImages" / f"{sprite_size}x{sprite_size}"

print(home_image_dir)


with open(str(pokedex_json_path), "r", encoding="utf-8") as f:
    pokedex = json.load(f)
print(f"Pokedex size: {len(pokedex)}")

all_form_map_json_path: Path = git_root_dir / "Packages/SerialPrograms/Resources/Pokemon/AllFormDisplayMap.json"
with open(str(all_form_map_json_path), "r", encoding="utf-8") as f:
    all_form_map = json.load(f)

all_form_sprite_map_path: Path = package_script_path / "AllFormHomeSpriteMap.json"
with open(str(all_form_sprite_map_path), "r", encoding="utf-8") as f:
    all_form_sprite_map: Dict[str, str] = json.load(f)
print(f"All forms with unique appearance (including shiny and non-shiny): {len(all_form_sprite_map)}")


total_forms_with_sprites = []
for dex_id, species in enumerate(pokedex):
    if species in all_form_map:
        forms = [t[0] for t in all_form_map[species]]
    else:
        forms = [species]

    shiny_forms = [form for form in forms if form.endswith("-shiny")]
    if not shiny_forms:
        shiny_forms = [form + "-shiny" for form in forms]
    forms = [form for form in forms if not form.endswith("-shiny")]

    total_forms_with_sprites.extend([f for f in forms if f in all_form_sprite_map])
    total_forms_with_sprites.extend([f for f in shiny_forms if f in all_form_sprite_map])

assert len(total_forms_with_sprites) == len(all_form_sprite_map)
n_sprites = len(total_forms_with_sprites)
print(f"Total sprites to build into: {n_sprites}")
n_sprites_in_row = int(math.sqrt(n_sprites))
n_sprites_in_col = math.ceil(n_sprites / n_sprites_in_row)

print(f"{n_sprites_in_row} x {n_sprites_in_col}")


output_json = {
    "spriteHeight": sprite_size,
    "spriteWidth": sprite_size,
}
spriteLocations = {}

# BGRA color channel order
canvas = np.zeros([sprite_size*n_sprites_in_col,sprite_size*n_sprites_in_row, 4], dtype=np.uint8)

for i, form in enumerate(total_forms_with_sprites):
    image_name = all_form_sprite_map[form]
    image_path = home_image_dir / image_name
    image = cv2.imread(str(image_path), cv2.IMREAD_UNCHANGED)
    
    x = i % n_sprites_in_row
    y = i // n_sprites_in_row
    spriteLocations[form] = {
        "top": y * sprite_size,
        "left": x * sprite_size,
    }

    canvas[y*sprite_size:(y+1)*sprite_size, x*sprite_size:(x+1)*sprite_size,:] = image

output_json["spriteLocations"] = spriteLocations


with open(f'AllHomeSprites.json', 'w', encoding='utf-8') as f:
    json.dump(output_json, f, ensure_ascii=False, indent=4)
cv2.imwrite('AllHomeSprites.png', canvas)



# check how much color is changed for a pokemon's shiny form


shiny_goodness = {}

for idx, form in enumerate(total_forms_with_sprites):
    if form.endswith("-shiny"):
        continue
    shiny_form = form + "-shiny"
    if shiny_form not in total_forms_with_sprites:
        continue
    shiny_idx = total_forms_with_sprites.index(shiny_form)

    x = idx % n_sprites_in_row
    y = idx // n_sprites_in_row
    sprite = canvas[y*sprite_size:(y+1)*sprite_size, x*sprite_size:(x+1)*sprite_size,:]
    x = shiny_idx % n_sprites_in_row
    y = shiny_idx // n_sprites_in_row
    shiny_sprite = canvas[y*sprite_size:(y+1)*sprite_size, x*sprite_size:(x+1)*sprite_size,:]
    diff = np.sum(np.abs(sprite-shiny_sprite)) / sprite.size
    shiny_goodness[form] = diff.item()

shiny_goodness_sort_buffer = [
    (diff, form) for form, diff in shiny_goodness.items()
]
shiny_goodness_sort_buffer = sorted(shiny_goodness_sort_buffer)

non_zero_diff_count = 0
for diff, form in shiny_goodness_sort_buffer:
    print(f"{form}: {diff}")
    if diff > 0:
        non_zero_diff_count += 1
    if non_zero_diff_count == 10:
        break