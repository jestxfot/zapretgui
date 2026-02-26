from preset_zapret2.preset_model import Preset
from preset_zapret2.preset_manager import PresetManager

app = PresetManager()

# Load a preset. We don't want to break the user's config so let's mock the env
from strategy_menu.strategies_registry import get_current_strategy_set
import unittest.mock as mock

print("Testing ADVANCED mode ...")
with mock.patch("strategy_menu.strategies_registry.get_current_strategy_set", return_value="advanced"):
    p = Preset(name="test")
    p.categories["youtube"] = app._create_category_with_defaults("youtube")
    # Simulate a strategy select
    app._update_category_args_from_strategy(p, "youtube", "youtube_tcp_split")
    cat = p.categories["youtube"]
    print("tcp_args:", cat.tcp_args)
    print("syndata enabled?", cat.syndata_tcp.enabled)
    print("send enabled?", cat.syndata_tcp.send_enabled)
    print("FULL:", cat.get_full_tcp_args().replace("\n", "  "))

print("\nTesting BASIC mode ...")
with mock.patch("strategy_menu.strategies_registry.get_current_strategy_set", return_value="basic"):
    p = Preset(name="test")
    p.categories["youtube"] = app._create_category_with_defaults("youtube")
    app._update_category_args_from_strategy(p, "youtube", "youtube_tcp_split")
    cat = p.categories["youtube"]
    print("tcp_args:", cat.tcp_args)
    print("syndata enabled?", cat.syndata_tcp.enabled)
    print("send enabled?", cat.syndata_tcp.send_enabled)
    print("FULL:", cat.get_full_tcp_args().replace("\n", "  "))
