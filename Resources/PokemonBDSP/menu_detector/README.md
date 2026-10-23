Menu detector screenshot tests

Top-level PNG files are expected to show the main game menu. Files beginning with non_menu_ are expected to be rejected. Each screenshot is tested at 1920x1080, 1280x720, and 960x540. The unit test also checks black and white frames.

Dev mode: Test Program (Computer) -> Run BDSP menu detector screenshot tests.
Unit Test Runner: PokemonBDSP::MenuDetector screenshot tests.

The default folder searches for Packages/Resources/PokemonBDSP/menu_detector above the executable, then falls back to runtime Resources. The dev-mode folder field can be changed.

Command-line tests also use the existing TestMap entry PokemonBDSP_MenuDetector. Copies under CommandLineTests/PokemonBDSP/MenuDetector use the standard _True/_False filename convention. Run:

SerialPrograms.exe --command-line-test-mode --command-line-test-folder "C:/Users/Kevin/GitRepos/BDSP-AutoStory/Packages/Resources/PokemonBDSP/menu_detector/CommandLineTests"

No controller inputs are sent.
