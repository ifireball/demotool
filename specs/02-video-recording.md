# Video Recording Specification

## Overview

This specification defines the video recording functionality for the demotool project. The recording system integrates with demo sessions to capture VNC streams as video files, supporting multiple recording sections within a single demo workflow.

## Core Concepts

### Recording Session

A recording session represents a single video capture operation within a demo context:

- Starts recording when context is entered
- Stops recording when context is exited
- Manages output file creation and cleanup
- Handles recording failures gracefully

### Recording Context Integration

The recording system integrates with the existing demo session structure:

- Uses `demo.directory` for output file placement
- Integrates with VM objects via `vm.vnc_port`
- Supports multiple recording sections per demo
- Follows the `@contextmanager` pattern

## Architecture Components

### 1. Recording Manager (`vm.record`)

```python
with vm.record("section-name"):
    # Recording is active during this context
    # Video file automatically created and managed
    # Recording stops when context exits
```

**Responsibilities:**

- Start VNC stream recording when context is entered
- Stop recording and finalize video file when context exits
- Manage recording process lifecycle
- Handle recording failures and cleanup
- Manage output file creation and cleanup internally

### 2. Recording Process Controller

**VLC Integration:**

- Use VLC command-line interface for maximum control and reliability
- Connect to VNC stream via `vm.vnc_port`
- Manage VLC process lifecycle via subprocess
- Handle remote control interface for clean shutdown

**Recording Process Details:**

- VLC command: `vlc -I rc --rc-quiet vnc://localhost:{vnc_port}`
- Remote control port: 4212 (VLC default)
- Output format: MP4 with H.264 video codec
- Audio: MP3 with 128kbps bitrate
- Mouse pointer: Include via `--screen-mouse-image` option

## Implementation Details

### Recording Start Sequence

1. Validate VNC port availability
   - Attempt TCP connection to `localhost:{vnc_port}` with 5-second timeout
   - Fail if connection cannot be established within timeout
2. Create output directory if it doesn't exist
   - Use `pathlib.Path.mkdir(parents=True, exist_ok=True)`
3. Generate output filename based on section name
   - Sanitize section name: replace invalid characters with underscores
   - Ensure filename is valid for target filesystem
4. Check available disk space
   - Use `shutil.disk_usage(output_directory)` to check available space
   - Require minimum 1GB available space for recording
   - Fail with `DiskSpaceError` if insufficient space
5. Start VLC recording process via subprocess
   - Use `subprocess.Popen` with `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL`
   - Store process reference for lifecycle management
   - Store process in instance variable: `self._vlc_process = process`
6. Wait for recording to stabilize
   - Fixed 2-second delay after VLC process start
   - Verify VLC process is still running after delay
7. Set recording state to active
   - Mark internal state as recording
   - Log successful recording start

**Output File Naming:**

- Format: `{section-name}.mp4`
- Location: `demo.directory / {section-name}.mp4`
- Example: `demo-videos/my-cool-demo/calculator.mp4`
- Uniqueness: Overwrite existing files with same name

### Recording Stop Sequence

1. Send VLC quit command via remote control interface
2. Wait for VLC process to terminate gracefully
   - Wait up to 10 seconds for graceful termination
   - Check process status every 100ms
3. Verify output file exists and has non-zero size
   - Check file exists using `pathlib.Path.exists()`
   - Verify file size > 1024 bytes (minimum valid MP4 size)
   - Check file is readable and not corrupted
4. Set recording state to inactive
5. Clean up temporary files and processes
   - Remove VLC temporary files from system temp directory
   - Terminate any remaining VLC processes

**VLC Shutdown Process:**

```python
import socket

# Connect to VLC remote control interface
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(10)  # 10 second timeout
    sock.connect(('localhost', 4212))
    sock.send(b'quit\n')
    sock.close()
```

- Use Python `socket` module for direct TCP communication
- Timeout: 10 seconds for graceful shutdown
- Force kill if graceful shutdown fails

### Recording Quality Settings

**Configuration:**

- Video codec: H.264
- Video bitrate: 2 Mbps
- Resolution: Native VNC resolution
- Frame rate: 30 fps
- Audio codec: MP3
- Audio bitrate: 128 kbps

**VLC Command Template:**

```bash
vlc -I rc --rc-quiet \
    vnc://localhost:{vnc_port} \
    --sout="#transcode{vcodec=h264,vb=2000,acodec=mp3,ab=128}:std{access=file,mux=mp4,dst={output_file_path}}" \
    --screen-mouse-image=/usr/share/icons/Adwaita/cursors/default
```

