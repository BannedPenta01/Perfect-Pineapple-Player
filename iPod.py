import pygame
import os
import sys
import datetime
import json
import random
import time
from tkinter import Tk, filedialog, messagebox
from PIL import Image as PILImage
# from moviepy.editor import VideoFileClip # REMOVED
import io
import subprocess # ADDED
# import shutil # REMOVED
import webbrowser
import ctypes
import threading

# --- Constants ---
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 240
STATUS_BAR_HEIGHT = 20
SIDE_PANEL_WIDTH = 100 # Width of the album art/info panel area
MAIN_AREA_WIDTH = SCREEN_WIDTH - SIDE_PANEL_WIDTH
FPS = 30

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (128, 128, 128)
LIGHT_GRAY = (200, 200, 200)
BLUE = (0, 0, 255) # Highlight color

# Themes (Color definitions and gradient logic)
# Gradients defined as (start_color, end_color)
THEMES = {
    "Silver": {"bg": (220, 220, 220), "text": BLACK, "highlight": BLUE, "side_gradient": ((180, 180, 180), (240, 240, 240))},
    "Dark": {"bg": (30, 30, 30), "text": LIGHT_GRAY, "highlight": (0, 100, 200), "side_gradient": ((20, 20, 20), (50, 50, 50))},
    "Red Wine": {"bg": (100, 0, 30), "text": WHITE, "highlight": (255, 100, 100), "side_gradient": ((80, 0, 20), (150, 20, 50))},
    "Grape Blue": {"bg": (50, 0, 100), "text": WHITE, "highlight": (150, 100, 255), "side_gradient": ((30, 0, 80), (90, 50, 150))},
    "Money Green": {"bg": (0, 80, 20), "text": WHITE, "highlight": (100, 255, 100), "side_gradient": ((0, 60, 10), (50, 120, 60))},
    "Dark Female Pink": {"bg": (130, 0, 130), "text": WHITE, "highlight": (255, 100, 255), "side_gradient": ((100, 0, 100), (180, 50, 180))},
    "Ocean Blue": {"bg": (0, 50, 100), "text": WHITE, "highlight": (100, 150, 255), "side_gradient": ((0, 30, 80), (50, 90, 150))},
    "Pineapple Orange": {"bg": (255, 165, 0), "text": BLACK, "highlight": (255, 69, 0), "side_gradient": ((240, 140, 0), (255, 200, 80))}
}
DEFAULT_THEME = "Silver"

# Settings File - Save in user's home directory for write permissions
SETTINGS_FILE = os.path.join(os.path.expanduser("~"), "ipod_settings.json")

# Gamepad Buttons (adjust indices based on your gamepad/pygame detection)
A_BUTTON = 0  # Typically the 'A' or 'X' button
B_BUTTON = 1  # Typically the 'B' or 'Circle' button
LB_BUTTON = 4 # Left bumper
RB_BUTTON = 5 # Right bumper
BACK_BUTTON = 6 # Added: Xbox Back button
START_BUTTON = 7 # Added: Xbox Start button
DPAD_UP = (0, 1)
DPAD_DOWN = (0, -1)
DPAD_LEFT = (-1, 0)
DPAD_RIGHT = (1, 0)
# Analog stick thresholds
STICK_THRESHOLD = 0.5

# --- Helper Functions ---

def validate_ffmpeg_path(dir_path):
    """Checks if ffprobe.exe and ffplay.exe exist in the given directory."""
    if not dir_path or not os.path.isdir(dir_path):
        return False
    ffprobe_path = os.path.join(dir_path, "ffprobe.exe")
    ffplay_path = os.path.join(dir_path, "ffplay.exe")
    return os.path.isfile(ffprobe_path) and os.path.isfile(ffplay_path)

def prompt_and_validate_ffmpeg_path():
    """Prompts user to select FFmpeg directory and validates it."""
    messagebox.showinfo("FFmpeg Location Needed",
                        "Perfect Pineapple Player needs the location of the directory containing \n"
                        "ffprobe.exe and ffplay.exe for video playback.\n\n"
                        "Please select the directory (often named 'bin') in the next dialog.")
    
    while True:
        dir_path = select_directory("Select FFmpeg Directory (containing ffprobe.exe, ffplay.exe)")
        if not dir_path: # User cancelled
            messagebox.showwarning("FFmpeg Path Required", "Video playback will be disabled because the FFmpeg path was not provided.")
            return None
            
        if validate_ffmpeg_path(dir_path):
            messagebox.showinfo("FFmpeg Path Set", f"FFmpeg path set to:\n{dir_path}")
            return dir_path
        else:
            if not messagebox.askretrycancel("Invalid FFmpeg Path",
                                            f"Could not find ffprobe.exe and ffplay.exe in:\n{dir_path}\n\n"
                                            "Please ensure you selected the correct directory. Retry?"):
                messagebox.showwarning("FFmpeg Path Required", "Video playback will be disabled because an invalid FFmpeg path was selected.")
                return None # User chose not to retry

def load_settings():
    """Loads settings from the JSON file."""
    default_settings = {
        "theme": DEFAULT_THEME,
        "music_dirs": [],
        "video_dirs": [],
        "image_dirs": [],
        "ffmpeg_path": None, # ADDED
        "games": [] # ADDED for imported games
    }
    if not os.path.exists(SETTINGS_FILE):
        return default_settings
    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            # Ensure all keys exist
            for key, value in default_settings.items():
                if key not in settings:
                    settings[key] = value
            
            # Validate theme exists
            if settings.get("theme") not in THEMES:
                settings["theme"] = DEFAULT_THEME

            # ADDED: Validate ffmpeg_path from settings
            if not validate_ffmpeg_path(settings.get("ffmpeg_path")):
                 print("Stored ffmpeg_path is invalid or missing, will prompt if needed.")
                 settings["ffmpeg_path"] = None # Reset if invalid
            else:
                 print(f"Using stored ffmpeg path: {settings['ffmpeg_path']}")

            return settings
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading settings: {e}, using defaults.")
        return default_settings

