# Perfect Pineapple Player

A modern media player inspired by the iPod Classic interface, built with Python and Pygame.

## Features

*   Classic iPod-style menu navigation.
*   Music, Video, and Photo playback support.
*   Theming capabilities.
*   Directory import for media.
*   Gamepad support (Xbox 360 style layout).

## Dependencies

*   Python 3.x
*   Pygame (`pip install pygame`)
*   Pillow (`pip install Pillow`)
*   PyWin32 (`pip install pywin32`) (Windows only, for FFmpeg window focus)
*   FFmpeg (ffplay.exe, ffprobe.exe) - Required for video playback. Must be downloaded separately and the path provided to the application when prompted or set in `ipod_settings.json`.

## Running

1.  Install dependencies: `pip install -r requirements.txt` (or run `requirements.bat` on Windows).
2.  Ensure FFmpeg executables are accessible (e.g., in a `bin` folder or added to PATH).
3.  Run the script: `python iPod.py`

## Video Playback Disclaimer

**Please Note:** Due to limitations related to how operating systems handle window focus and interaction between different processes (Pygame and the external FFmpeg player), achieving seamless and perfectly integrated video playback within the application window proved challenging.

Therefore, video playback currently occurs in a **separate window** launched by `ffplay.exe`. While controls like play/pause/seek/stop can be triggered from the main application using a gamepad, direct interaction with the video window itself might behave unexpectedly depending on the OS.

Efforts were made to manage window focus and fullscreen transitions, but OS-level behaviors can interfere. A potential future solution might involve replacing the external FFmpeg dependency with a more tightly integrated video playback library, but this is not implemented at this time. 