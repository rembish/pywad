# Bash completion for wadcli
# Source this file or copy to /etc/bash_completion.d/wadcli

_wadcli() {
    local cur prev words cword
    _init_completion || return

    # Top-level commands
    local commands="info check complevel diff list export scan convert"

    # list subcommands
    local list_cmds="actors animations flats lumps maps music patches scripts sounds sprites stats textures"

    # export subcommands
    local export_cmds="animation colormap endoom flat font lump map music obj palette patch sound sprite texture"

    # scan subcommands
    local scan_cmds="textures"

    # convert subcommands
    local convert_cmds="pk3 wad complevel"

    # Global options (before subcommand)
    local global_opts="--wad --pwad --deh --help"

    # Determine position in command chain
    local cmd="" subcmd=""
    local i
    for ((i=1; i < cword; i++)); do
        case "${words[i]}" in
            --wad|--pwad|--deh)
                ((i++))  # skip the argument
                ;;
            info|check|complevel|diff|list|export|scan|convert)
                cmd="${words[i]}"
                # Look for subcommand
                for ((i=i+1; i < cword; i++)); do
                    case "${words[i]}" in
                        --*) ;;
                        *)
                            subcmd="${words[i]}"
                            break
                            ;;
                    esac
                done
                break
                ;;
        esac
    done

    # Complete based on context
    case "$cmd" in
        "")
            # No command yet — suggest global opts + commands
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "$global_opts" -- "$cur"))
            elif [[ "$prev" == --wad || "$prev" == --pwad || "$prev" == --deh ]]; then
                _filedir '@(wad|WAD|deh|DEH|bex|BEX)'
            else
                COMPREPLY=($(compgen -W "$commands" -- "$cur"))
            fi
            ;;
        list)
            if [[ -z "$subcmd" ]]; then
                COMPREPLY=($(compgen -W "$list_cmds" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "--json --filter" -- "$cur"))
            fi
            ;;
        export)
            if [[ -z "$subcmd" ]]; then
                COMPREPLY=($(compgen -W "$export_cmds" -- "$cur"))
            else
                case "$subcmd" in
                    map)
                        COMPREPLY=($(compgen -W "--floors --alpha --scale --sprites --multiplayer --all" -- "$cur"))
                        ;;
                    sound|music)
                        COMPREPLY=($(compgen -W "--raw" -- "$cur"))
                        ;;
                    palette)
                        COMPREPLY=($(compgen -W "--palette" -- "$cur"))
                        ;;
                    endoom)
                        COMPREPLY=($(compgen -W "--ansi" -- "$cur"))
                        ;;
                    sprite)
                        COMPREPLY=($(compgen -W "--all" -- "$cur"))
                        ;;
                    font)
                        COMPREPLY=($(compgen -W "stcfn fonta fontb" -- "$cur"))
                        ;;
                    obj)
                        COMPREPLY=($(compgen -W "--scale --materials" -- "$cur"))
                        ;;
                    *)
                        _filedir
                        ;;
                esac
            fi
            ;;
        scan)
            if [[ -z "$subcmd" ]]; then
                COMPREPLY=($(compgen -W "$scan_cmds" -- "$cur"))
            else
                COMPREPLY=($(compgen -W "--json --unused" -- "$cur"))
            fi
            ;;
        convert)
            if [[ -z "$subcmd" ]]; then
                COMPREPLY=($(compgen -W "$convert_cmds" -- "$cur"))
            else
                case "$subcmd" in
                    complevel)
                        COMPREPLY=($(compgen -W "vanilla boom mbf mbf21 zdoom udmf" -- "$cur"))
                        ;;
                    *)
                        _filedir
                        ;;
                esac
            fi
            ;;
        info)
            COMPREPLY=($(compgen -W "--json" -- "$cur"))
            ;;
        complevel)
            COMPREPLY=($(compgen -W "--json --check" -- "$cur"))
            ;;
        check)
            COMPREPLY=($(compgen -W "--json" -- "$cur"))
            ;;
        diff)
            _filedir '@(wad|WAD)'
            ;;
    esac
}

complete -F _wadcli wadcli

# wadmount completion
_wadmount() {
    local cur prev
    _init_completion || return

    case "$prev" in
        wadmount)
            _filedir '@(wad|WAD)'
            ;;
        *)
            if [[ "$cur" == -* ]]; then
                COMPREPLY=($(compgen -W "--readonly -r --background -b --help" -- "$cur"))
            else
                _filedir -d
            fi
            ;;
    esac
}

complete -F _wadmount wadmount
