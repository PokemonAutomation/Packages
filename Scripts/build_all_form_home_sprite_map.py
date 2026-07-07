"""
Build a JSON file that maps all forms (shiny forms included) to corresponding Pokemon Home sprite dump images.

Input files/folders:
- ../../HomeImages/128x128/
    folder of Pokemon Home sprite dump PNG images. The folder is inside repo "HomeImages". The repo is placed next to Arduino-Source/
    repo. The repo is maintained by Zyro, at https://github.com/zyro670/HomeImages. The folder 128x128 hosts Home sprites of
    128x128 resolution. Each file inside is named like poke_capture_<dex_id>_<form_id>_<gender>_<gmax>_<subform_id>_<f/b>_<n/r>.png
    The commit of the repo this script uses is: 08048a0ca180b3682dfef9d29f6291a2e1083927
- Packages/SerialPrograms/Resources/Pokemon/Pokedex/Pokedex-National.json
    national Pokédex — list of all species slugs
- Packages/SerialPrograms/Resources/Pokemon/SpecialPokemonWithNoShinyForm.txt
    species/forms that have no shiny sprite (one slug per line)
- Packages/SerialPrograms/Resources/Pokemon/PokemonNameDisplay.json
    English (and other language) display names for each species
- Packages/SerialPrograms/Resources/Pokemon/AllFormDisplayMap.json
    maps each species to its visually distinct forms (output of build_all_form_display_map.py)

Output file (written to the current working directory):
- AllFormHomeSpriteMap.json
    maps each form slug (and shiny variant slug) to its corresponding Home sprite image filename
"""

import os
import json
from typing import List, Dict, Tuple, Sequence
from pathlib import Path
import json
import copy
from collections import defaultdict
from functools import partial


current_path: Path = Path(os.getcwd())


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



git_root_dir: Path = get_git_root_dir(current_path)
# print(git_root_dir)

# we assume all the Pokemon Home sprite dump images are in a repo called "HomeImages", and we pick image
# resolution at "128x128".
home_image_dir = git_root_dir / "HomeImages" / "128x128"
print(home_image_dir)

all_image_names: List[str] = [image_path.name for image_path in home_image_dir.iterdir() if image_path.is_file()]
print(f"Found {len(all_image_names)} images")
all_image_names = sorted(all_image_names)

# images have names like poke_capture_xxx_xxx_xx_n_00000000_f/b_n/r.png
# example image image_name: poke_capture_1025_000_uk_n_00000000_f_r.png
# poke_capture_<pokedex_id, 1-indxed>_<form_id, 0-indexed>_<gender_label>_<gigantamax>_<sub_form_id, 0-indexed>_<front_or_back>_<normal_or_shiny>.png
#
# gender_label: can be
# - mf: sprite is for both male and female, implying the pokemon can be male or female and there is no form differences between male and females
# - mo: sprite is for male only
# - fo: sprite is for female only
# - md: sprite is for male only, both male and female in this pokemon species belong to the same techinical form, meaning they only differ by appearance
# - fd: sprite is for female only, both male and female in this pokemon species belong to the same techinical form, meaning they only differ by appearance
# - uk: the pokemon has unknown gender
#
# <gigantamax> is either "g" for Gigantamax form or "n" for non-Gigantamax form
#
# <front_or_back> is "f" for front view and "b" for back view.
#
# <normal_or_shiny> is "n" for non-shiny and "r" for shiny ("rare").

# useful image: "poke_capture_0670_005_fo_n_00000000_f_n" is a pokeball image for missing sprite. It is the eternal floette


# images with poke_capture_xxx_xxx_fd_n_00000000_b_n/r.png, notice the "_b_" means this is a back-view image
# we don't need back-view images. Filter them out:
all_image_names = [name for name in all_image_names if not "_b_" in name]
print(len(all_image_names))


# Load pokemon national dex
pokemon_folder_path: Path = git_root_dir / "Packages/SerialPrograms/Resources/Pokemon" 
pokedex_json_path: Path = pokemon_folder_path / "Pokedex/Pokedex-National.json"
special_pokemon_with_no_shiny_path: Path = pokemon_folder_path / "SpecialPokemonWithNoShinyForm.txt"

