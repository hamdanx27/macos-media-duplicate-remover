# macos-media-duplicate-remover

A macOS utility for finding and reviewing visually duplicated or near-duplicated images and videos, then deleting unwanted files directly from a local web dashboard.

Unlike a conventional duplicate finder that only compares filenames, file sizes, or exact file contents, this script uses **perceptual hashing (pHash)** to identify media that looks the same or very similar. Images are hashed directly, while videos are represented by a perceptual hash of a frame taken from the middle of the video. Files with the same generated perceptual hash are grouped together for visual review.

> **Important:** This project is designed for local use on macOS. The dashboard is served by Flask on `127.0.0.1:5000`, so it is intended to be accessed from the same computer running the script.

## Features

- **Native macOS folder selection** using AppleScript and Finder, with support for selecting **multiple folders at once**.
- **Recursive scanning** of the selected parent directories, including files inside their subdirectories.
- **Image support** for:
  - JPG / JPEG
  - PNG
  - HEIC
  - WEBP
- **Video support** for:
  - MP4
  - MOV
  - WEBM
  - AVI
  - MKV
  - M4V
- **Perceptual hashing (pHash)** to find visually identical or near-identical media rather than relying only on exact file matches.
- **Interactive Flask web dashboard** presenting detected match groups in a visual card layout.
- **Image previews** displayed directly in the dashboard.
- **Playable video previews** for browser-supported MP4, MOV, WEBM and M4V files, with `preload="metadata"` and conditional file serving to avoid unnecessarily loading the entire video up front.
- **Fallback display for unsupported video previews**, so formats such as AVI and MKV can still appear in duplicate groups even when the browser cannot play them directly.
- **File metadata display**, including filename, human-readable file size, extension and full path.
- **One-click deletion** from the dashboard using a local POST request to the Flask server.
- **Hidden-file skipping**, ignoring filenames beginning with `.` during the scan.
- **Pillow large-image safety handling**, relying on Pillow's built-in protection against potentially dangerous decompression bombs in unusually large image files.

## MAJOR CRITICAL WARNING: DELETE IS PERMANENT

**The `Delete` button in the dashboard deletes the selected file immediately and permanently.**

There is deliberately **no browser confirmation popup** before deletion. Clicking `Delete` sends the delete request straight to the Flask server, which removes the file from disk with Python's `os.remove()`.

There is also **no undo button** in the application.

Before deleting anything, carefully review the preview, filename, size and full path shown on the dashboard. Only delete a file when you are certain it is the copy you no longer need.

This application does not provide a recycle-bin, trash-management, versioning, backup, or restore mechanism. Whether macOS can recover a removed file through another system-level recovery or backup mechanism is outside the application's control.

## How Duplicate Detection Works

The scanning process is based on perceptual hashes:

1. The script recursively walks through every selected folder and its subdirectories.
2. Supported image and video files are identified by their file extension.
3. For images, Pillow opens the file and `imagehash.phash()` generates a perceptual hash.
4. For videos, OpenCV opens the video, seeks to approximately the middle frame, converts that frame to an image, and generates a pHash from that frame.
5. Files that produce the same pHash are collected into the same match group.
6. Groups containing more than one file are shown in the dashboard.

### Important implementation detail for videos

The current implementation does **not** compare every frame of a video. It uses a **single frame from roughly the middle of the video** to create the perceptual hash.

As a result, two videos can be grouped together when their middle frames look the same, even if other parts of the videos differ. Conversely, videos that are genuinely related may fail to match if their selected middle frames differ significantly.

## Prerequisites

You will need:

- **macOS**, because folder selection is implemented through `osascript` and Finder's native AppleScript interface.
- **Python 3**.
- A working **Terminal** environment.
- Internet access only for installing the Python dependencies; the duplicate scanning and dashboard itself run locally.

### Built-in Python modules used

The script also uses standard Python modules that do not need to be installed separately:

- `os`
- `subprocess`
- `threading`
- `webbrowser`

## Installation

Clone or download the project, then install the external Python dependencies with:

```bash
python3 -m pip install Pillow imagehash opencv-python Flask
```

The dependencies correspond to the imports used by the script:

| Package | Purpose |
|---|---|
| `Pillow` | Opens images and converts video frames into images for hashing |
| `imagehash` | Generates perceptual hashes using pHash |
| `opencv-python` | Opens videos and extracts the middle frame |
| `Flask` | Serves the local duplicate-review dashboard and handles deletion requests |

## Usage

### 1. Open Terminal

Navigate to the directory containing the Python script. For example:

```bash
cd /path/to/mac-media-one-click-deduper
```

### 2. Run the script

```bash
python3 duplicate_finder.py
```

The script will print a startup message and open the native macOS folder picker.

### 3. Select folders to scan

The macOS folder picker allows **multiple folder selections**.

Choose the parent directories containing the images and videos you want to check. The script recursively scans the selected folders and their subfolders.

For example, you might select:

```text
~/Pictures
~/Movies
~/Downloads
```

The script reports how many folders were selected and begins generating visual hashes.

> Video files can take longer to process because OpenCV must open each video and extract a frame for hashing.

### 4. Wait for scanning to complete

The terminal will display progress messages such as:

```text
Scanning 3 folder(s)...
Generating visual hashes (this may take a minute for videos)...
```

When duplicate groups are found, the script starts the Flask server on port `5000` and automatically opens:

```text
http://127.0.0.1:5000
```

### 5. Review the dashboard

Each detected group is displayed together so you can visually compare the files.

For each file, the dashboard can show:

- a visual image preview, or
- a playable video preview where the browser supports the format, or
- a message explaining that the video format cannot be previewed directly in the browser.

The card also displays:

- filename
- file size
- file type / extension
- full file path

### 6. Delete unwanted duplicates

Click **Delete** on the file you no longer want.

The deletion request is sent immediately to the local Flask server. When successful, the file's card is hidden from the dashboard.

**There is no confirmation step and no undo function.** See the warning above before using the button.

### 7. Stop the server

When you have finished reviewing the results, return to the Terminal window running Flask and press:

```text
Ctrl+C
```

This stops the local server and ends the application.

## Example Scenarios

The following examples are illustrative. The actual filenames and paths will depend on your own media library.

### Scenario 1: Same photo, different file sizes

A camera photo and a resized/exported copy can look effectively identical while having different file sizes:

```text
Match Group
├── Original
│   ├── Name: IMG_1042.JPG
│   ├── Size: 5.84 MB
│   └── Path: /Users/<user>/Pictures/Camera/IMG_1042.JPG
│
└── Duplicate
    ├── Name: IMG_1042_copy.JPG
    ├── Size: 1.92 MB
    └── Path: /Users/<user>/Pictures/Exports/IMG_1042_copy.JPG
```

The different sizes and paths do not prevent the files from being grouped when they generate the same perceptual hash.

### Scenario 2: The same visual image in different formats

The same picture may also exist in multiple formats:

```text
Match Group
├── Name: holiday-photo.PNG
│   ├── Size: 7.10 MB
│   └── Path: /Users/<user>/Pictures/Archive/holiday-photo.PNG
│
└── Name: holiday-photo.WEBP
    ├── Size: 1.24 MB
    └── Path: /Users/<user>/Pictures/Web/holiday-photo.WEBP
```

The script does not require the extension or file size to be identical. It hashes the visual content instead.

### Scenario 3: Similar video files

For videos, matching is based on the pHash of the selected middle frame:

```text
Match Group
├── Name: trip-video.MP4
│   ├── Size: 482.30 MB
│   └── Path: /Users/<user>/Movies/Camera/trip-video.MP4
│
└── Name: trip-video-copy.MOV
    ├── Size: 356.70 MB
    └── Path: /Users/<user>/Movies/Exports/trip-video-copy.MOV
```

Because only a middle frame is hashed, treat video matches as **potential visual duplicates** and inspect the files before deleting anything.

## DecompressionBombWarning and Large Images

When Pillow opens a very large image, it can issue a `DecompressionBombWarning` or related protection error. Pillow includes this safeguard because specially crafted or extremely large images can consume excessive memory or CPU when decompressed, potentially causing a denial-of-service condition.

The script itself does not disable this protection. It simply attempts to open the image with Pillow, and its exception handling allows scanning to continue when an individual file cannot be hashed.

### Processing known large, trusted images

If you are intentionally scanning very large images that you trust and understand, you can reconfigure Pillow's decompression-bomb settings in the script **before calling `Image.open()`**.

For example, Pillow allows its maximum image pixel limit to be adjusted through `Image.MAX_IMAGE_PIXELS`.

A commonly used approach for a controlled local workload is to set a higher limit explicitly:

```python
from PIL import Image

Image.MAX_IMAGE_PIXELS = 200_000_000
```

Only raise the limit when you understand the size of the files being processed. Do not blindly disable the safeguard for untrusted images.

> **Note:** The exact warning/error behaviour depends on the Pillow version installed. The safest option is normally to leave Pillow's default protection enabled unless you have a specific reason to change it.

## Limitations and Behaviour to Know

- **Exact pHash grouping:** the script puts files in the same duplicate group when their generated pHash strings are equal. It does not currently calculate a Hamming-distance threshold between different pHashes.
- **Video hashing uses one frame:** only approximately the middle frame is used for a video's perceptual hash.
- **No similarity score is shown:** the dashboard does not display a percentage or similarity distance.
- **No automatic "keep the best copy" logic:** the script shows all files in a match group and leaves the deletion decision to the user.
- **No recycle-bin integration:** deletion uses `os.remove()` directly.
- **Browser support varies by video format:** MP4, MOV, WEBM and M4V are marked as browser-playable by the script, while AVI and MKV receive a non-playable placeholder in the dashboard.
- **The server is local:** the application listens on port `5000` and opens the dashboard at `127.0.0.1:5000`.
- **The dashboard should be treated as a local administration interface:** it exposes file-serving and deletion routes for the files identified by the scan. Do not expose the development server to an untrusted network.
- **The scan only considers the extensions listed by the script:** other image or video formats will be ignored.
- **Hidden files are skipped:** files whose names begin with `.` are not processed.

## Project Structure

A minimal project layout can look like this:

```text
macos-media-duplicate-remover/
├── duplicate_finder.py
└── README.md
```

## License

This project is licensed under the MIT License. See the LICENSE file for details.