def save_settings(settings):
    """Saves settings to the JSON file."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except IOError as e:
        print(f"Error saving settings: {e}")

def get_themed_color(theme_name, color_key):
    """Gets a color from the current theme."""
    return THEMES.get(theme_name, THEMES[DEFAULT_THEME]).get(color_key, BLACK)

def draw_gradient_rect(surface, rect, start_color, end_color, vertical=True):
    """Draws a gradient rectangle."""
    steps = rect.height if vertical else rect.width
    if steps == 0: return # Avoid division by zero
    start_r, start_g, start_b = start_color
    end_r, end_g, end_b = end_color
    delta_r = (end_r - start_r) / steps
    delta_g = (end_g - start_g) / steps
    delta_b = (end_b - start_b) / steps

    for i in range(steps):
        color = (
            min(255, max(0, int(start_r + i * delta_r))),
            min(255, max(0, int(start_g + i * delta_g))),
            min(255, max(0, int(start_b + i * delta_b)))
        )
        if vertical:
            line_rect = pygame.Rect(rect.left, rect.top + i, rect.width, 1)
        else:
            line_rect = pygame.Rect(rect.left + i, rect.top, 1, rect.height)
        pygame.draw.rect(surface, color, line_rect)

def select_directory(title="Select Directory"):
    """Opens a directory selection dialog."""
    root = Tk()
    root.withdraw()  # Hide the main window
    root.attributes('-topmost', True) # Bring the dialog to the front
    directory = filedialog.askdirectory(title=title)
    root.destroy()
    return directory if directory else None

def get_media_files(directories, extensions):
    """Scans directories for files with given extensions."""
    files = []
    for directory in directories:
        if not os.path.isdir(directory):
            continue
        try:
            for item in os.listdir(directory):
                full_path = os.path.join(directory, item)
                if os.path.isfile(full_path) and item.lower().endswith(extensions):
                    files.append(full_path)
        except OSError as e:
            print(f"Error scanning directory {directory}: {e}")
    return files

def format_time(seconds):
    """Formats seconds into MM:SS format."""
    minutes = int(seconds // 60)
    seconds = int(seconds % 60)
    return f"{minutes:02d}:{seconds:02d}"

def truncate_text(text, font, max_width):
    """Truncates text with '...' if it exceeds max_width in pixels."""
    if not text: return ""
    original_width = font.size(text)[0]
    if original_width <= max_width:
        return text
    else:
        ellipsis = "..."
        ellipsis_width = font.size(ellipsis)[0]
        # Start removing chars from the end until it fits with ellipsis
        truncated = text
        while len(truncated) > 0 and font.size(truncated + ellipsis)[0] > max_width:
            truncated = truncated[:-1]
        return truncated + ellipsis

def render_text_wrapped(surface, text, font, color, rect, aa=True):
    """Renders text wrapped within a given rect. Returns the total height used."""
    try:
        y = rect.top
        line_spacing = font.get_linesize()
        font_height = font.size('Tg')[1]
        lines = text.splitlines()
        for text_line in lines:
            while text_line:
                i = 1
                if y + font_height > rect.bottom and rect.height != 10000: # Allow overflow for height calculation
                    break
                max_w = rect.width
                while font.size(text_line[:i])[0] < max_w and i < len(text_line):
                    i += 1
                if i < len(text_line):
                    i = text_line.rfind(" ", 0, i) + 1
                    if i <= 0:
                        i = len(text_line) # Word longer than width
                image = font.render(text_line[:i], aa, color)
                if surface: # Only blit if a surface is provided
                    surface.blit(image, (rect.left, y))
                y += line_spacing
                text_line = text_line[i:]
        return y - rect.top
    except Exception as e:
        print(f"[ERROR in render_text_wrapped]: {e}")
        import traceback
        traceback.print_exc()
        return 0 # Indicate error

# --- UI Classes ---

class StatusBar:
    """Handles drawing the top status bar."""
    def __init__(self, font, current_theme_name):
        self.font = font
        self.height = STATUS_BAR_HEIGHT
        self.battery_level = 1.0 # 0.0 to 1.0
        self.battery_charging = False # Placeholder
        self.update_theme(current_theme_name)

    def update_theme(self, theme_name):
        self.bg_color = get_themed_color(theme_name, "bg")
        self.text_color = get_themed_color(theme_name, "text")
        self.gradient_start = (0, 150, 0) # Green gradient for battery
        self.gradient_end = (0, 255, 0)

    def draw(self, surface):
        # Background
        pygame.draw.rect(surface, self.bg_color, (0, 0, SCREEN_WIDTH, self.height))
        pygame.draw.line(surface, GRAY, (0, self.height -1), (SCREEN_WIDTH, self.height -1))

        # Time
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M")
        time_surf = self.font.render(time_str, True, self.text_color)
        time_rect = time_surf.get_rect(center=(SCREEN_WIDTH // 2, self.height // 2))
        surface.blit(time_surf, time_rect)

        # Battery Icon (simple gradient version)
        batt_width = 20
        batt_height = 10
        batt_x = SCREEN_WIDTH - batt_width - 10
        batt_y = (self.height - batt_height) // 2
        batt_rect = pygame.Rect(batt_x, batt_y, batt_width, batt_height)
        pygame.draw.rect(surface, self.text_color, batt_rect, 1) # Outline

        # Nub
        nub_width = 2
        nub_height = 4
        nub_x = batt_x + batt_width
        nub_y = batt_y + (batt_height - nub_height) // 2
        pygame.draw.rect(surface, self.text_color, (nub_x, nub_y, nub_width, nub_height))

        # Fill based on level with gradient
        fill_width = int((batt_width - 2) * self.battery_level) # -2 for border
        fill_rect = pygame.Rect(batt_x + 1, batt_y + 1, fill_width, batt_height - 2)
        if fill_width > 0:
            draw_gradient_rect(surface, fill_rect, self.gradient_start, self.gradient_end, vertical=False)

        # Program Name (Optional, maybe place elsewhere)
        # name_surf = self.font.render("Perfect Pineapple Player", True, self.text_color)
        # name_rect = name_surf.get_rect(left=5, centery=self.height // 2)
        # surface.blit(name_surf, name_rect)


class SidePanel:
    """Handles drawing the side panel (e.g., for album art or context)."""
    def __init__(self, current_theme_name):
        self.width = SIDE_PANEL_WIDTH
        # Position on the right
        self.rect = pygame.Rect(SCREEN_WIDTH - self.width, STATUS_BAR_HEIGHT, self.width, SCREEN_HEIGHT - STATUS_BAR_HEIGHT)
        self.update_theme(current_theme_name)

    def update_theme(self, theme_name):
        theme = THEMES.get(theme_name, THEMES[DEFAULT_THEME])
        self.gradient_start, self.gradient_end = theme["side_gradient"]

    def draw(self, surface):
        draw_gradient_rect(surface, self.rect, self.gradient_start, self.gradient_end, vertical=True)
        # Placeholder for content (e.g., album art)
        # title_font = pygame.font.SysFont(None, 18)
        # title_surf = title_font.render("Now Playing", True, BLACK) # Use theme text color


class Menu:
    """Handles drawing and interaction for a list-based menu."""
    def __init__(self, items, font, item_height=20):
        self.items = items # List of strings or tuples (display_name, action_key)
        self.font = font
        self.item_height = item_height
        self.selected_index = 0
        self.scroll_offset = 0 # Index of the first visible item
        # Position on the left
        self.rect = pygame.Rect(0, STATUS_BAR_HEIGHT, MAIN_AREA_WIDTH, SCREEN_HEIGHT - STATUS_BAR_HEIGHT)
        self.theme_bg = WHITE
        self.theme_text = BLACK
        self.theme_highlight = BLUE

    def update_theme(self, theme_name):
        self.theme_bg = get_themed_color(theme_name, "bg")
        self.theme_text = get_themed_color(theme_name, "text")
        self.theme_highlight = get_themed_color(theme_name, "highlight")

    def get_visible_items_count(self):
        return self.rect.height // self.item_height

    def navigate(self, direction):
        """Handles up/down navigation."""
        if not self.items: return
        max_index = len(self.items) - 1
        self.selected_index = max(0, min(max_index, self.selected_index + direction))

        # Scrolling logic
        visible_count = self.get_visible_items_count()
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + visible_count:
            self.scroll_offset = self.selected_index - visible_count + 1

        # Ensure scroll_offset doesn't go too far
        self.scroll_offset = max(0, min(len(self.items) - visible_count, self.scroll_offset))
        # Handle case where items list is shorter than visible area
        if len(self.items) <= visible_count:
            self.scroll_offset = 0


    def get_selected_action(self):
        """Returns the action key of the selected item."""
        if not self.items or self.selected_index >= len(self.items):
            return None
        item = self.items[self.selected_index]
        return item[1] if isinstance(item, tuple) else item # Return action key or the item itself if simple list

    def draw(self, surface):
        surface.fill(self.theme_bg, self.rect)
        visible_count = self.get_visible_items_count()
        max_text_width = self.rect.width - 10
        for i in range(visible_count):
            index = self.scroll_offset + i
            if index >= len(self.items):
                break
            item = self.items[index]
            display_text = item[0] if isinstance(item, tuple) else item
            y = self.rect.top + i * self.item_height
            is_selected = (index == self.selected_index)
            bg_color = self.theme_highlight if is_selected else self.theme_bg
            text_color = self.theme_bg if is_selected else self.theme_text
            if is_selected:
                pygame.draw.rect(surface, bg_color, (self.rect.left, y, self.rect.width, self.item_height))
            # Truncate text if too long
            display_text = truncate_text(display_text, self.font, max_text_width)
            text_surf = self.font.render(display_text, True, text_color)
            text_rect = text_surf.get_rect(left=self.rect.left + 5, centery=y + self.item_height // 2)
            surface.blit(text_surf, text_rect)

# --- Media Player Classes (Placeholders) ---

class BaseMediaPlayer:
    """Base class for media players."""
    def __init__(self, font, initial_theme):
        self.font = font
        self.playlist = []
        self.current_index = -1
        self.is_playing = False
        self.playback_position = 0 # In seconds
        self.duration = 0 # In seconds
        # Player area should match the Menu area (now on the left)
        self.rect = pygame.Rect(0, STATUS_BAR_HEIGHT, MAIN_AREA_WIDTH, SCREEN_HEIGHT - STATUS_BAR_HEIGHT)
        self.update_theme(initial_theme)

    def update_theme(self, theme_name):
        self.theme_bg = get_themed_color(theme_name, "bg")
        self.theme_text = get_themed_color(theme_name, "text")
        self.theme_highlight = get_themed_color(theme_name, "highlight") # For progress bar etc.

    def load_playlist(self, files):
        self.playlist = files
        self.current_index = 0 if files else -1
        self.stop()
        if self.current_index != -1:
            self._load_current_track()

    def play_pause(self):
        if self.current_index == -1: return
        if self.is_playing:
            self._pause()
            self.is_playing = False
        else:
            self._play()
            self.is_playing = True

    def stop(self):
        self._stop()
        self.is_playing = False
        self.playback_position = 0

    def next_track(self):
        if not self.playlist: return
        self.stop()
        self.current_index = (self.current_index + 1) % len(self.playlist)
        self._load_current_track()
        self.play_pause() # Autoplay next

    def prev_track(self):
        if not self.playlist: return
        self.stop()
        self.current_index = (self.current_index - 1 + len(self.playlist)) % len(self.playlist)
        self._load_current_track()
        self.play_pause() # Autoplay previous

    def seek(self, time_delta):
        """Seek forward or backward by time_delta seconds."""
        if self.current_index == -1 or self.duration <= 0: return
        new_pos = max(0, min(self.duration, self.playback_position + time_delta))
        self._seek(new_pos)
        self.playback_position = new_pos # Update internal tracker immediately

    def update(self):
        """Update playback position, handle end of track etc."""
        if self.is_playing:
            self._update_position()
            if self.playback_position >= self.duration > 0:
                self.next_track() # Auto-advance

    def draw(self, surface):
        surface.fill(self.theme_bg, self.rect)

        # --- Define Layout Areas ---
        content_area = self.rect.inflate(-20, -20) # Area for positioning text

        # --- Draw Title (Truncated) --- Near the Top
        if self.current_track_title:
            title_max_width = content_area.width
            truncated_title = truncate_text(self.current_track_title, self.font, title_max_width)
            title_surf = self.font.render(truncated_title, True, self.theme_text)
            # Position title near the top, centered horizontally
            title_rect = title_surf.get_rect(centerx=self.rect.centerx, top=content_area.top + 10)
            surface.blit(title_surf, title_rect)

        # --- Progress Bar --- Near the Bottom
        pb_rect = pygame.Rect(content_area.left, content_area.bottom - 10, content_area.width, 10)
        pygame.draw.rect(surface, GRAY, pb_rect, 1) # Draw outline regardless of duration
        # Draw fill only if duration is known and positive
        if self.duration > 0:
            progress = self.playback_position / self.duration if self.duration else 0
            fill_width = int((pb_rect.width - 2) * progress)
            # Ensure fill_width is not negative
            fill_width = max(0, fill_width)
            fill_rect = pygame.Rect(pb_rect.left + 1, pb_rect.top + 1, fill_width, pb_rect.height - 2)
            pygame.draw.rect(surface, self.theme_highlight, fill_rect)

        # --- Playback Status and Time --- Just Above Progress Bar
        status_text = "Playing" if self.is_playing else "Paused" if self.current_index != -1 else "Stopped"
        pos_str = format_time(self.playback_position) # Always format current position
        dur_str = format_time(self.duration) if self.duration > 0 else "--:--" # Show --:-- if duration unknown
        time_text = f"{status_text} | {pos_str} / {dur_str}"
        time_surf = self.font.render(time_text, True, self.theme_text)
        # Position time text just above the progress bar
        time_rect = time_surf.get_rect(centerx=self.rect.centerx, bottom=pb_rect.top - 5)
        surface.blit(time_surf, time_rect)

    # --- Methods to be implemented by subclasses ---
    def _load_current_track(self): pass
    def _play(self): pass
    def _pause(self): pass
    def _stop(self): pass
    def _seek(self, position_sec): pass
    def _update_position(self): pass

    @property
    def current_track_title(self):
        if self.current_index != -1 and self.current_index < len(self.playlist):
            return os.path.basename(self.playlist[self.current_index])
        return ""


class MusicPlayer(BaseMediaPlayer):
    """Handles music playback using pygame.mixer."""
    def __init__(self, font, initial_theme, ffprobe_exec=None):
        super().__init__(font, initial_theme)
        pygame.mixer.init()
        self._start_time = 0
        self._paused_position = 0
        self.ffprobe_exec = ffprobe_exec # Store ffprobe path for duration detection

    def _load_current_track(self):
        if self.current_index != -1:
            filepath = self.playlist[self.current_index]
            try:
                pygame.mixer.music.load(filepath)
                self.duration = self._get_music_duration_ffprobe(filepath)
                self.playback_position = 0
                self._start_time = 0
                self._paused_position = 0
                self.is_playing = False # Reset playing state
                print(f"Loaded Music: {os.path.basename(filepath)} ({self.duration:.2f}s)")
            except pygame.error as e:
                print(f"Error loading music {filepath}: {e}")
                self.current_index = -1
                self.duration = 0
                self.playback_position = 0
            except Exception as e:
                print(f"Error getting duration for {filepath}: {e}")
                self.duration = 0 # Set duration to 0 if ffprobe fails
                self.playback_position = 0

    def _get_music_duration_ffprobe(self, filepath):
        """Gets music duration using ffprobe.exe."""
        if not self.ffprobe_exec or not os.path.isfile(self.ffprobe_exec):
            print("ffprobe.exe not set or not found. Cannot get music duration.")
            return 0
        try:
            result = subprocess.run([
                self.ffprobe_exec,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            duration_str = result.stdout.strip()
            if duration_str:
                duration = float(duration_str)
                if duration > 0:
                    return duration
            print(f"ffprobe could not get duration for: {filepath}")
        except Exception as e:
            print(f"ffprobe error reading {filepath}: {e}")
        return 0

    def play_pause(self):
        if self.current_index == -1: return

        if not pygame.mixer.music.get_busy(): # If not playing or paused
            try:
                pygame.mixer.music.play()
                self.is_playing = True
                self._start_time = time.time() - self._paused_position # Adjust start time based on paused pos
                self._paused_position = 0
                print("Music playing")
            except pygame.error as e:
                print(f"Error playing music: {e}")
        elif self.is_playing: # If playing, pause
            pygame.mixer.music.pause()
            self.is_playing = False
            # Store position when paused
            self._paused_position = time.time() - self._start_time + self._paused_position
            print("Music paused")
        else: # If paused, unpause
            pygame.mixer.music.unpause()
            self.is_playing = True
            # Reset start time based on stored paused position
            self._start_time = time.time() - self._paused_position
            self._paused_position = 0
            print("Music resumed")

    def stop(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.playback_position = 0
        self._start_time = 0
        self._paused_position = 0
        self.current_index = -1 # Indicate stopped
        self.duration = 0
        print("Music stopped")

    def seek(self, seconds):
        if not self.duration > 0: return # Can't seek without duration
        # Calculate target position based on internal timer
        current_pos = self.playback_position
        target_pos = current_pos + seconds
        target_pos = max(0, min(self.duration - 0.1, target_pos)) # Clamp within bounds

        try:
            # Still use set_pos for the actual audio engine seek
            pygame.mixer.music.set_pos(target_pos)
            # Update internal timer state to match seek
            self.playback_position = target_pos
            self._paused_position = 0 # Reset paused position after seek
            if self.is_playing:
                 self._start_time = time.time() - target_pos
            else:
                 # If paused, update the effective _paused_position
                 self._paused_position = target_pos
            print(f"Seeked music to: {target_pos:.2f}s")
        except pygame.error as e:
            print(f"Error seeking music (set_pos): {e}")
            # Attempt to resync internal timer even if set_pos fails
            self.playback_position = target_pos
            self._paused_position = 0
            if self.is_playing:
                 self._start_time = time.time() - target_pos
            else:
                 self._paused_position = target_pos

    def _update_position(self):
        # Remove the duration > 0 check here - update timer if playing
        if self.is_playing:
            elapsed = time.time() - self._start_time + self._paused_position
            # Clamp position based on duration *if* duration is known
            if self.duration > 0:
                self.playback_position = max(0, min(elapsed, self.duration))
                # Check if track ended based on our timer
                if self.playback_position >= self.duration:
                    self.stop() # Or potentially move to next track
                    print("Music track finished (timer based)")
            else:
                # If duration is unknown, just let playback_position increase
                self.playback_position = max(0, elapsed)
        # If paused, position is fixed
        elif not self.is_playing and self._paused_position > 0:
             self.playback_position = self._paused_position


class VideoPlayer(BaseMediaPlayer):
    """Handles video playback using ffplay external process."""
    def __init__(self, font, initial_theme, settings):
        super().__init__(font, initial_theme)
        self.settings = settings # Need settings reference
        self.ffprobe_exec = None # Full path to ffprobe.exe
        self.ffplay_exec = None  # Full path to ffplay.exe
        self.video_playback_enabled = False
        # Initialize ffplay process tracking attributes
        self._ffplay_process = None
        self._ff_start_time = 0

        # --- Find and set FFmpeg path --- 
        ffmpeg_dir = self.settings.get("ffmpeg_path")

        if not validate_ffmpeg_path(ffmpeg_dir):
             print("FFmpeg path not set or invalid in settings. Prompting user...")
             ffmpeg_dir = prompt_and_validate_ffmpeg_path()
             if ffmpeg_dir:
                 self.settings["ffmpeg_path"] = ffmpeg_dir
                 save_settings(self.settings) # Save the newly found path
             else:
                 print("User did not provide a valid FFmpeg path. Video playback disabled.")
                 
        if ffmpeg_dir: # Path is now validated (either from settings or prompt)
            self.ffprobe_exec = os.path.join(ffmpeg_dir, "ffprobe.exe")
            self.ffplay_exec = os.path.join(ffmpeg_dir, "ffplay.exe")
            self.video_playback_enabled = True
            print(f"FFmpeg executables set: \n  Probe: {self.ffprobe_exec}\n  Play: {self.ffplay_exec}")
        else:
             print("ERROR: Could not determine FFmpeg path. Video playback will be disabled.")
             # Keep self.ffprobe_exec and self.ffplay_exec as None
             self.video_playback_enabled = False

    def _get_video_info(self, filepath):
        """Uses ffprobe to get video duration and dimensions."""
        if not self.video_playback_enabled or not self.ffprobe_exec:
            print("Video info unavailable: Playback disabled or ffprobe path not set.")
            return 0, (0, 0)

        command = [
            self.ffprobe_exec, # USE FULL PATH
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration",
            "-of", "json",
            filepath
        ]
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True,
                                  creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0)
            data = json.loads(result.stdout)
            if "streams" in data and data["streams"]:
                stream = data["streams"][0]
                duration = float(stream.get("duration", 0))
                width = int(stream.get("width", 0))
                height = int(stream.get("height", 0))
                return duration, (width, height)
            else:
                return 0, (0, 0)
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError, KeyError, ValueError) as e:
            print(f"Error getting video info for {filepath}: {e}")
            return 0, (0, 0)

    def _load_current_track(self):
        self._stop_ffplay() # Ensure previous process is stopped
        self.is_playing = False
        self.playback_position = 0
        self.duration = 0

        if self.current_index != -1 and self.video_playback_enabled:
            filepath = self.playlist[self.current_index]
            try:
                self.duration, _ = self._get_video_info(filepath)
                print(f"Loaded Video: {filepath} ({self.duration:.2f}s)")
            except Exception as e:
                print(f"Error preparing video {filepath}: {e}")
                self.duration = 0
        elif not self.video_playback_enabled:
             print("Cannot load video track: Video playback is disabled.")

    def _launch_ffplay(self, start_pos=0):
        """Launches ffplay process."""
        if not self.video_playback_enabled or not self.ffplay_exec or self.current_index == -1:
             print("Cannot launch ffplay: Playback disabled, path not found, or no track selected.")
             return

        filepath = self.playlist[self.current_index]
        command = [
            self.ffplay_exec, # USE FULL PATH
            "-v", "error",
            "-autoexit",
            "-window_title", f"Perfect Pineapple Player - {os.path.basename(filepath)}",
        ]
        if start_pos > 0:
            command.extend(["-ss", str(start_pos)])
        command.append(filepath)

        try:
            # Use Popen for non-blocking execution
            # CREATE_NEW_PROCESS_GROUP allows terminating the whole process tree (might not be needed)
            # CREATE_NO_WINDOW hides the console window on Windows if ffplay itself shows one
            creation_flags = 0
            if sys.platform == 'win32':
                 creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP

            self._ffplay_process = subprocess.Popen(command, creationflags=creation_flags)
            self._ff_start_time = time.time() - start_pos # Record start time relative to seek position
            self.playback_position = start_pos # Set estimated position
            print(f"Launched ffplay for {filepath} at {start_pos}s")
        except (FileNotFoundError, OSError) as e:
            print(f"Error launching ffplay: {e}")
            self._ffplay_process = None

    def _stop_ffplay(self):
        """Stops the ffplay process if running."""
        if self._ffplay_process:
            print("Stopping ffplay...")
            try:
                # Terminate politely first, then kill if necessary
                self._ffplay_process.terminate()
                try:
                    self._ffplay_process.wait(timeout=0.5) # Wait briefly
                except subprocess.TimeoutExpired:
                    print("ffplay did not terminate, killing...")
                    self._ffplay_process.kill()
            except OSError as e:
                # Handle cases where process already exited
                if e.winerror != 5: # Access is denied (sometimes happens if already gone)
                     print(f"Error stopping ffplay: {e}")
            except Exception as e:
                 print(f"Unexpected error stopping ffplay: {e}")
            finally:
                 self._ffplay_process = None

    def _play(self):
        if not self.video_playback_enabled: return
        if self._ffplay_process: # Already playing (or process exists)
            # We can't reliably unpause, so maybe do nothing or log?
            print("ffplay already running (or failed to stop previously)")
            # Attempt to stop just in case it's a zombie process
            # self._stop_ffplay()
        else:
            # Relaunch from current (possibly paused) position
            self._launch_ffplay(start_pos=self.playback_position)

    def _pause(self):
        # Can't truly pause, so stop ffplay and keep position
        if self._ffplay_process:
             # Update estimated position before stopping
             self._update_position()
             self._stop_ffplay()
             # is_playing will be set to False by play_pause

    def _stop(self):
        self._stop_ffplay()
        self.playback_position = 0
        # is_playing handled by caller (stop method in BaseMediaPlayer)

    def _seek(self, position_sec):
        # Stop current playback and restart at new position
        if self.current_index != -1 and self.video_playback_enabled:
            was_playing = self.is_playing
            self._stop_ffplay()
            self.playback_position = position_sec
            if was_playing:
                 self._launch_ffplay(start_pos=self.playback_position)
                 self.is_playing = True # Ensure state is correct after relaunch
            else:
                 # If paused, just update position, don't relaunch yet
                 self.is_playing = False

    def _update_position(self):
        # Estimate position based on time elapsed since launch/seek
        # This is NOT accurate, especially if ffplay is manually closed or stalls.
        if self.is_playing and self._ffplay_process:
            # Check if process is still alive
            if self._ffplay_process.poll() is None:
                self.playback_position = (time.time() - self._ff_start_time)
                self.playback_position = max(0, min(self.playback_position, self.duration)) # Clamp to duration
            else:
                # Process exited, likely finished or closed manually
                print("ffplay process ended.")
                self._stop_ffplay() # Clean up reference
                self.is_playing = False
                # If it finished naturally, set position to end?
                if self.duration > 0: self.playback_position = self.duration
                # Auto-advance handled by BaseMediaPlayer.update()

    def draw(self, surface):
        # Draw base player UI (title, progress bar, time, etc.)
        super().draw(surface)

        # --- Display Video Specific Message --- Position Below Title
        info_font = pygame.font.SysFont(None, 18)
        if not self.video_playback_enabled:
             msg = "Video Playback Disabled (FFmpeg path not set/valid)"
             color = RED # Assume RED is defined globally or add it
        elif self.current_index == -1:
            msg = "No video loaded."
            color = self.theme_text
        elif self.is_playing:
            msg = "Video playing in separate window..."
            color = self.theme_text
        else:
            msg = "Video paused/stopped (external window closed)"
            color = self.theme_text

        msg_surf = info_font.render(msg, True, color)
        # Position message below where the title was drawn
        # Get title position from super().draw() if possible, or estimate
        title_bottom_approx = self.rect.inflate(-20, -20).top + 10 + self.font.get_linesize() # Approx bottom of title
        msg_rect = msg_surf.get_rect(centerx=self.rect.centerx, top=title_bottom_approx + 10)
        surface.blit(msg_surf, msg_rect)

    def focus_ffplay_window(self):
        """Attempts to bring the ffplay window to the foreground (Windows only)."""
        if not self._ffplay_process or not self._ffplay_process.pid:
            print("No ffplay process to focus.")
            return
        try:
            import time
            import ctypes
            import ctypes.wintypes
            import win32gui
            import win32process
            import win32con
        except ImportError:
            print("win32gui/win32process not available; cannot focus ffplay window.")
            return
        pid = self._ffplay_process.pid
        hwnd = None
        def enum_handler(h, l):
            nonlocal hwnd
            tid, win_pid = win32process.GetWindowThreadProcessId(h)
            if win_pid == pid:
                # Check window title
                title = win32gui.GetWindowText(h)
                if "ffplay" in title.lower() or "perfect pineapple player" in title.lower():
                    hwnd = h
        win32gui.EnumWindows(enum_handler, None)
        if hwnd:
            print(f"Focusing ffplay window (HWND={hwnd})...")
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        else:
            print("Could not find ffplay window to focus.")

    def is_ffplay_running(self):
        return self._ffplay_process and self._ffplay_process.poll() is None


class ImageViewer(BaseMediaPlayer):
    """Handles image viewing using Pillow and pygame."""
    # Adapting BaseMediaPlayer structure slightly for non-timed media
    def __init__(self, font, initial_theme):
        super().__init__(font, initial_theme)
        self.image_surface = None
        self.current_image_path = None
        self.duration = 0 # Not applicable, but keep attribute for consistency
        self.playback_position = 0

    def load_playlist(self, files):
        # Filter for image files specifically, although BaseMediaPlayer might have done this
        img_extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff')
        self.playlist = [f for f in files if f.lower().endswith(img_extensions)]
        self.current_index = 0 if self.playlist else -1
        self.stop() # Clear previous image
        if self.current_index != -1:
            self._load_current_track()

    def _load_current_track(self):
        if self.current_index != -1:
            filepath = self.playlist[self.current_index]
            self.current_image_path = filepath
            try:
                img = PILImage.open(filepath)
                img = img.convert("RGBA") # Ensure consistent format

                # Scale image to fit display area
                target_rect = self.rect.inflate(-20, -20) # Padding
                img_w, img_h = img.size
                ratio = min(target_rect.width / img_w, target_rect.height / img_h)
                scaled_size = (int(img_w * ratio), int(img_h * ratio))

                # Use thumbnail for potentially faster scaling? Or resize directly
                # img.thumbnail(scaled_size, PILImage.Resampling.LANCZOS)
                img = img.resize(scaled_size, PILImage.Resampling.LANCZOS)

                # Convert PIL image to Pygame surface
                mode = img.mode
                size = img.size
                data = img.tobytes()

                if mode == 'RGBA':
                    self.image_surface = pygame.image.fromstring(data, size, mode).convert_alpha()
                else:
                    self.image_surface = pygame.image.fromstring(data, size, mode).convert()

                self.image_draw_pos = self.image_surface.get_rect(center=self.rect.center)
                print(f"Loaded Image: {filepath}")

            except Exception as e:
                print(f"Error loading image {filepath}: {e}")
                self.image_surface = None
                self.current_image_path = None
                # Create an error surface?
                error_font = pygame.font.SysFont(None, 20)
                error_surf = error_font.render(f"Cannot load image", True, RED) # Need RED color
                self.image_surface = pygame.Surface((target_rect.width, 50))
                self.image_surface.fill(GRAY)
                err_rect = error_surf.get_rect(center=self.image_surface.get_rect().center)
                self.image_surface.blit(error_surf, err_rect)
                self.image_draw_pos = self.image_surface.get_rect(center=self.rect.center)


    def draw(self, surface):
        # Hide side panel and center image in the whole window
        surface.fill(self.theme_bg)
        if self.image_surface:
            win_rect = surface.get_rect()
            img_rect = self.image_surface.get_rect(center=win_rect.center)
            surface.blit(self.image_surface, img_rect)
            # Truncate filename if too long
            filename = os.path.basename(self.current_image_path) if self.current_image_path else "Error"
            img_count = f"{self.current_index + 1} of {len(self.playlist)}"
            info_text = f"{filename} ({img_count})"
            info_text = truncate_text(info_text, self.font, win_rect.width - 20)
            info_surf = self.font.render(info_text, True, self.theme_text)
            info_rect = info_surf.get_rect(centerx=win_rect.centerx, bottom=win_rect.bottom - 5)
            surface.blit(info_surf, info_rect)
        elif self.current_index != -1:
            error_font = pygame.font.SysFont(None, 20)
            error_surf = error_font.render(f"Error loading image", True, self.theme_text)
            err_rect = error_surf.get_rect(center=surface.get_rect().center)
            surface.blit(error_surf, err_rect)
        else:
            no_img_surf = self.font.render("No Images Loaded", True, self.theme_text)
            no_img_rect = no_img_surf.get_rect(center=surface.get_rect().center)
            surface.blit(no_img_surf, no_img_rect)

    # --- Overrides for non-applicable methods ---
    def play_pause(self): pass # N/A for images
    def seek(self, time_delta): pass # N/A
    def update(self): pass # N/A
    def _play(self): pass
    def _pause(self): pass
    def _stop(self):
        self.image_surface = None # Clear loaded image
        self.current_image_path = None
    def _seek(self, position_sec): pass
    def _update_position(self): pass


# --- New Screen Classes ---

class BaseScreen:
    """Base class for full-screen informational views like About, Donate."""
    def __init__(self, font, theme_name):
        self.font = font
        self.rect = pygame.Rect(0, STATUS_BAR_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT - STATUS_BAR_HEIGHT)
        self.scroll_y = 0
        self.content_surface = None
        self.total_content_height = 0
        self.scroll_step = 20 # Pixels per scroll step
        self.update_theme(theme_name)
        self._pre_render_content() # Call specific rendering in subclass

    def update_theme(self, theme_name):
        self.theme_bg = get_themed_color(theme_name, "bg")
        self.theme_text = get_themed_color(theme_name, "text")
        self.theme_highlight = get_themed_color(theme_name, "highlight") # Or a specific text color?
        self.theme_border = GRAY # Example border color

    def _pre_render_content(self):
        """Subclasses must implement this to render their specific text
           onto self.content_surface and set self.total_content_height."""
        raise NotImplementedError

    def handle_input(self, events):
        """Handles input for scrolling and closing. Returns an action string or None."""
        direction = 0
        action = None
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_UP, pygame.K_w]: direction = -1
                elif event.key in [pygame.K_DOWN, pygame.K_s]: direction = 1
                elif event.key in [pygame.K_ESCAPE, pygame.K_BACKSPACE]: action = 'close'
            elif event.type == pygame.JOYBUTTONDOWN:
                if event.button == B_BUTTON: action = 'close'
                elif event.button == LB_BUTTON: direction = -5 # Faster scroll
                elif event.button == RB_BUTTON: direction = 5  # Faster scroll
            elif event.type == pygame.JOYHATMOTION:
                if event.value == DPAD_UP: direction = -1
                elif event.value == DPAD_DOWN: direction = 1
            elif event.type == pygame.JOYAXISMOTION:
                if event.axis == 1: # Left stick vertical
                    if event.value < -STICK_THRESHOLD: direction = -1
                    elif event.value > STICK_THRESHOLD: direction = 1

        if direction != 0:
            self.scroll(direction)
            # Don't return an action for scroll, just update state

        return action # Return 'close' or specific actions handled by subclass

    def scroll(self, direction):
        """Updates the scroll_y position."""
        if not self.content_surface: return
        # Calculate visible height consistently with the draw method's content_rect
        content_rect = self.rect.inflate(-20, -20)
        visible_height = content_rect.height
        if visible_height <= 0: return # Avoid division by zero or nonsensical scroll

        max_scroll = max(0, self.total_content_height - visible_height)
        self.scroll_y += direction * self.scroll_step
        self.scroll_y = max(0, min(max_scroll, self.scroll_y))
        # print(f"[DEBUG {self.__class__.__name__}] Scroll Y: {self.scroll_y}, Max Scroll: {max_scroll}, Visible H: {visible_height}, Total H: {self.total_content_height}") # Optional debug

    def draw(self, surface):
        """Draws the screen content, handling scrolling."""
        surface.fill(self.theme_bg, self.rect) # Fill background

        if self.content_surface:
            content_rect = self.rect.inflate(-20, -20) # Inner padded area
            visible_height = content_rect.height

            # Calculate source rect from the pre-rendered text surface
            source_rect_width = self.content_surface.get_width()
            source_rect_height = min(visible_height, self.total_content_height - self.scroll_y)
            source_rect = pygame.Rect(0, self.scroll_y, source_rect_width, source_rect_height)

            # Blit the visible portion
            if source_rect.width > 0 and source_rect.height > 0:
                 surface.blit(self.content_surface, content_rect.topleft, area=source_rect)
            # else:
            #      print(f"[WARN] Invalid source_rect for {self.__class__.__name__} blit: {source_rect}")

            # Draw scroll indicators
            if self.total_content_height > visible_height:
                max_scroll = self.total_content_height - visible_height
                arrow_color = self.theme_border
                arrow_up_points = [(self.rect.right - 15, self.rect.top + 15), (self.rect.right - 5, self.rect.top + 15), (self.rect.right - 10, self.rect.top + 5)]
                arrow_down_points = [(self.rect.right - 15, self.rect.bottom - 15), (self.rect.right - 5, self.rect.bottom - 15), (self.rect.right - 10, self.rect.bottom - 5)]
                if self.scroll_y > 0: pygame.draw.polygon(surface, arrow_color, arrow_up_points)
                if self.scroll_y < max_scroll: pygame.draw.polygon(surface, arrow_color, arrow_down_points)
        else:
             # Draw placeholder if content failed to render
             err_surf = self.font.render("Error loading content.", True, self.theme_text)
             err_rect = err_surf.get_rect(center=self.rect.center)
             surface.blit(err_surf, err_rect)


class AboutScreen(BaseScreen):
    def _pre_render_content(self):
        about_lines = [
            "Perfect Pineapple Player",
            "",
            "A modern iPod Classic-inspired media player.",
            "",
            "Created by BannedPenta01.",
            "",
            "Disclaimer:",
            "If you think AI is 'ruining creativity',",
            "consider this: The same people who once said 'digital art isn't real art' now say 'AI isn't real creativity.'",
            "Gatekeeping tools is the oldest trick in the book.",
            "AI is a paintbrush for the neurodivergent, the disabled, the outsider, and the dreamer.",
            "If you fear new voices, maybe it's your own creativity that's threatened.",
            "",
            "Support more art, more music, more weirdness.",
            "Let us eat the Pineapple in peace", # NEW TEXT
            "",
            "(Press G to visit Github, B/Esc to close)",
        ]
        render_width = self.rect.width - 40
        # Estimate height initially, will be recalculated accurately later
        estimated_height = len(about_lines) * (self.font.get_linesize() + 6) + 100 # Generous estimate
        self.content_surface = pygame.Surface((render_width, estimated_height), pygame.SRCALPHA)
        self.content_surface.fill((0,0,0,0))
        y = 10 # Start with some top padding
        max_y = 0
        for i, line in enumerate(about_lines):
            color = self.theme_highlight if (i == 0 or line.startswith("Disclaimer") or line.startswith("(Press")) else self.theme_text
            font = self.font
            if i == 0:
                font = pygame.font.SysFont(None, 28, bold=True)
            elif line.startswith("Disclaimer"):
                font = pygame.font.SysFont(None, 22, bold=True)

            # --- Corrected Text Wrapping Logic --- Start
            words = line.split(' ')
            line_spacing = font.get_linesize()
            x = 10 # Reset x for each new original line
            current_line_text = ""

            if not line:
                # Handle blank lines explicitly to add vertical space
                y += line_spacing // 1.5 # Add space for blank lines
                max_y = max(max_y, y)
            else:
                for word in words:
                    # Test if adding the word (with a space if needed) exceeds width
                    test_text = current_line_text
                    if test_text: # Add space only if line isn't empty
                        test_text += " "
                    test_text += word

                    test_width = font.size(test_text)[0]

                    if test_width < render_width - 10: # Word fits
                        if current_line_text: # Add space if not the first word
                            current_line_text += " "
                        current_line_text += word
                    else: # Word does not fit, render the previous line
                        if current_line_text: # Render if there's something to render
                            line_surf = font.render(current_line_text, True, color)
                            self.content_surface.blit(line_surf, (x, y))
                            y += line_spacing
                            max_y = max(max_y, y)
                        # Start the new line with the current word
                        current_line_text = word
                        # Handle cases where a single word is too long (optional: could truncate)
                        if font.size(current_line_text)[0] >= render_width - 10:
                           # For now, render the oversized word on its own line
                           line_surf = font.render(current_line_text, True, color)
                           self.content_surface.blit(line_surf, (x, y))
                           y += line_spacing
                           max_y = max(max_y, y)
                           current_line_text = "" # Clear it as it's rendered

                # Render the last remaining line for the current original line
                if current_line_text:
                    line_surf = font.render(current_line_text, True, color)
                    self.content_surface.blit(line_surf, (x, y))
                    y += line_spacing
                    max_y = max(max_y, y)
            # --- Corrected Text Wrapping Logic --- End

            # Add a smaller gap between paragraphs/original lines
            if line: # Add less space after wrapped lines within the same original line
                 y += 2
            else: # Add more space after a blank line
                 y += 6
            max_y = max(max_y, y)

        # Crop the surface to the actual used height + bottom padding
        # Increase bottom padding slightly to prevent last line cutoff
        actual_height = max_y + 15 # Increased padding from 10 to 15
        cropped_surface = pygame.Surface((render_width, actual_height), pygame.SRCALPHA)
        cropped_surface.blit(self.content_surface, (0,0), (0, 0, render_width, actual_height))
        self.content_surface = cropped_surface
        self.total_content_height = self.content_surface.get_height()
        # print(f"[DEBUG AboutScreen] Final total_content_height: {self.total_content_height}") # Optional debug

    def handle_input(self, events):
        action = super().handle_input(events)
        if action: return action
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_g:
                    return 'github'
        return None

class DonateScreen(BaseScreen):
    # Define the single target URL
    _single_donate_url = "https://paypal.me/JanMichaelVegaTapia"

    # Keep labels, but point all URLs to the single target
    _donate_links = [
        ("$1", _single_donate_url),
        ("$5", _single_donate_url),
        ("$10", _single_donate_url),
        ("$15", _single_donate_url),
        ("$25", _single_donate_url),
    ]

    def _pre_render_content(self):
        base_lines = [
            "Support development!",
            "",
            "Press the corresponding number key (1-5) to open a PayPal link in your browser.",
            "",
        ]
        # render_width is the width of the content_surface
        render_width = self.rect.width - 40

        # Create a temporary surface with a generous height to render content onto
        estimated_height = 500
        temp_content_surface = pygame.Surface((render_width, estimated_height), pygame.SRCALPHA)
        temp_content_surface.fill((0,0,0,0)) # Transparent background

        y = 0
        # Render base lines using render_text_wrapped for proper word wrapping
        for line in base_lines:
            # The rect for render_text_wrapped is relative to temp_content_surface
            # Provide 10px padding on each side (total 20px off render_width)
            line_render_rect = pygame.Rect(10, y, render_width - 20, estimated_height - y)
            height_used = render_text_wrapped(temp_content_surface, line, self.font, self.theme_text, line_render_rect)
            y += height_used + (6 if line == "" else 0) # Add some padding between lines, more for blank lines

        # Render donation buttons with shortcut highlight
        button_font = pygame.font.SysFont(None, 24, bold=True)
        for idx, (label, url) in enumerate(self._donate_links):
            btn_rect = pygame.Rect(10, y, render_width-20, self.font.get_linesize() + 8)
            pygame.draw.rect(temp_content_surface, self.theme_highlight, btn_rect, border_radius=6)
            btn_text = f"[{idx+1}] {label}"
            text_surf = button_font.render(btn_text, True, self.theme_bg)
            text_rect = text_surf.get_rect(center=btn_rect.center)
            temp_content_surface.blit(text_surf, text_rect)
            y += btn_rect.height + 4

        # Render close instructions using render_text_wrapped
        close_text = "(Press B/Esc to close)"
        close_render_rect = pygame.Rect(10, y + 10, render_width - 20, estimated_height - (y+10))
        height_used_close = render_text_wrapped(temp_content_surface, close_text, self.font, self.theme_text, close_render_rect)
        y += 10 + height_used_close # Add padding and height of the close text

        # Crop the temporary surface to the actual content height and assign it
        final_height = y + 10 # Add a bit of padding at the bottom
        self.content_surface = pygame.Surface((render_width, final_height), pygame.SRCALPHA)
        self.content_surface.blit(temp_content_surface, (0,0), (0, 0, render_width, final_height))
        self.total_content_height = final_height

    def handle_input(self, events):
        action = super().handle_input(events)
        if action: return action
        donate_choice = None
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_1, pygame.K_KP1]: donate_choice = 0
                elif event.key in [pygame.K_2, pygame.K_KP2]: donate_choice = 1
                elif event.key in [pygame.K_3, pygame.K_KP3]: donate_choice = 2
                elif event.key in [pygame.K_4, pygame.K_KP4]: donate_choice = 3
                elif event.key in [pygame.K_5, pygame.K_KP5]: donate_choice = 4
        if donate_choice is not None:
            return f'donate_{donate_choice}'
        return None

# --- Add a placeholder screen for games --- # Moved here
class GamePlaceholderScreen(BaseScreen):
    def __init__(self, font, theme_name, game_name):
        self.game_name = game_name
        super().__init__(font, theme_name)

    def _pre_render_content(self):
        lines = [
            f"Game: {self.game_name}",
            "",
            "(Game launching/emulation not implemented)",
            "",
            "Press B/Esc to go back."
        ]
        render_width = self.rect.width - 40 # Available width for text
        # Initial estimate, will be recalculated
        estimated_height = len(lines) * (self.font.get_linesize() + 6) + 100
        temp_surface = pygame.Surface((render_width, estimated_height), pygame.SRCALPHA)
        temp_surface.fill((0,0,0,0))

        y = 10 # Start y position
        max_y = 0
        line_spacing = self.font.get_linesize()

        for line in lines:
            words = line.split(' ')
            x = 10 # Start x position for each line
            current_line_text = ""

            if not line:
                # Handle blank lines
                y += line_spacing // 1.5
                max_y = max(max_y, y)
            else:
                for word in words:
                    test_text = current_line_text
                    if test_text: test_text += " "
                    test_text += word
                    test_width = self.font.size(test_text)[0]

                    if test_width < render_width - 10: # Word fits
                        if current_line_text: current_line_text += " "
                        current_line_text += word
                    else: # Word doesn't fit, render previous line
                        if current_line_text:
                            line_surf = self.font.render(current_line_text, True, self.theme_text)
                            temp_surface.blit(line_surf, (x, y))
                            y += line_spacing
                            max_y = max(max_y, y)
                        current_line_text = word
                        # Handle single word too long (render it anyway)
                        if self.font.size(current_line_text)[0] >= render_width - 10:
                            line_surf = self.font.render(current_line_text, True, self.theme_text)
                            temp_surface.blit(line_surf, (x, y))
                            y += line_spacing
                            max_y = max(max_y, y)
                            current_line_text = "" # Clear as rendered

                # Render the last part of the line
                if current_line_text:
                    line_surf = self.font.render(current_line_text, True, self.theme_text)
                    temp_surface.blit(line_surf, (x, y))
                    y += line_spacing
                    max_y = max(max_y, y)

            # Add space between original lines
            if line: y += 2
            else: y += 6
            max_y = max(max_y, y)

        # Crop the surface to the actual content height
        actual_height = max_y + 15 # Add bottom padding
        self.content_surface = pygame.Surface((render_width, actual_height), pygame.SRCALPHA)
        self.content_surface.blit(temp_surface, (0,0), (0, 0, render_width, actual_height))
        self.total_content_height = actual_height

# --- Main Application Class ---

class PerfectPineapplePlayer:
    # --- REMOVE Overlay Attributes ---
    # _overlay_mode = None
    # _overlay_message = None
    # _overlay_text_surface = None
    # _overlay_scroll_y = 0
    # _overlay_total_height = 0
    # _scroll_step = 20

    _donate_links = [ # Keep this data if DonateScreen needs it directly (or pass it)
        ("$1", "https://paypal.me/BannedPenta01/1"),
        ("$5", "https://paypal.me/BannedPenta01/5"),
        ("$10", "https://paypal.me/BannedPenta01/10"),
        ("$15", "https://paypal.me/BannedPenta01/15"),
        ("$25", "https://paypal.me/BannedPenta01/25"),
    ]

    def __init__(self):
        pygame.init()
        pygame.joystick.init()
        self.joysticks = [pygame.joystick.Joystick(i) for i in range(pygame.joystick.get_count())]
        if self.joysticks: print(f"Detected Gamepad: {self.joysticks[0].get_name()}")
        else: print("No Gamepad Detected.")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SCALED | pygame.FULLSCREEN)
        pygame.display.set_caption("Perfect Pineapple Player")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        self.small_font = pygame.font.SysFont(None, 18)

        print(f"Settings file path: {SETTINGS_FILE}")

        # --- Auto-detect ffmpeg_path in script directory and bin subfolder ---
        script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        autodetected_ffmpeg = False
        autodetect_path = None
        # Check script directory
        ffprobe_path = os.path.join(script_dir, "ffprobe.exe")
        ffplay_path = os.path.join(script_dir, "ffplay.exe")
        if os.path.isfile(ffprobe_path) and os.path.isfile(ffplay_path):
            autodetected_ffmpeg = True
            autodetect_path = script_dir
            print(f"Auto-detected ffprobe.exe and ffplay.exe in: {script_dir}")
        else:
            # Check bin subfolder
            bin_dir = os.path.join(script_dir, "bin")
            ffprobe_path_bin = os.path.join(bin_dir, "ffprobe.exe")
            ffplay_path_bin = os.path.join(bin_dir, "ffplay.exe")
            if os.path.isfile(ffprobe_path_bin) and os.path.isfile(ffplay_path_bin):
                autodetected_ffmpeg = True
                autodetect_path = bin_dir
                print(f"Auto-detected ffprobe.exe and ffplay.exe in: {bin_dir}")

        self.settings = load_settings()
        # If autodetected and not already set, update settings
        if autodetected_ffmpeg and (not self.settings.get("ffmpeg_path") or not validate_ffmpeg_path(self.settings.get("ffmpeg_path"))):
            self.settings["ffmpeg_path"] = autodetect_path
            save_settings(self.settings)
            print(f"Set ffmpeg_path in settings to: {autodetect_path}")

        self.current_theme_name = self.settings.get("theme", DEFAULT_THEME)

        # UI Components
        self.status_bar = StatusBar(self.small_font, self.current_theme_name)
        self.side_panel = SidePanel(self.current_theme_name)

        # Media Players (Pass settings to VideoPlayer)
        # Pass ffprobe path to MusicPlayer
        ffmpeg_path = self.settings.get("ffmpeg_path")
        ffprobe_exec = os.path.join(ffmpeg_path, "ffprobe.exe") if ffmpeg_path else None
        self.music_player = MusicPlayer(self.font, self.current_theme_name, ffprobe_exec=ffprobe_exec)
        self.video_player = VideoPlayer(self.font, self.current_theme_name, self.settings) # PASS SETTINGS
        self.image_viewer = ImageViewer(self.font, self.current_theme_name)

        # Menu Navigation State
        self.menu_stack = [] # Stack to handle submenu navigation
        self.active_menu = None
        self.active_player = None # Points to the currently active player object
        self.active_screen = None # NEW: To hold AboutScreen or DonateScreen instance
        self.running = True
        self.was_fullscreen_before_video = False # ADDED: Track fullscreen state for video

        # Gamepad state tracking
        self.dpad_pressed = {'up': False, 'down': False, 'left': False, 'right': False}
        self.analog_y_pressed = {'up': False, 'down': False}
        self.button_pressed = { btn: False for btn in [A_BUTTON, B_BUTTON, LB_BUTTON, RB_BUTTON, BACK_BUTTON, START_BUTTON] }
        self.last_input_time = 0
        # Reduce input delay for more responsive navigation
        self.input_delay = 0.05 # Seconds delay for repeated input (Reduced from 0.15)

        self.build_main_menu()

    def build_main_menu(self):
        items = [
            ("Music", "music"),
            ("Videos", "videos"),
            ("Photos", "photos"),
            ("Games", "games"), # Inserted before Settings
            ("Settings", "settings"),
            ("Quit", "quit") # Added Quit button
        ]
        self.active_menu = Menu(items, self.font)
        self.active_menu.update_theme(self.current_theme_name)
        self.menu_stack = [self.active_menu] # Start with main menu on stack
        self.active_player = None # Ensure no player active
        self.active_screen = None # Ensure no screen active

    def build_settings_menu(self):
        items = [
            ("Import Music", "import_music"),
            ("Import Videos", "import_videos"),
            ("Import Photos", "import_photos"),
            ("Import Games", "import_games"), # ADDED
            ("Themes", "themes"),
            ("Reset Imported Paths", "reset_imported_paths"),
            ("Donate", "donate"),
            ("About", "about"),
            ("Github", "github"),
            ("Back", "back"),
        ]
        menu = Menu(items, self.font)
        menu.update_theme(self.current_theme_name)
        return menu

    def build_themes_menu(self):
        items = [(theme, f"set_theme_{theme}") for theme in THEMES.keys()]
        items.append(("Back", "back"))
        menu = Menu(items, self.font)
        menu.update_theme(self.current_theme_name)
        return menu

    def build_media_menu(self, media_type):
        """Builds menu listing files for music, videos, or photos."""
        extensions = ()
        files = []
        player = None
        action_prefix = ""

        if media_type == "music":
            extensions = ('.mp3', '.ogg', '.wav', '.flac') # Add more as supported by mixer/moviepy
            files = get_media_files(self.settings["music_dirs"], extensions)
            player = self.music_player
            action_prefix = "play_music_"
        elif media_type == "videos":
             extensions = ('.mp4', '.avi', '.mov', '.mkv') # Add more as supported by moviepy/ffmpeg
             files = get_media_files(self.settings["video_dirs"], extensions)
             player = self.video_player
             action_prefix = "play_video_"
        elif media_type == "photos":
             extensions = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')
             files = get_media_files(self.settings["image_dirs"], extensions)
             player = self.image_viewer
             action_prefix = "view_photo_"

        if not files:
            items = [("No media found.", None), ("(Import in Settings)", None), ("Back", "back")]
        else:
            # Create (display name, action) tuples
            items = [(os.path.basename(f), f"{action_prefix}{i}") for i, f in enumerate(files)]
            items.append(("Back", "back"))

        menu = Menu(items, self.font)
        menu.update_theme(self.current_theme_name)

        # Load playlist into the respective player when menu is built
        if player:
             player.load_playlist(files)

        return menu

    def build_games_menu(self):
        """Builds menu listing imported games (.ipg files)."""
        games = self.settings.get("games", [])
        if not games:
            items = [("No games imported.", None), ("(Import in Settings)", None), ("Back", "back")]
        else:
            items = [(os.path.basename(f), f"play_game_{i}") for i, f in enumerate(games)]
            items.append(("Back", "back"))
        menu = Menu(items, self.font)
        menu.update_theme(self.current_theme_name)
        return menu

    def update_theme(self, new_theme_name):
        if new_theme_name in THEMES:
            self.current_theme_name = new_theme_name
            self.settings["theme"] = new_theme_name
            save_settings(self.settings)
            # Update all theme-sensitive components
            self.status_bar.update_theme(new_theme_name)
            self.side_panel.update_theme(new_theme_name)
            if self.active_menu: self.active_menu.update_theme(new_theme_name)
            if self.active_player: self.active_player.update_theme(new_theme_name)
            if self.active_screen: self.active_screen.update_theme(new_theme_name) # Update active screen theme
            for menu in self.menu_stack:
                 menu.update_theme(new_theme_name)
            print(f"Theme set to: {new_theme_name}")


    def handle_input(self):
        # --- Primary Input Handling Order: Screen > Player > Menu ---
        events = pygame.event.get() # Get all events once per frame

        # Always define joystick and keys at the start
        joystick = self.joysticks[0] if self.joysticks else None
        keys = pygame.key.get_pressed()

        # 1. Handle Active Screen (About/Donate) Input
        if self.active_screen:
            action = self.active_screen.handle_input(events)
            if action == 'close':
                self.active_screen = None
                if self.menu_stack: # Restore previous menu
                    self.active_menu = self.menu_stack[-1]
                else: # Should not happen, but fallback to main menu
                    self.build_main_menu()
            elif action == 'github':
                 webbrowser.open_new_tab("https://github.com/BannedPenta01")
            elif action and action.startswith('donate_'): # Any donate action opens the single link
                 webbrowser.open_new_tab(DonateScreen._single_donate_url)
                 self.active_screen = None # Close after opening link
                 if self.menu_stack: self.active_menu = self.menu_stack[-1]
                 else: self.build_main_menu()
            return # Active screen handled input, stop processing

        # 2. Handle Player Input (if no active screen)
        current_time = time.time()
        process_input = current_time > self.last_input_time + self.input_delay
        action_select = False
        action_back = False
        action_seek_forward = False
        action_seek_backward = False
        action_toggle_fullscreen = False
        direction = 0 # For menu navigation

        # Re-process events for player/menu if not handled by screen
        for event in events:
             if event.type == pygame.QUIT:
                 self.running = False
                 return

             # Fullscreen toggle is global
             if event.type == pygame.JOYBUTTONDOWN:
                 if joystick and event.button == BACK_BUTTON and process_input and not self.button_pressed[BACK_BUTTON]:
                     action_toggle_fullscreen = True
                     self.button_pressed[BACK_BUTTON] = True
                     self.last_input_time = current_time + 0.1
                 elif joystick and not joystick.get_button(BACK_BUTTON): self.button_pressed[BACK_BUTTON] = False # Reset on release

                 if joystick and event.button == START_BUTTON and process_input and not self.button_pressed[START_BUTTON]:
                     action_toggle_fullscreen = True
                     self.button_pressed[START_BUTTON] = True
                     self.last_input_time = current_time + 0.1
                     # Only Start triggers ffplay focus
                     if self.active_player and isinstance(self.active_player, VideoPlayer) and self.active_player.is_playing:
                         threading.Thread(target=self.active_player.focus_ffplay_window, daemon=True).start()
                 elif joystick and not joystick.get_button(START_BUTTON): self.button_pressed[START_BUTTON] = False # Reset on release

             # Player / Menu specific input
             if self.active_player:
                 # Handle Player specific inputs (A=Play/Pause, B=Stop/Back, LB/RB=Seek)
                 if event.type == pygame.KEYDOWN:
                     if process_input:
                          if keys[pygame.K_SPACE] or keys[pygame.K_RETURN]: action_select = True; self.last_input_time = current_time + 0.1
                          elif keys[pygame.K_BACKSPACE] or keys[pygame.K_ESCAPE]: action_back = True; self.last_input_time = current_time + 0.1
                          elif keys[pygame.K_RIGHTBRACKET]: action_seek_forward = True; self.last_input_time = current_time + 0.05
                          elif keys[pygame.K_LEFTBRACKET]: action_seek_backward = True; self.last_input_time = current_time + 0.05
                 elif event.type == pygame.JOYBUTTONDOWN:
                      if process_input and joystick:
                           if event.button == A_BUTTON and not self.button_pressed[A_BUTTON]: action_select = True; self.button_pressed[A_BUTTON] = True; self.last_input_time = current_time + 0.1
                           elif event.button == B_BUTTON and not self.button_pressed[B_BUTTON]: action_back = True; self.button_pressed[B_BUTTON] = True; self.last_input_time = current_time + 0.1
                           elif event.button == RB_BUTTON and not self.button_pressed[RB_BUTTON]: action_seek_forward = True; self.button_pressed[RB_BUTTON] = True; self.last_input_time = current_time + 0.05
                           elif event.button == LB_BUTTON and not self.button_pressed[LB_BUTTON]: action_seek_backward = True; self.button_pressed[LB_BUTTON] = True; self.last_input_time = current_time + 0.05
                 elif event.type == pygame.JOYBUTTONUP: # Reset button state on release
                     if event.button in self.button_pressed: self.button_pressed[event.button] = False

             elif self.active_menu:
                 # Handle Menu specific inputs (Up/Down Nav, A=Select, B=Back)
                 if event.type == pygame.KEYDOWN:
                      if process_input:
                           if keys[pygame.K_UP]: direction = -1; self.last_input_time = current_time
                           elif keys[pygame.K_DOWN]: direction = 1; self.last_input_time = current_time
                           elif keys[pygame.K_RETURN] or keys[pygame.K_SPACE]: action_select = True; self.last_input_time = current_time + 0.1
                           elif keys[pygame.K_BACKSPACE] or keys[pygame.K_ESCAPE]: action_back = True; self.last_input_time = current_time + 0.1
                 elif event.type == pygame.JOYBUTTONDOWN:
                      if process_input and joystick:
                           if event.button == A_BUTTON and not self.button_pressed[A_BUTTON]: action_select = True; self.button_pressed[A_BUTTON] = True; self.last_input_time = current_time + 0.1
                           elif event.button == B_BUTTON and not self.button_pressed[B_BUTTON]: action_back = True; self.button_pressed[B_BUTTON] = True; self.last_input_time = current_time + 0.1
                 elif event.type == pygame.JOYBUTTONUP:
                      if event.button in self.button_pressed: self.button_pressed[event.button] = False
                 elif event.type == pygame.JOYHATMOTION:
                      if process_input:
                           hat = event.value
                           if hat == DPAD_UP and not self.dpad_pressed['up']: direction = -1; self.dpad_pressed['up'] = True; self.last_input_time = current_time
                           elif hat != DPAD_UP: self.dpad_pressed['up'] = False
                           if hat == DPAD_DOWN and not self.dpad_pressed['down']: direction = 1; self.dpad_pressed['down'] = True; self.last_input_time = current_time
                           elif hat != DPAD_DOWN: self.dpad_pressed['down'] = False
                 elif event.type == pygame.JOYAXISMOTION:
                      if process_input and event.axis == 1:
                          axis_y = event.value
                          if axis_y < -STICK_THRESHOLD and not self.analog_y_pressed['up']: direction = -1; self.analog_y_pressed['up'] = True; self.last_input_time = current_time
                          elif axis_y >= -STICK_THRESHOLD: self.analog_y_pressed['up'] = False
                          if axis_y > STICK_THRESHOLD and not self.analog_y_pressed['down']: direction = 1; self.analog_y_pressed['down'] = True; self.last_input_time = current_time
                          elif axis_y <= STICK_THRESHOLD: self.analog_y_pressed['down'] = False


        # --- Process Actions for Player / Menu ---
        if action_toggle_fullscreen:
            print("Toggling fullscreen...")
            pygame.display.toggle_fullscreen()

        if self.active_player:
            if action_select: self.active_player.play_pause()
            elif action_back:
                # Store fullscreen state *before* stopping video
                fullscreen_to_restore = self.was_fullscreen_before_video
                self.active_player.stop()
                self.active_player = None
                 # Restore menu
                if not self.menu_stack: self.build_main_menu()
                else: self.active_menu = self.menu_stack[-1]
                # Restore fullscreen if needed *after* stopping player and showing menu
                if fullscreen_to_restore:
                    pygame.display.toggle_fullscreen()
                    self.was_fullscreen_before_video = False # Reset flag
                else:
                    # Ensure flag is reset even if wasn't fullscreen
                    self.was_fullscreen_before_video = False
            elif action_seek_forward: self.active_player.seek(10)
            elif action_seek_backward: self.active_player.seek(-10)

        elif self.active_menu:
            if direction != 0: self.active_menu.navigate(direction)
            elif action_select: self.execute_menu_action()
            elif action_back: self.go_back_menu()


    def go_back_menu(self):
         """ Handles the 'back' action, popping from the menu stack."""
         if self.active_screen: # If a screen is active, 'back' closes it
              self.active_screen = None
              if self.menu_stack: self.active_menu = self.menu_stack[-1]
              else: self.build_main_menu()
         elif len(self.menu_stack) > 1: # Otherwise, go back in menu stack
             self.menu_stack.pop()
             self.active_menu = self.menu_stack[-1]
         # else: Do nothing if already at main menu and no screen active

    def execute_menu_action(self):
        """Executes the action associated with the selected menu item."""
        if not self.active_menu: return
        action = self.active_menu.get_selected_action()
        if action is None: return
        print(f"Menu Action: {action}")

        # Handle non-screen actions first
        if action == "back": self.go_back_menu()
        elif action == "settings":
            settings_menu = self.build_settings_menu()
            self.menu_stack.append(settings_menu)
            self.active_menu = settings_menu
        elif action == "themes":
             themes_menu = self.build_themes_menu()
             self.menu_stack.append(themes_menu)
             self.active_menu = themes_menu
        elif action.startswith("set_theme_"):
             theme_name = action.split("set_theme_")[1]
             self.update_theme(theme_name)
             self.go_back_menu()
        elif action == "import_music":
            dir_path = select_directory("Select Music Folder")
            if dir_path and dir_path not in self.settings["music_dirs"]:
                 self.settings["music_dirs"].append(dir_path); save_settings(self.settings)
                 print(f"Added music directory: {dir_path}")
        elif action == "import_videos":
             dir_path = select_directory("Select Videos Folder")
             if dir_path and dir_path not in self.settings["video_dirs"]:
                  self.settings["video_dirs"].append(dir_path); save_settings(self.settings)
                  print(f"Added video directory: {dir_path}")
        elif action == "import_photos":
             dir_path = select_directory("Select Photos Folder")
             if dir_path and dir_path not in self.settings["image_dirs"]:
                  self.settings["image_dirs"].append(dir_path); save_settings(self.settings)
                  print(f"Added image directory: {dir_path}")
        elif action == "reset_imported_paths":
            # Show confirmation submenu
            self.menu_stack.append(self.active_menu)
            self.active_menu = Menu(
                [
                    ("Are you sure you want to reset?", None),
                    ("Yes", "confirm_reset_imported_paths"),
                    ("No", "cancel_reset_imported_paths")
                ],
                self.font
            )
            self.active_menu.update_theme(self.current_theme_name)
            return
        elif action == "confirm_reset_imported_paths":
            print("Resetting imported paths...")
            self.settings["music_dirs"] = []
            self.settings["video_dirs"] = []
            self.settings["image_dirs"] = []
            self.settings["games"] = [] # Also reset games
            save_settings(self.settings)
            print("Imported paths reset.")
            self.go_back_menu()
            return
        elif action == "cancel_reset_imported_paths":
            self.go_back_menu()
            return
        elif action == "github": webbrowser.open_new_tab("https://github.com/BannedPenta01")
        elif action == "quit": self.running = False

        # Handle screen activation
        elif action == "about":
             self.active_screen = AboutScreen(self.font, self.current_theme_name)
             self.active_menu = None # Hide menu
        elif action == "donate":
             self.active_screen = DonateScreen(self.font, self.current_theme_name)
             self.active_menu = None # Hide menu

        # Handle media selection (THESE WERE MISSING)
        elif action == "music":
              music_menu = self.build_media_menu("music")
              self.menu_stack.append(music_menu)
              self.active_menu = music_menu
        elif action == "videos":
              video_menu = self.build_media_menu("videos")
              self.menu_stack.append(video_menu)
              self.active_menu = video_menu
        elif action == "photos":
              photo_menu = self.build_media_menu("photos")
              self.menu_stack.append(photo_menu)
              self.active_menu = photo_menu
        elif action.startswith("play_music_"):
              index = int(action.split("play_music_")[1])
              self.active_player = self.music_player
              # Complete the logic:
              if 0 <= index < len(self.active_player.playlist):
                   self.active_player.current_index = index
                   self.active_player._load_current_track()
                   self.active_player.play_pause()
                   self.active_menu = None # Hide menu when playing
        # --- ADD MISSING BLOCKS --- Start
        elif action.startswith("play_video_"):
              index = int(action.split("play_video_")[1])
              self.active_player = self.video_player
              if 0 <= index < len(self.active_player.playlist):
                  # --- Fullscreen Handling --- Start
                  self.was_fullscreen_before_video = pygame.display.is_fullscreen()
                  if self.was_fullscreen_before_video:
                      print("Video started: Turning off fullscreen for main window...")
                      pygame.display.toggle_fullscreen()
                  # --- Fullscreen Handling --- End
                  self.active_player.current_index = index
                  self.active_player._load_current_track() # Prepares duration etc.
                  self.active_player.play_pause() # This now calls _launch_ffplay without -nodisp
                  self.active_menu = None # Hide menu when playing
        elif action.startswith("view_photo_"):
              index = int(action.split("view_photo_")[1])
              self.active_player = self.image_viewer
              if 0 <= index < len(self.active_player.playlist):
                  self.active_player.current_index = index
                  self.active_player._load_current_track()
                  # No play_pause for images, just load and hide menu
                  self.active_menu = None # Hide menu when viewing
        # --- ADD MISSING BLOCKS --- End
        elif action.startswith("play_game_"):
            index = int(action.split("play_game_")[1])
            games = self.settings.get("games", [])
            if 0 <= index < len(games):
                self.active_screen = GamePlaceholderScreen(self.font, self.current_theme_name, os.path.basename(games[index]))
                self.active_menu = None
        elif action == "games":
            games_menu = self.build_games_menu()
            self.menu_stack.append(games_menu)
            self.active_menu = games_menu
        elif action == "import_games":
            # Use file dialog to select one or more .ipg files
            root = Tk()
            root.withdraw()
            root.attributes('-topmost', True)
            file_paths = filedialog.askopenfilenames(
                title="Select iPod Game Files (.ipg)",
                filetypes=[("iPod Games", "*.ipg"), ("All Files", "*.*")]
            )
            root.destroy()
            if file_paths:
                # Add new games, avoiding duplicates
                new_games = [f for f in file_paths if f not in self.settings["games"]]
                if new_games:
                    self.settings["games"].extend(new_games)
                    save_settings(self.settings)
                    print(f"Imported games: {new_games}")
                else:
                    print("No new games to import (all already imported)")

    def update(self):
        """Update game state."""
        if self.active_player:
            self.active_player.update()

    def draw(self):
        self.screen.fill(BLACK)

        # --- Draw Active Component: Screen > Player > Menu ---
        if self.active_screen:
            self.active_screen.draw(self.screen)
        elif self.active_player:
            self.active_player.draw(self.screen)
        elif self.active_menu:
            self.active_menu.draw(self.screen)
        else: # Fallback if nothing is active
            fallback_surf = self.font.render("Perfect Pineapple Player", True, WHITE)
            fallback_rect = fallback_surf.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2)
            self.screen.blit(fallback_surf, fallback_rect)

        # --- Draw Persistent UI Elements ---
        # Draw side panel only if a menu is active (not player or screen)
        if self.active_menu and not self.active_screen and not self.active_player:
             if not (self.active_player and isinstance(self.active_player, (ImageViewer, MusicPlayer))): # Keep hide logic? Maybe redundant now.
                  self.side_panel.draw(self.screen)

        self.status_bar.draw(self.screen) # Status bar always on top

        pygame.display.flip()


    def run(self):
        """Main game loop."""
        while self.running:
            self.handle_input()
            # --- Detect ffplay window close (X) ---
            if self.active_player and isinstance(self.active_player, VideoPlayer):
                if self.active_player._ffplay_process and self.active_player._ffplay_process.poll() is not None:
                    # ffplay process exited (user closed window)
                    self.active_player.stop()
                    self.active_player = None
                    if not self.menu_stack: self.build_main_menu()
                    else: self.active_menu = self.menu_stack[-1]
                    # Restore fullscreen if needed
                    if self.was_fullscreen_before_video:
                        pygame.display.toggle_fullscreen()
                        self.was_fullscreen_before_video = False
            # --- ADD MISSING UPDATE CALL --- #
            self.update()
            # --- END ADD --- #
            self.draw()
            self.clock.tick(60)

        # Cleanup before exit
        if self.active_player:
            # Ensure player resources are released (includes stopping ffplay)
            self.active_player.stop()
        pygame.quit()
        sys.exit()


# --- Entry Point ---
if __name__ == '__main__':
    try:
        RED = (255, 0, 0)
        # No need for Tkinter root setup here anymore
        player = PerfectPineapplePlayer()
        player.run()
    except Exception as e:
        print("\n--- UNHANDLED EXCEPTION ---")
        import traceback
        traceback.print_exc()
        print("--------------------------")
        try: pygame.quit()
        except Exception: pass
        input("An error occurred. Press Enter to exit.")
        sys.exit(1) 

# --- Add a placeholder screen for games --- # REMOVED FROM HERE