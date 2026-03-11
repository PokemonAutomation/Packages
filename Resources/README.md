# Guideline of Resources Folder

## Pokémon Definitions

In this doc we define a Pokémon "species" to mean all the Pokémon that share the same national Pokédex entry number. For example, Kantonian and Alolan Rattata belong to the same species called "Rattata".

## Slug

A slug is a string that uniquely identify an object for a program to manage it. Each Pokémon and in-game item needs a slug for SerialPrograms to identify it internally.
For example, slugs for all the Pokémon species can be found in [Pokedex-National.json](Resources/Pokemon/Pokedex/Pokedex-National.json).

We set a slug to consist only of lowercase letters, digits and hyphens. To sanitize Pokémon names into slugs, we convert white spaces and special characters to hyphens if they are in the middle of a name:

"Mime Jr." -> `mime-jr`

"Farfetch'd" -> `farfetch-d`

### Pokémon Forms

To create slugs for Pokémon forms, we have following rules:

- Shiny forms add "-shiny" to the end of the slug.

- Gender differences add "-(fe)male" to the end of the slug, e.g. `gyarados-male`. The only exception is Nidoran which get `nidoran-m` and `nidoran-f` since the two genders are two separate Pokédex entries.

- Mega forms add "-mega" to the end of the slug, e.g. `lucario-mega`, `charizard-mega-x`.

- Regional forms add "-\<region_name\>" to the end of the slug, e.g. `rattata-alola`. If a Pokémon species has a new regional form in an upcoming generation, we don't retroactively add a regional name to the base form's slug to ensure backward comaptibility. For example, Kantonian rattata is still `rattata`. We don't use `rattata-kanto`.

- Gigantamax forms add "-gmax" to the end of the slug, e.g. `venusaur-gmax`.

- General form differences. Use best judgement, e.g. `shellos-east-sea`, `shellos-west-sea`.

If a form has two or more suffixes, use this order:

speciesname-regional-generalform-gender-mega-gmax-shiny


## Descriptions of Resource Files

### Pokemon/AllFormDisplayMap.json
A dictionary of Pokémon species slug -> list of tuples. Each tuple represents a form of this species. Each tuple has two elements: the first is the form's slug; the second is the English display name of that form.

This file lists all possible Pokémon shape and appearance variations (which we call "forms" in this doc), including gender differences, regional forms, Mega forms, Gigantamax forms, special Terastallized forms, and other general form differences.

The data for forms are mostly sourced from [this Bulbapedia page](https://bulbapedia.bulbagarden.net/wiki/List_of_Pok%C3%A9mon_with_form_differences).

Notes:
- Shiny versions are not counted in this file as almost all forms have unique shiny counterparts. The only exceptions are rare cases like Alcremie and Minior. Multiple forms of them have the same shiny appearances. So to keep track of this, their unique shiny form slugs are included in this file.
- Different Spinda appearance variations are not counted in this file. There are too many Spinda variations to collect any way!
- Technical forms that don't have unique appearances are not included in this file. For example, Rockruff has a technical form that has Own Tempo ability. Scatterbug and Spewpa have different technical forms that lead to different Vivillon forms when evolved. We don't count them in this file.

This file is built by Scripts/build_all_form_display_map.py using data in other form-related files.

### Pokemon/GeneralFormDisplayMap.json
A dictionary of Pokémon species slug -> list of tuples. Each tuple represents a form of this species. Each tuple has two elements: the first is the form's slug; the second is the English display name of that form.

This file lists all the general form differences that don't go to catgories of gender differences, regional forms, Mega forms and Gigantamax forms. Since there are only two species having special Terastallized forms, those forms are in this file as well.

All the notes for **Pokemon/AllFormDisplayMap.json** apply in this file.


### Pokemon/GigantamaxForms.txt
Collects all the Gigantamax forms. Each line is a Gigantamax form slug.

### Pokemon/ImpossibleToDiscernForms.txt
Collects all the form groups that are impossible or almost impossible to tell apart the forms within each group.
Each line is a such form group, where each group is those form slugs spearated by ", ".

### Pokemon/MajorGenderDifferenceList.txt
Collects all the Pokémon species or regional forms with very different gender appearances.
Each line is a slug for such Pokémon.
As of Gen 9, all Pokémon both with gender differences and with Pokédex entry added since Gen 5 have such major gender differences.

### Pokemon/MinorGenderDifferenceList.txt
Collects all the Pokémon species or regional forms with subtle gender appearance differences.
Each line is a slug for such Pokémon.
As of Gen 9, all Pokémon both with gender differences and with Pokédex entry in Gen 1 to 4 have such minor gender differences.

### Pokemon/MegaPokemonList.txt
Collects slugs of all Pokémon Mega forms. Each line is a Mega slug.

### Pokemon/RegionalForms.json
A dictionary of region name slug -> list of Pokémon species that have regional forms there.
Collects all the regional form data. You can use this JSON file to build all the regional form slugs.