**Command Construction:**

- `{vnc_port}`: Replace with actual VNC port number from `vm.vnc_port`
- `{output_file_path}`: Replace with absolute path to output file (e.g., `/path/to/demo-videos/demo-name/section-name.mp4`)
- Use `str(output_file.absolute())` to get absolute path for VLC command

### Mouse Pointer Recording

**Pointer Image Configuration:**

- Cursor image path: `/usr/share/icons/Adwaita/cursors/default`
- Skip mouse pointer if image file not found

## Error Handling

### Error Classes

**Base Exception:**

```python
class RecordingError(Exception):
    """Base exception for all recording-related errors."""
    pass
```

**Specific Exceptions:**

```python
class RecordingStartError(RecordingError):
    """Raised when recording cannot be started."""
    pass

class VNCConnectionError(RecordingError):
    """Raised when VNC connection fails."""
    pass

class OutputDirectoryError(RecordingError):
    """Raised when output directory cannot be created."""
    pass

class DiskSpaceError(RecordingError):
    """Raised when insufficient disk space for recording."""
    pass

class VNCStreamError(RecordingError):
    """Raised when VNC stream becomes unavailable."""
    pass

class OutputFileError(RecordingError):
    """Raised when output file is corrupted or invalid."""
    pass
```

### Recording Failures

**Start Recording Failures:**

- VLC process fails to start: Log error with process output, raise `RecordingStartError`
- VNC connection fails: Log error with connection details, raise `VNCConnectionError`
- Output directory creation fails: Log error with path and permissions, raise `OutputDirectoryError`

**During Recording Failures:**

- VLC process crashes: Attempt restart once (wait 5 seconds), then fail with `RecordingStartError`
- Disk space full: Stop recording, log error with available space, raise `DiskSpaceError`
- VNC stream becomes unavailable: Stop recording, log error with stream status, raise `VNCStreamError`

**Stop Recording Failures:**

- VLC shutdown timeout: Force kill process using `process.terminate()` then `process.kill()`, log warning
- Output file corruption: Log error with file size and modification time, raise `OutputFileError`
- Cleanup failures: Log warnings with specific failure details, continue with demo

### Error Recovery

**Automatic Recovery:**

- VLC process restart on crash (maximum 1 attempt, wait 5 seconds between attempts)
- Temporary file cleanup on partial failures
- Output directory recreation if deleted

**Manual Recovery:**

- Provide clear error messages with actionable steps
- Include file paths and process IDs in error logs
- Suggest manual cleanup commands if needed

### Recording-Specific Logging

**Required Log Messages:**

- Recording start: `INFO: Recording started for section '{section_name}' to {output_file}`
- Recording stop: `INFO: Recording stopped for section '{section_name}', file size: {size} bytes`
- VLC process start: `DEBUG: VLC process started with PID {pid}`
- VLC process stop: `DEBUG: VLC process stopped, exit code: {exit_code}`

**Context Information:**

- Demo name, section name, VNC port, output file path
- VLC process ID, exit codes, file sizes

## File Management

### Output Organization

**Directory Structure:**

```
demo-videos/
└── {demo-name}/
    ├── section1.mp4
    ├── section2.mp4
    └── section3.mp4
```

**File Cleanup:**

- Remove incomplete recordings on failures
- Preserve successful recordings
- Clean up temporary VLC files
- Handle partial file corruption

### Temporary Files

**VLC Process Management:**

- VLC process may create temporary files during recording
- Monitor system temp directory for files created during recording session
- Cleanup: Terminate VLC process and remove any temporary files
- Fallback: Manual cleanup instructions in error logs if automatic cleanup fails

## Implementation Notes

### Process Management

**VLC Process Lifecycle:**

- Monitor process status using `process.poll()` method
- Handle process termination in context manager cleanup

**Resource Monitoring:**

- Check disk space before starting recording (minimum 1GB required)
- Monitor VLC process memory usage during recording
- Clean up process and temporary files on context exit

### Error Detection

**File Corruption Detection:**

- Verify file size > 1024 bytes (minimum valid MP4)
- Check file is readable using `pathlib.Path.is_file()`
- Validate file can be opened without errors

## Dependencies

**Python Libraries:**

- `subprocess` - Process management
- `pathlib` - File path handling
- `shutil` - Disk space checking
- `psutil` - Process monitoring (optional)

**System Dependencies:**

- `vlc` - Video recording engine

## Future Considerations

- Alternative recording engines (FFmpeg, GStreamer)
- Hardware acceleration support
- Multi-stream recording
- Recording compression and optimization
- Integration with video editing tools
