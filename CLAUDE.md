# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Zapret GUI is a Windows desktop application for bypassing DPI (Deep Packet Inspection) internet censorship. It provides a GUI wrapper around the Zapret DPI bypass tools (winws.exe/winws2.exe). The interface is in Russian.

**Target platform:** Windows only (uses WinDivert kernel driver)

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application (requires admin rights)
python main.py

# Build with PyInstaller
python -m PyInstaller zapret_build.spec
# Output: dist/Zapret/

# Build installer (requires Inno Setup installed)
# Test channel: compile zapret_test.iss
# Stable channel: compile zapret_stable.iss
```

**Note:** The application requires administrator privileges to run (for WinDivert driver access and network manipulation).

## Architecture

### Multi-Manager Pattern

The application uses a manager-based architecture with PyQt6 signals/slots for event-driven communication:

- **`LupiDPIApp`** ([main.py](main.py)) - Main application class inheriting from `QWidget`, `MainWindowUI`, `ThemeSubscriptionManager`, `FramelessWindowMixin`
- **`InitializationManager`** ([managers/initialization_manager.py](managers/initialization_manager.py)) - Phased async initialization
- **`DPIManager`** ([managers/dpi_manager.py](managers/dpi_manager.py)) - DPI service control (start/stop winws)
- **`UIManager`** ([managers/ui_manager.py](managers/ui_manager.py)) - UI state coordination
- **`ProcessMonitorManager`** ([managers/process_monitor_manager.py](managers/process_monitor_manager.py)) - Background process monitoring
- **`SubscriptionManager`** ([managers/subscription_manager.py](managers/subscription_manager.py)) - Premium features handling

### Directory Structure

- **`config/`** - Configuration and registry management; `build_info.py` is auto-generated with version/channel
- **`ui/`** - PyQt6 user interface (Windows 11-style sidebar navigation)
  - `ui/pages/` - Individual pages (home, strategies, network, appearance, etc.)
  - `ui/widgets/` - Custom reusable widgets
- **`managers/`** - Business logic managers
- **`strategy_menu/`** - Strategy selection system
- **`startup/`** - Application startup logic (admin check, single instance, certificate installer)
- **`updater/`** - Auto-update system (GitHub releases + Telegram)
- **`bat/`** - BAT strategy files (legacy Zapret 1 format)
- **`json/`** - JSON configuration files
- **`exe/`** - Core executables (winws.exe for Zapret 1, winws2.exe for Zapret 2)

### Build Channels

The app has two build channels with separate registry paths:

- **test**: Uses `Software\Zapret2DevReg` registry, `ZapretDevLogo4.ico`
- **stable**: Uses `Software\Zapret2Reg` registry, `Zapret2.ico`

Channel is set in [config/build_info.py](config/build_info.py) via `CHANNEL` variable.

### Configuration Storage

All settings are stored in Windows Registry under `HKEY_CURRENT_USER\Software\Zapret2Reg` (or `Zapret2DevReg` for test builds):
- `\Autostart` - Autostart settings
- `\GUI` - GUI preferences
- `\Strategies` - Strategy selection
- `\Window` - Window position/size

Registry interface: [config/reg.py](config/reg.py)

## Strategy System

Strategies define DPI bypass configurations. Two formats are supported:

### BAT Format (Zapret 1)
Files in `bat/` folder with metadata in REM comments:
```bat
@echo off
REM NAME: Strategy name
REM VERSION: 1.0
REM DESCRIPTION: Description
REM LABEL: recommended|deprecated|experimental
REM AUTHOR: author
bin\winws.exe --wf-tcp=80,443 ...
```

### JSON Format (Zapret 2)
Strategy definitions in `strategy_menu/strategies/` for direct execution via winws2.exe

Key strategy files:
- [strategy_menu/strategies_registry.py](strategy_menu/strategies_registry.py) - Strategy definitions
- [strategy_menu/strategy_runner.py](strategy_menu/strategy_runner.py) - Strategy execution
- [strategy_menu/filters_config.py](strategy_menu/filters_config.py) - Category filtering

## Key Dependencies

- **PyQt6** - GUI framework
- **pywin32** - Windows API access
- **psutil** - Process management
- **qtawesome** - Font Awesome icons
- **qt_material** - Material Design themes
- **requests** - HTTP client
- **pyrogram/telethon** - Telegram integration for updates
