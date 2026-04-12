#compdef wadcli wadmount

# Zsh completion for wadcli and wadmount
# Copy to a directory in your $fpath (e.g. ~/.zsh/completions/)
# or source directly: source wadcli.zsh

# ---------------------------------------------------------------------------
# wadcli
# ---------------------------------------------------------------------------

_wadcli() {
    local -a commands list_cmds export_cmds font_names

    commands=(
        'info:show WAD header and summary stats'
        'check:sanity-check a WAD for authoring errors'
        'complevel:detect compatibility level'
        'convert:convert between formats'
        'diff:compare two WADs and report differences'
        'list:list WAD contents'
        'export:export WAD contents to files'
        'scan:analyse WAD resource usage'
    )

    list_cmds=(
        'actors:list DECORATE actor definitions'
        'animations:list ANIMDEFS animation sequences'
        'flats:list floor/ceiling flat names'
        'lumps:list all directory entries'
        'maps:list maps with thing/linedef counts'
        'music:list music lumps'
        'patches:list patch names from PNAMES'
        'scripts:list ACS scripts'
        'sounds:list DMX sound lumps'
        'sprites:list sprite lumps'
        'stats:aggregate statistics across all maps'
        'textures:list composite texture names'
    )

    export_cmds=(
        'animation:render an ANIMDEFS sequence as GIF'
        'colormap:render COLORMAP as PNG grid'
        'endoom:export ENDOOM as text or ANSI'
        'flat:render a flat to PNG'
        'font:render a WAD font as sprite sheet'
        'lump:dump raw lump bytes to file'
        'map:render a map to PNG'
        'music:export music as MIDI'
        'obj:export a map as 3D OBJ mesh'
        'palette:render PLAYPAL as colour swatch'
        'patch:render a patch to PNG'
        'sound:export a DMX sound as WAV'
        'sprite:render a sprite to PNG'
        'texture:render a wall texture to PNG'
    )

    local -a scan_cmds convert_cmds complevel_names

    scan_cmds=(
        'textures:report texture and flat usage'
    )

    convert_cmds=(
        'pk3:convert WAD to pk3 archive'
        'wad:convert pk3 to WAD'
        'complevel:downgrade to target compatibility level'
    )

    complevel_names=(vanilla boom mbf mbf21 zdoom udmf)

    font_names=(stcfn fonta fontb)

    # Global options
    _arguments -C \
        '--wad[path to base WAD file]:WAD file:_files -g "*.{wad,WAD}"' \
        '*--pwad[additional PWAD to layer]:PWAD file:_files -g "*.{wad,WAD}"' \
        '--deh[standalone .deh patch to apply]:DEH file:_files -g "*.{deh,DEH,bex,BEX}"' \
        '1:command:->command' \
        '*::arg:->args'

    case "$state" in
        command)
            _describe -t commands 'wadcli command' commands
            ;;
        args)
            case "$words[1]" in
                list)
                    if (( CURRENT == 2 )); then
                        _describe -t list_cmds 'list subcommand' list_cmds
                    else
                        _arguments \
                            '--json[output as JSON]' \
                            '--filter[filter by name pattern]:pattern:'
                    fi
                    ;;
                export)
                    if (( CURRENT == 2 )); then
                        _describe -t export_cmds 'export subcommand' export_cmds
                    else
                        case "$words[2]" in
                            map)
                                _arguments \
                                    '1:map name:' \
                                    '2:output file:_files -g "*.png"' \
                                    '--floors[render floor textures]' \
                                    '--alpha[transparent background]' \
                                    '--scale[scale factor]:scale:' \
                                    '--sprites[render thing sprites]' \
                                    '--multiplayer[include multiplayer things]' \
                                    '--all[export all maps]'
                                ;;
                            sound)
                                _arguments \
                                    '1:sound name:' \
                                    '2:output file:_files -g "*.wav"' \
                                    '--raw[export raw DMX data]'
                                ;;
                            music)
                                _arguments \
                                    '1:music name:' \
                                    '2:output file:_files -g "*.mid"' \
                                    '--raw[export raw MUS data]'
                                ;;
                            palette)
                                _arguments \
                                    '1:output file:_files -g "*.png"' \
                                    '--palette[palette index]:index:'
                                ;;
                            endoom)
                                _arguments \
                                    '1:output file:_files -g "*.txt"' \
                                    '--ansi[output with ANSI colours]'
                                ;;
                            font)
                                _arguments \
                                    '1:font name:(stcfn fonta fontb)' \
                                    '2:output file:_files -g "*.png"'
                                ;;
                            sprite)
                                _arguments \
                                    '1:sprite name:' \
                                    '2:output file:_files -g "*.png"' \
                                    '--all[export all sprites]'
                                ;;
                            obj)
                                _arguments \
                                    '1:map name:' \
                                    '2:output file:_files -g "*.obj"' \
                                    '--scale[scale factor]:scale:' \
                                    '--materials[generate .mtl file]'
                                ;;
                            flat|texture|patch|colormap|animation|lump)
                                _arguments \
                                    '1:name:' \
                                    '2:output file:_files'
                                ;;
                        esac
                    fi
                    ;;
                scan)
                    if (( CURRENT == 2 )); then
                        _describe -t scan_cmds 'scan subcommand' scan_cmds
                    else
                        _arguments \
                            '--json[output as JSON]' \
                            '--unused[show only unused textures/flats]'
                    fi
                    ;;
                convert)
                    if (( CURRENT == 2 )); then
                        _describe -t convert_cmds 'convert subcommand' convert_cmds
                    else
                        case "$words[2]" in
                            complevel)
                                _arguments \
                                    '1:target level:(vanilla boom mbf mbf21 zdoom udmf)' \
                                    '2:output file:_files -g "*.wad"'
                                ;;
                            pk3)
                                _arguments '1:output file:_files -g "*.pk3"'
                                ;;
                            wad)
                                _arguments \
                                    '1:input pk3:_files -g "*.{pk3,PK3}"' \
                                    '2:output file:_files -g "*.wad"'
                                ;;
                        esac
                    fi
                    ;;
                info|check)
                    _arguments '--json[output as JSON]'
                    ;;
                complevel)
                    _arguments \
                        '--json[output as JSON]' \
                        '--check[check compatibility]:level:(vanilla boom mbf mbf21 zdoom udmf)'
                    ;;
                diff)
                    _arguments \
                        '1:second WAD:_files -g "*.{wad,WAD}"' \
                        '--json[output as JSON]'
                    ;;
            esac
            ;;
    esac
}

# ---------------------------------------------------------------------------
# wadmount
# ---------------------------------------------------------------------------

_wadmount() {
    _arguments \
        '1:WAD file:_files -g "*.{wad,WAD}"' \
        '2:mountpoint:_directories' \
        '--readonly[mount read-only]' \
        '-r[mount read-only]' \
        '--background[run in background]' \
        '-b[run in background]' \
        '--help[show help]'
}

compdef _wadcli wadcli
compdef _wadmount wadmount
