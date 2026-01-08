# preset_zapret2/preset_defaults.py
"""
Built-in default preset template.

This file contains the default preset content as a Python constant,
which allows us to:
1. Always restore default.txt from code (no external file dependency)
2. Guarantee that default.txt is never corrupted
3. Provide a recovery mechanism for users

The content is copied to:
- presets/Default.txt (for preset list)
- preset-zapret2.txt (when Default is active)
"""

DEFAULT_PRESET_CONTENT = """# Preset: Default
# Builtin: true

# Base args (общие параметры для всех категорий)
--lua-init=@lua/zapret-lib.lua
--lua-init=@lua/zapret-antidpi.lua
--lua-init=@lua/zapret-auto.lua
--wf-tcp-out=80,443,1080,2053,2083,2087,2096,8443
--wf-udp-out=80,443

# Category: youtube (TCP)
--filter-tcp=80,443
--hostlist=lists/youtube.txt
--lua-desync=multidisorder_legacy_midsld

--new

# Category: YouTube QUIC
--filter-udp=443
--ipset=lists/ipset-youtube.txt
--lua-desync=multidisorder_legacy_midsld

--new

# Category: discord (TCP)
--filter-tcp=80,443,1080,2053,2083,2087,2096,8443
--hostlist=lists/discord.txt
--lua-desync=multidisorder_legacy_midsld

--new

# Category: discord_voice (UDP/STUN)
--filter-l7=stun,discord
--payload=stun,discord_ip_discovery
--out-range=-d10
--lua-desync=fake:blob=0x00:repeats=6
"""
