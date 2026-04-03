"""
Build a JSON resource file, AllFormDisplayMap.json that stores all the pokemon forms and their display names.

See Packages/Resources/README.md on more details about AllFormDisplayMap.json.

Input files (all under SerialPrograms/Resources/Pokemon/):
- Pokedex/Pokedex-National.json      : national Pokédex — list of all species slugs
- PokemonNameDisplay.json            : English (and other language) display names for each species
- MinorGenderDifferenceList.txt      : species with minor visual gender differences (one slug per line)
- MajorGenderDifferenceList.txt      : species with major visual gender differences (one slug per line)
- RegionalForms.json                 : regional variant forms grouped by region (alola, galar, hisui, paldea)
- GeneralFormDisplayMap.json         : general alternate forms with their slugs and display names
- MegaPokemonList.txt                : Mega Evolution form slugs (one per line)
- GigantamaxForms.txt                : Gigantamax form slugs (one per line)

Output file (written to the current working directory):
- AllFormDisplayMap.json             : maps each species slug to a list of (form_slug, display_name) pairs
                                       for all of its visually distinct forms
"""

import os
import json
from typing import List, Dict, Tuple
from pathlib import Path
import json
import copy


# species name -> list of forms of that species
all_form_map: Dict[str, List[str]] = {}

REGION_TO_DISPLAY_PREFIX: Dict[str, str] = {
    "alola": "Alolan",
    "galar": "Galarian",
    "hisui": "Hisuian",
    "paldea": "Paldean",
}

def get_package_root_dir(current_path: Path) -> str:
    """
    Given a path somewhere in the repo Packages, return the absolute path of the Packages folder
    """
    original_path = current_path
    while current_path.name != 'Packages':
        if str(current_path) == "/":
        	raise RuntimeError(f"canot find root Git folder, Packages/ from path {original_path}")
        current_path = current_path.parent
    return str(current_path)


def load_slugs_from_txt(filename: str) -> List[str]:
    """
    Given a txt file path, assume it has a slug per line, load and return the slug list.
    """
    # print(filename)
    with open(filename, "r") as f:
        lines = f.readlines()
    return [l.lower().strip() for l in lines]


def find_form_species_name(form: str) -> str:
    """
    Given a form slug, reverse search it in `all_form_map` to find its species name slug
    """
    global all_form_map
    for species_name, existing_forms in all_form_map.items():
        if form in existing_forms:
            return species_name
    raise RuntimeError(f"form {form} not found in all_form_map")


def add_new_forms_from_base(base_form: str, new_forms: str | List[str]):
    """
    modify `all_form_map` to add new forms to a species besides its base form

    e.g. add a new Mega form or a Gmax form of a regional form.

    base_form: can be a species name or a form name already found in `all_form_map`.
    """

    global all_form_map
    if isinstance(new_forms, str):
        new_forms = [new_forms]
    if base_form in pokedex:
        if base_form not in all_form_map:
            all_form_map[base_form] = [base_form] + new_forms
        else: # form is already there
            for new_form in new_forms:
                if new_form not in all_form_map[base_form]:
                    all_form_map[base_form].append(new_form)
    else: # this must be a form name
        species_name = find_form_species_name(base_form)
        for new_form in new_forms:
            if new_form not in all_form_map[species_name]:
                all_form_map[species_name].append(new_form)
        

def replace_form_with_new_forms(base_form: str, new_forms: str | List[str]):
    """
    modify `all_form_map` to replace a form with new forms.
    - This can happen when we find out a pokemon has gendered difference:
      e.g. replace_form_with_new_forms('pikachu', ['pikachu-male', 'pikachu-female'])
    - This can also happen when we find out a pokemon species is split by forms:
      e.g. replace_form_with_new_forms('shellos', ['shellos-west-sea', 'shellos-east-sea'])

    Apart from species names, base_form can also be a form name, e.g.:
        replace_form_with_new_forms('sneasel-hisui', ['sneasel-hisui-male', 'sneasel-hisui-female'])
        In this case, the base_form must already be in `all_form_map`.
    """

    global all_form_map
    if isinstance(new_forms, str):
        new_forms = [new_forms]
    if base_form in pokedex:  # it's a species name
        species_name = base_form
    else:
        # look for the name in all_form_map
        for species_name, existing_forms in all_form_map.items():
            if base_form in existing_forms:
                break  # find the species
    if species_name not in all_form_map:
        assert base_form == species_name, f"base_form is {base_form}, species is {species_name}"
        all_form_map[species_name] = new_forms
    else:
        form_list = all_form_map[species_name]
        assert base_form in form_list, f"base_form {base_form} not found in {form_list}"
        base_idx = form_list.index(base_form)
        all_form_map[species_name] = form_list[0:base_idx] + new_forms + form_list[base_idx+1:]


current_path: Path = Path(os.getcwd())
package_root_dir: str = get_package_root_dir(current_path)
pokemon_dir: str = os.path.join(package_root_dir, "SerialPrograms/Resources/Pokemon")

# Load pokemon national dex
pokedex_json_path: str = os.path.join(pokemon_dir, "Pokedex/Pokedex-National.json")