with open(str(pokedex_json_path), "r", encoding="utf-8") as f:
    pokedex = json.load(f)
print(f"Pokedex size: {len(pokedex)}")

no_shiny_special_forms: List[str] = load_slugs_from_txt(special_pokemon_with_no_shiny_path)

pokemon_species_display_json_path = pokemon_folder_path / "PokemonNameDisplay.json"
with open(str(pokemon_species_display_json_path), "rb") as f:
    display_names = json.load(f)

all_form_map_json_path: Path = git_root_dir / "Packages/SerialPrograms/Resources/Pokemon/AllFormDisplayMap.json"
with open(str(all_form_map_json_path), "r", encoding="utf-8") as f:
    all_form_map = json.load(f)




def get_national_dex_no_from_path(image_name: str) -> int:
    nation_id = int(image_name.split("_")[2])
    return nation_id - 1 # convert to 0-indexed


def is_shiny_image(image_name: str) -> bool:
    return image_name.endswith("r.png")


def is_male_form_image(image_name: str) -> bool:
    # if species in minor_genders:
    return "_md_n_" in image_name or "_mo_n_" in image_name
    # else:
    #     return "_mo_n_" in image_name


def is_female_form_image(image_name: str) -> bool:
    return "_fd_n_" in image_name or "_fo_n_" in image_name


def is_gmax_form_image(image_name: str) -> bool:
    return "_g_" in image_name


def is_first_form_image(image_name: str) -> bool:
    return "_000_" in image_name


def match_image_suffix(image_name: str, suffix: str) -> bool:
    # remove the ending "_n.png" or "_r.png"
    return image_name[0:-6].endswith(suffix)


dex_to_image_names: Dict[int, List[str]] = defaultdict(list)
for image_name in all_image_names:
    dex_id = get_national_dex_no_from_path(image_name)
    dex_to_image_names[dex_id].append(image_name)


# special rules:
# if a form name is the same as the species name, we should add (normal form) to the end
# if there is shiny in the form name, we don't create shiny slugs for that species
# when creating labelling slugs, also add slugs for difficult-to-label minor gender differences and impossible forms


all_form_image_map = {}
all_shiny_form_image_map = {}

# have multiple forms (at least technically) but we can just pick the first form
FIRST_FORM_SPECIES = {
    "mothim",  # technical forms
    "scatterbug",  # technical forms
    "spewpa",  # technical forms
    "gumshoos",  # totem pokemon
    "vikavolt",  # totem pokemon
    "ribombee",  # totem pokemon
    "rockruff",  # technical forms
    "araquanid",  # totem pokemon
    "lurantis",  # totem pokemon
    "salazzle",  # totem pokemon
    "togedemaru",  # totem pokemon
    "kommo-o",  # totem pokemon
    "kleavor",  # noble pokemon
    "spidops",  # second form is a bad egg
    "tandemaus",  # technical forms
}

FIRST_REMAINING_FORM_SPECIES = {
    "raticate-alola",  # totem pokemon
    "arcanine-hisui",  # noble pokemon
    "electrode-hisui",  # noble pokemon
    "marowak-alola",  # totem pokemon
    "lilligant-hisui",  # noble pokemon
    "avalugg-hisui",  # noble pokemon
}

# TYPE_ORDER = [
#     "normal", "fire", 

def set_path(normal_image_names: List[str], shiny_image_names: List[str], form: str, first_form_set: Sequence[str] | None = None):
    if first_form_set is None:
        first_form_set = set()
    
    if (len(normal_image_names) == 1 and len(shiny_image_names) == 1) or form in first_form_set:
        normal_image_filename = normal_image_names[0]
        shiny_image_filename = shiny_image_names[0]
        all_form_image_map[form] = normal_image_filename
        if form not in no_shiny_special_forms:
            all_shiny_form_image_map[form + "-shiny"] = shiny_image_filename
    else:
        err_msg = f"For {form}, non-one filename for supposedly a single form"
        print(err_msg)
        print(normal_image_names)
        print(shiny_image_names)
        raise RuntimeError(err_msg)

