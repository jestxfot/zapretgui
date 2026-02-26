import sys
import os

sys.path.insert(0, os.path.abspath('h:/Privacy/zapretgui'))
from preset_zapret2.txt_preset_parser import extract_strategy_args, extract_syndata_from_args, extract_send_from_args

block = '''--filter-tcp=80,443,1080,2053,2083,2087,2096,8443
--hostlist=lists/discord.txt
--out-range=-d10
--lua-desync=send:repeats=2
--lua-desync=syndata:blob=tls_google
--lua-desync=multisplit:pos=2,midsld-2:seqovl=1:seqovl_pattern=tls7'''

print("--- STRATEGY ARGS ---")
print(extract_strategy_args(block))
print("--- SYNDATA ---")
print(extract_syndata_from_args(block))
print("--- SEND ---")
print(extract_send_from_args(block))