with open(pokedex_json_path, "r", encoding="utf-8") as f:
    pokedex = json.load(f)
print(f"Pokedex size: {len(pokedex)}")

pokemon_species_display_json_path = os.path.join(pokemon_dir, "PokemonNameDisplay.json")
# encoding="utf-8" cannot decode this file, so I have to load via "rb" mode. This script only uses the English display name,
# so should be no problem with "rb"."
with open(pokemon_species_display_json_path, "rb") as f:
    display_names = json.load(f)
assert len(display_names) == len(pokedex)

species_to_display_name: Dict[str, str] = {dex_name: display_names[dex_name]["eng"] for dex_name in pokedex}

# mapping of any slug (species, forms, etc.) to its display name
slug_to_display_name: Dict[str, str] = copy.deepcopy(species_to_display_name)

# load various form data
minor_genders = load_slugs_from_txt(os.path.join(pokemon_dir, "MinorGenderDifferenceList.txt"))
major_genders = load_slugs_from_txt(os.path.join(pokemon_dir, "MajorGenderDifferenceList.txt"))
with open(os.path.join(pokemon_dir, "RegionalForms.json"), 'r', encoding='utf-8') as f:
    regional_forms: Dict[str, List[str]] = json.load(f)
with open(os.path.join(pokemon_dir, "GeneralFormDisplayMap.json"), 'r', encoding='utf-8') as f:
    general_form_displays: Dict[str, List[Tuple[str, str]]] = json.load(f)
mega_list = load_slugs_from_txt(os.path.join(pokemon_dir, "MegaPokemonList.txt"))
gmax_list = load_slugs_from_txt(os.path.join(pokemon_dir, "GigantamaxForms.txt"))
    

# build regional form display names and form slugs
for region_name, region_species in regional_forms.items():
    for species_name in region_species:
        assert species_name in species_to_display_name
        slug = f"{species_name}-{region_name}"
        display_name = f"{REGION_TO_DISPLAY_PREFIX[region_name]} {species_to_display_name[species_name]}" 
        # print(display_name)
        slug_to_display_name[slug] = display_name
        add_new_forms_from_base(species_name, slug)

# build general form display names and slugs
# form_and_displays: List[Tuple[str, str]], in each Tuple, the first str is the form slug while the second is the display name
for base_name, form_and_displays in general_form_displays.items():
    for form_name, display_name in form_and_displays:
        slug_to_display_name[form_name] = display_name
    replace_form_with_new_forms(base_name, [p[0] for p in form_and_displays])

# build Mega form display names and slugs
for mega_slug in mega_list:
    assert "mega" in mega_slug
    slug_words: List[str] = mega_slug.split('-')
    if slug_words[-1] == "mega":  # e.g. aerodactyl-mega
        species_name = '-'.join(slug_words[0:-1])
        display_name = f"Mega {species_to_display_name[species_name]}"
    else: # e.g. charizard-mega-x
        assert slug_words[-2] == "mega"
        ch = slug_words[-1].upper()
        species_name = '-'.join(slug_words[0:-2])
        display_name = f"Mega {species_to_display_name[species_name]} {ch}"
    slug_to_display_name[mega_slug] = display_name
    assert species_name in species_to_display_name
    add_new_forms_from_base(species_name, mega_slug)

# build Gigantamax form display names and slugs
# note: building Gigantamax form data must come after building general form data because
# a pokemon urshifu is split into two general forms while having different gmax forms.
for gmax_slug in gmax_list:
    base_name = gmax_slug[0:-5] # remove the "-gmax" suffix
    assert base_name in slug_to_display_name, f"{base_name}"
    display_name = f"Gigantamax {slug_to_display_name[base_name]}"
    slug_to_display_name[gmax_slug] = display_name
    add_new_forms_from_base(base_name, gmax_slug)

# build gender form display names and slugs
# note: building gender form data must come after building regional form data because a
# regional form, sneasel-hisui has gender differences
gender_list: List[str] = minor_genders + major_genders
for base_name in gender_list:
    gender_forms = [f"{base_name}-male", f"{base_name}-female"]
    slug_to_display_name[gender_forms[0]] = f"Male {slug_to_display_name[base_name]}"
    slug_to_display_name[gender_forms[1]] = f"Female {slug_to_display_name[base_name]}"
    replace_form_with_new_forms(base_name, gender_forms)

print(f"Found {len(all_form_map)} species have visually differnt forms")
print(f"Total forms found: {sum(len(forms) for forms in all_form_map.values())}")


# sanity check
for species_name, forms in all_form_map.items():
    assert species_name in pokedex
    form_set = set(forms)
    assert len(form_set) == len(forms)  # all forms in this species have unique slugs
    for form in forms:
        assert form in slug_to_display_name
all_forms: List[str] = sum((forms for forms in all_form_map.values()), start=[])
assert len(all_forms) == len(set(all_forms))  # all forms have unique slugs

output_json = {}
for species, forms in all_form_map.items():
    output_json[species] = [(f, slug_to_display_name[f]) for f in forms]

# print(output_json)
with open(f'AllFormDisplayMap.json', 'w', encoding='utf-8') as f:
    json.dump(output_json, f, ensure_ascii=False, indent=4)