def update_path(
    normal_image_names: List[str],
    shiny_image_names: List[str],
    cur_forms: List[str],
    filter_func,
    form: str,
    first_form_set: Sequence[str] | None = None,
):
    if isinstance(filter_func, str):
        filter_func = partial(match_image_suffix, suffix=filter_func)
    
    found_normal_names = [p for p in normal_image_names if filter_func(p)]
    found_shiny_names = [p for p in shiny_image_names if filter_func(p)]
    set_path(found_normal_names, found_shiny_names, form, first_form_set)
    for n in found_normal_names:
        normal_image_names.remove(n)
    for s in found_shiny_names:
        shiny_image_names.remove(s)
    cur_forms.remove(form)

for dex_id, species in enumerate(pokedex):
    image_names = copy.deepcopy(dex_to_image_names[dex_id])
    normal_image_names = [p for p in image_names if not is_shiny_image(p)]
    shiny_image_names = [p for p in image_names if is_shiny_image(p)]
    
    if species not in all_form_map:
        # no form variations
        set_path(normal_image_names, shiny_image_names, species, FIRST_FORM_SPECIES)
        continue
    # species in all form map!
    forms: List[str] = [t[0] for t in all_form_map[species]]
    male_form = f"{species}-male"
    female_form = f"{species}-female"
    mega_form = f"{species}-mega"
    gmax_form = f"{species}-gmax"

    cur_forms = copy.copy(forms)
    cur_normal_names = copy.copy(normal_image_names)
    cur_shiny_names = copy.copy(shiny_image_names)

    if species == "charizard":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_001_mf_n_00000000_f", "charizard-mega-x")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_002_mf_n_00000000_f", "charizard-mega-y")
    elif species == "pikachu":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_000_md_n_00000000_f", "pikachu-male")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_000_fd_n_00000000_f", "pikachu-female")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_001_mo_n_00000000_f", "pikachu-original-cap")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_002_mo_n_00000000_f", "pikachu-hoenn-cap")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_003_mo_n_00000000_f", "pikachu-sinnoh-cap")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_004_mo_n_00000000_f", "pikachu-unova-cap")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_005_mo_n_00000000_f", "pikachu-kalos-cap")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_006_mo_n_00000000_f", "pikachu-alola-cap")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_007_mo_n_00000000_f", "pikachu-partner-cap")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_009_mo_n_00000000_f", "pikachu-world-cap")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, is_gmax_form_image, gmax_form)
        continue
    elif species == "eevee":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_000_md_n_00000000_f", "eevee-male")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_000_fd_n_00000000_f", "eevee-female")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, is_gmax_form_image, gmax_form)
        continue
    elif species == "meowth":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "meowth-alola")
    elif species == "slowbro":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "slowbro-mega")
    elif species == "tauros":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mo_n_00000000_f", "tauros-paldea-combat-breed")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mo_n_00000000_f", "tauros-paldea-blaze-breed")
    elif species == "mewtwo":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_001_uk_n_00000000_f", "mewtwo-mega-x")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "_002_uk_n_00000000_f", "mewtwo-mega-y")
    elif species == "pichu":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, is_first_form_image, "pichu")
        continue
    elif species == "unown":
        for i in range(28):
            # poke_capture_0201_000_uk_n_00000000_f_r
            if i < 26:
                letter = chr(ord('a') + i)
            elif i == 26:
                letter = 'exclamation'
            else:
                letter = 'question'
            update_path(cur_normal_names, cur_shiny_names, cur_forms, f"_{i:03d}_uk_n_00000000_f", f"unown-{letter}")
    elif species == "sneasel":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_md_n_00000000_f", "sneasel-hisui-male")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_fd_n_00000000_f", "sneasel-hisui-female")
    elif species == "castform":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "castform-sunny")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "castform-rainy")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_mf_n_00000000_f", "castform-snowy")
    elif species == "deoxys":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "deoxys-attack")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_uk_n_00000000_f", "deoxys-defense")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_uk_n_00000000_f", "deoxys-speed")
    elif species == "burmy":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "burmy-sandy-cloak")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "burmy-trash-cloak")
    elif species == "wormadam":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_fo_n_00000000_f", "wormadam-sandy-cloak")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_fo_n_00000000_f", "wormadam-trash-cloak")
    elif species == "cherrim":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "cherrim-sunshine")
    elif species == "shellos":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "shellos-east-sea")
    elif species == "gastrodon":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "gastrodon-east-sea")
    elif species == "rotom":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "rotom-heat")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_uk_n_00000000_f", "rotom-wash")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_uk_n_00000000_f", "rotom-frost")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "004_uk_n_00000000_f", "rotom-fan")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "005_uk_n_00000000_f", "rotom-mow")
    elif species == "giratina":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "giratina-origin")
    elif species == "shaymin":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "shaymin-sky")
    elif species == "arceus":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_uk_n_00000000_f", "arceus-normal")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "arceus-fighting")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_uk_n_00000000_f", "arceus-flying")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_uk_n_00000000_f", "arceus-poison")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "004_uk_n_00000000_f", "arceus-ground")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "005_uk_n_00000000_f", "arceus-rock")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "006_uk_n_00000000_f", "arceus-bug")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "007_uk_n_00000000_f", "arceus-ghost")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "008_uk_n_00000000_f", "arceus-steel")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "009_uk_n_00000000_f", "arceus-fire")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "010_uk_n_00000000_f", "arceus-water")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "011_uk_n_00000000_f", "arceus-grass")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "012_uk_n_00000000_f", "arceus-electric")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "013_uk_n_00000000_f", "arceus-psychic")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "014_uk_n_00000000_f", "arceus-ice")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "015_uk_n_00000000_f", "arceus-dragon")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "016_uk_n_00000000_f", "arceus-dark")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "017_uk_n_00000000_f", "arceus-fairy")
        continue
    elif species == "basculin":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "basculin-blue-striped")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "basculin-white-striped")
    elif species == "darmanitan":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "darmanitan-zen-mode")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "darmanitan-galar-standard-mode")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_mf_n_00000000_f", "darmanitan-galar-zen-mode")
    elif species == "deerling":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "deerling-summer")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "deerling-autumn")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_mf_n_00000000_f", "deerling-winter")
    elif species == "sawsbuck":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "sawsbuck-summer")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "sawsbuck-autumn")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_mf_n_00000000_f", "sawsbuck-winter")
    elif species == "tornadus":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mo_n_00000000_f", "tornadus-therian")
    elif species == "thundurus":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mo_n_00000000_f", "thundurus-therian")
    elif species == "landorus":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mo_n_00000000_f", "landorus-therian")
    elif species == "kyurem":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "kyurem-white")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_uk_n_00000000_f", "kyurem-black")
    elif species == "keldeo":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "keldeo-resolute")
    elif species == "meloetta":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "meloetta-pirouette")
    elif species == "genesect":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "genesect-douse-drive")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_uk_n_00000000_f", "genesect-shock-drive")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_uk_n_00000000_f", "genesect-burn-drive")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "004_uk_n_00000000_f", "genesect-chill-drive")
    elif species == "greninja":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_mf_n_00000000_f", "greninja")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mo_n_00000000_f", "greninja-ash")
        continue
    elif species == "vivillon":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_mf_n_00000000_f", "vivillon-icy-snow")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "vivillon-polar")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "vivillon-tundra")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_mf_n_00000000_f", "vivillon-continental")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "004_mf_n_00000000_f", "vivillon-garden")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "005_mf_n_00000000_f", "vivillon-elegant")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "006_mf_n_00000000_f", "vivillon-meadow")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "007_mf_n_00000000_f", "vivillon-modern")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "008_mf_n_00000000_f", "vivillon-marine")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "009_mf_n_00000000_f", "vivillon-archipelago")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "010_mf_n_00000000_f", "vivillon-high-plains")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "011_mf_n_00000000_f", "vivillon-sandstorm")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "012_mf_n_00000000_f", "vivillon-river")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "013_mf_n_00000000_f", "vivillon-monsoon")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "014_mf_n_00000000_f", "vivillon-savanna")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "015_mf_n_00000000_f", "vivillon-sun")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "016_mf_n_00000000_f", "vivillon-ocean")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "017_mf_n_00000000_f", "vivillon-jungle")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "018_mf_n_00000000_f", "vivillon-fancy")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "019_mf_n_00000000_f", "vivillon-poke-ball")
    elif species == "flabebe":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_fo_n_00000000_f", "flabebe-red-flower")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_fo_n_00000000_f", "flabebe-yellow-flower")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_fo_n_00000000_f", "flabebe-orange-flower")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_fo_n_00000000_f", "flabebe-blue-flower")
    elif species == "floette":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_fo_n_00000000_f", "floette-red-flower")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_fo_n_00000000_f", "floette-yellow-flower")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_fo_n_00000000_f", "floette-orange-flower")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_fo_n_00000000_f", "floette-blue-flower")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "004_fo_n_00000000_f", "floette-white-flower")
    elif species == "florges":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_fo_n_00000000_f", "florges-red-flower")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_fo_n_00000000_f", "florges-yellow-flower")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_fo_n_00000000_f", "florges-orange-flower")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_fo_n_00000000_f", "florges-blue-flower")
    elif species == "furfrou":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "furfrou-heart-trim")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "furfrou-star-trim")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_mf_n_00000000_f", "furfrou-diamond-trim")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "004_mf_n_00000000_f", "furfrou-debutante-trim")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "005_mf_n_00000000_f", "furfrou-matron-trim")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "006_mf_n_00000000_f", "furfrou-dandy-trim")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "007_mf_n_00000000_f", "furfrou-la-reine-trim")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "008_mf_n_00000000_f", "furfrou-kabuki-trim")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "009_mf_n_00000000_f", "furfrou-pharaoh-trim")
    elif species == "aegislash":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "aegislash-blade")
    elif species == "pumpkaboo":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "pumpkaboo-small-size")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "pumpkaboo-large-size")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_mf_n_00000000_f", "pumpkaboo-super-size")
    elif species == "gourgeist":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "gourgeist-small-size")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "gourgeist-large-size")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_mf_n_00000000_f", "gourgeist-super-size")
    elif species == "xerneas":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "xerneas-active-mode")
    elif species == "zygarde":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_uk_n_00000000_f", "zygarde-fifty-percent")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "zygarde-ten-percent")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "004_uk_n_00000000_f", "zygarde-complete")
        continue
    elif species == "hoopa":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "hoopa-unbound")
    elif species == "oricorio":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "oricorio-pom-pom-style")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "oricorio-pau-style")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_mf_n_00000000_f", "oricorio-sensu-style")
    elif species == "lycanroc":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "lycanroc-midnight")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "lycanroc-dusk")
    elif species == "wishiwashi":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "wishiwashi-school")
    elif species == "silvally":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_uk_n_00000000_f", "silvally-normal")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "silvally-fighting")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_uk_n_00000000_f", "silvally-flying")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_uk_n_00000000_f", "silvally-poison")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "004_uk_n_00000000_f", "silvally-ground")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "005_uk_n_00000000_f", "silvally-rock")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "006_uk_n_00000000_f", "silvally-bug")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "007_uk_n_00000000_f", "silvally-ghost")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "008_uk_n_00000000_f", "silvally-steel")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "009_uk_n_00000000_f", "silvally-fire")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "010_uk_n_00000000_f", "silvally-water")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "011_uk_n_00000000_f", "silvally-grass")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "012_uk_n_00000000_f", "silvally-electric")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "013_uk_n_00000000_f", "silvally-psychic")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "014_uk_n_00000000_f", "silvally-ice")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "015_uk_n_00000000_f", "silvally-dragon")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "016_uk_n_00000000_f", "silvally-dark")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "017_uk_n_00000000_f", "silvally-fairy")
    elif species == "minior":
        all_form_image_map["minior-meteor"] = "poke_capture_0774_000_uk_n_00000000_f_n.png"
        all_form_image_map["minior-red-core"] = "poke_capture_0774_007_uk_n_00000000_f_n.png"
        all_form_image_map["minior-orange-core"] = "poke_capture_0774_008_uk_n_00000000_f_n.png"
        all_form_image_map["minior-yellow-core"] = "poke_capture_0774_009_uk_n_00000000_f_n.png"
        all_form_image_map["minior-green-core"] = "poke_capture_0774_010_uk_n_00000000_f_n.png"
        all_form_image_map["minior-blue-core"] = "poke_capture_0774_011_uk_n_00000000_f_n.png"
        all_form_image_map["minior-indigo-core"] = "poke_capture_0774_012_uk_n_00000000_f_n.png"
        all_form_image_map["minior-violet-core"] = "poke_capture_0774_013_uk_n_00000000_f_n.png"
        all_shiny_form_image_map["minior-core-shiny"] = "poke_capture_0774_007_uk_n_00000000_f_r.png"
        continue
    elif species == "mimikyu":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_mf_n_00000000_f", "mimikyu-disguised")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "mimikyu-busted")
        continue
    elif species == "necrozma":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "necrozma-dusk-mane")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_uk_n_00000000_f", "necrozma-dawn-wings")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_uk_n_00000000_f", "necrozma-ultra")
    elif species == "cramorant": 
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "cramorant-gulping")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "cramorant-gorging")
    elif species == "toxtricity":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_mf_g_00000000_f", "toxtricity-gmax")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_mf_n_00000000_f", "toxtricity-amped")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "toxtricity-low-key")
        continue
    elif species == "sinistea":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "sinistea-antique")
    elif species == "polteageist":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "polteageist-antique")
    elif species == "alcremie":
        all_form_image_map["alcremie-gmax"] = "poke_capture_0869_000_fo_g_00000000_f_n.png"
        all_shiny_form_image_map["alcremie-gmax-shiny"] = "poke_capture_0869_000_fo_g_00000000_f_r.png"

        creams = ["vanilla-cream", "ruby-cream", "matcha-cream", "mint-cream", "lemon-cream", "salted-cream", "ruby-swirl", "caramel-swirl", "rainbow-swirl"]
        assert len(creams) == 9
        sweets = ["strawberry", "berry", "love", "star", "clover", "flower", "ribbon"]
        assert len(sweets) == 7
        for j_s, sweet in enumerate(sweets):
            shiny_form = f"alcremie-{sweet}-shiny"
            all_shiny_form_image_map[shiny_form] = f"poke_capture_0869_000_fo_n_0000000{j_s}_f_r.png"
            for i_c, cream in enumerate(creams):
                form = f"alcremie-{cream}-{sweet}"
                all_form_image_map[form] = f"poke_capture_0869_00{i_c}_fo_n_0000000{j_s}_f_n.png"
        continue
    elif species == "eiscue":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "eiscue-noice-face")
    elif species == "morpeko":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "morpeko-hangry-mode")
    elif species == "zacian":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "zacian-crowned-sword")
    elif species == "zamazenta":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "zamazenta-crowned-shield")
    elif species == "urshifu":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_mf_g_00000000_f", "urshifu-single-strike-style-gmax")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_mf_n_00000000_f", "urshifu-single-strike-style")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_g_00000000_f", "urshifu-rapid-strike-style-gmax")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "urshifu-rapid-strike-style")
    elif species == "calyrex":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "calyrex-ice-rider")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_uk_n_00000000_f", "calyrex-shadow-rider")
    elif species == "enamorus":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_fo_n_00000000_f", "enamorus-therian")
    elif species == "maushold":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_uk_n_00000000_f", "maushold-family-of-three")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "maushold-family-of-four")
        continue
    elif species == "squawkabilly":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "squawkabilly-blue-plumage")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "squawkabilly-yellow-plumage")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_mf_n_00000000_f", "squawkabilly-white-plumage")
    elif species == "palafin":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "palafin-hero")
    elif species == "tatsugiri":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "tatsugiri-droopy")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "tatsugiri-stretchy")
    elif species == "dudunsparce":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "dudunsparce-three-segment")
    elif species == "gimmighoul":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "gimmighoul-roaming")
    elif species == "koraidon":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_uk_n_00000000_f", "koraidon-apex-build")
        continue
    elif species == "miraidon":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_uk_n_00000000_f", "miraidon-ultimate-mode")
        continue
    elif species == "poltchageist":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "poltchageist-artisan")
    elif species == "sinistcha":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_uk_n_00000000_f", "sinistcha-masterpiece")
    elif species == "ogerpon":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "000_fo_n_00000000_f", "ogerpon-teal-mask")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_fo_n_00000000_f", "ogerpon-wellspring-mask")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_fo_n_00000000_f", "ogerpon-hearthflame-mask")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "003_fo_n_00000000_f", "ogerpon-cornerstone-mask")
        continue
    elif species == "terapagos":
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "001_mf_n_00000000_f", "terapagos-terastal")
        update_path(cur_normal_names, cur_shiny_names, cur_forms, "002_mf_n_00000000_f", "terapagos-stellar")

    has_shiny_form = any(form.endswith("-shiny") for form in forms)
    if has_shiny_form: # and species != "minior":
        print("Sepcial situation!")
        print(f"Sepcies {species} has {len(forms)} forms: {forms}")
        print(f"normal images: {len(normal_image_names)}")
        for image_path in normal_image_names:
            print(image_path)
        break
        
    if male_form in cur_forms:
        update_path(cur_normal_names, cur_shiny_names, cur_forms, is_male_form_image, male_form)
    if female_form in cur_forms:
        update_path(cur_normal_names, cur_shiny_names, cur_forms, is_female_form_image, female_form)
    if gmax_form in cur_forms:
        update_path(cur_normal_names, cur_shiny_names, cur_forms, is_gmax_form_image, gmax_form)
    if species in cur_forms and len([n for n in cur_normal_names if is_first_form_image(n)]) == 1:
        update_path(cur_normal_names, cur_shiny_names, cur_forms, is_first_form_image, species)

    if len(cur_forms) == 0 and len(cur_normal_names) == 0 and len(cur_shiny_names) == 0:
        continue
    if len(cur_forms) == 1 and len(cur_normal_names) == 1 and len(cur_shiny_names) == 1:
        set_path(cur_normal_names, cur_shiny_names, cur_forms[0])
        continue
    if len(cur_forms) == 1 and cur_forms[0] in FIRST_REMAINING_FORM_SPECIES:
        set_path(cur_normal_names, cur_shiny_names, cur_forms[0], FIRST_REMAINING_FORM_SPECIES)
        continue
        
    print(f"{species} has {len(forms)} forms: {forms}")
    print(f"remaining forms: {len(cur_forms)}, {cur_forms}")
    print(f"remaining normal images: {len(cur_normal_names)}")
    for image_path in cur_normal_names:
        print(image_path)
    break


# sanity check
missing_normal_form_images = [
    "pikachu-cosplay",
    "pikachu-rock-star",
    "pikachu-belle",
    "pikachu-pop-star",
    "pikachu-phd",
    "pikachu-libre",
    "pichu-spiky-eared",
    "koraidon-limited-build",
    "koraidon-sprinting-build",
    "koraidon-swimming-build",
    "koraidon-gliding-build",
    "miraidon-low-power-mode",
    "miraidon-drive-mode",
    "miraidon-aquatic-mode",
    "miraidon-glide-mode",
    "ogerpon-teal-mask-terastallized",
    "ogerpon-cornerstone-mask-terastallized",
    "ogerpon-hearthflame-mask-terastallized",
    "ogerpon-wellspring-mask-terastallized",
]
missing_shiny_form_images = [
    f + "-shiny" for f in missing_normal_form_images
]
for dex_id, species in enumerate(pokedex):    
    if species in all_form_map:
        forms = [t[0] for t in all_form_map[species]]
    else:
        forms = [species]

    shiny_forms = [form for form in forms if form.endswith("-shiny")]
    if not shiny_forms:
        shiny_forms = [form + "-shiny" for form in forms if form not in no_shiny_special_forms]
    forms = [form for form in forms if not form.endswith("-shiny")]
    for form in forms:
        if form not in missing_normal_form_images:
            assert form in all_form_image_map, f"{form}"
    for shiny_form in shiny_forms:
        if shiny_form not in missing_shiny_form_images:
            assert shiny_form in all_shiny_form_image_map, shiny_form
for form in all_form_image_map:
    assert form not in all_shiny_form_image_map
for shiny_form in all_shiny_form_image_map:
    assert shiny_form not in all_form_image_map


# build final image map:
total_image_map = all_form_image_map | all_shiny_form_image_map
print(f"total unique sprites found with unique forms: {len(total_image_map)}")


with open(f'AllFormHomeSpriteMap.json', 'w', encoding='utf-8') as f:
    json.dump(total_image_map, f, ensure_ascii=False, indent=4)
print("Saved JSON to AllFormHomeSpriteMap.json")