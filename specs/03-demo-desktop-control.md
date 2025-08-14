# Demo Desktop Control Specification

## Overview

This specification defines the desktop automation and interaction functionality
for the demotool project. The desktop control system provides high-level
automation methods for common demo tasks, integrating with the existing demo
session structure to enable smooth, human-like interactions within VM
environments.

## Core Concepts

### Desktop Control Session

A desktop control session represents the automation context within a VM:

- Integrates with existing demo sessions and VM objects
- Provides high-level automation methods for common demo patterns
- Handles automation failures gracefully with recovery strategies
- Supports both recorded and non-recorded interaction sequences

### Integration with Demo Architecture

The desktop control system integrates with the existing demo session structure:

- Uses `vm.vnc_port` for VNC connection to the VM
- Integrates with recording contexts via `vm.record()` for demo automation
- Follows the established error handling and logging patterns

## Architecture Components

### 1. VM Desktop Control Integration

The desktop control API is provided directly on the VM object, integrating with the existing demo session structure:

```python
with demo.vm("fedora-42") as vm:
    # Desktop automation methods available directly on vm object
    vm.mouseDrag(10, 10, step=10)
    vm.type("calculator")
    vm.keyPress("enter")
```

**Integration Points:**

- Uses `vm.vnc_port` for VNC connection
- Available directly on VM objects for easy access
- Integrates with recording contexts via `vm.record()` for demo automation
- Follows the established demo session patterns

### 2. VNC Interaction Engine

**VNC Tool Integration:**

- Use the Python bindings provided by vncdotool as described in the [vncdotool documentation](https://vncdotool.readthedocs.io/en/latest/library.html)
- Integrate directly with the `vncdotool.api` module for VNC connection and automation
- Handle VNC connection lifecycle and error recovery

**Connection Management:**

- VNC connection is established by the `demo.vm()` context manager
- VM object receives an established vncdotool client connection
- Connection lifecycle is managed by the context manager

## Implementation Details

### VNC Connection Implementation

**VM Object Interface:**

The VM object receives a vncdotool client connection from the `demo.vm()` context manager:

```python
class VM:
    def __init__(self, vnc_client):
        self._vnc_client = vnc_client
```

**Note:** The `demo.vm()` context manager establishes the VNC connection and passes the connected client to the VM object.

### Mouse Operations

**Mouse Operation Methods:**

The VM object provides mouse automation methods that forward to vncdotool's existing API:

```python
def mouseDrag(self, x: int, y: int, step: int = 10):
    """Animate moving the mouse to coordinates with step size."""
    
def mousePress(self, button: int = 1):
    """Press mouse button (1=left, 2=middle, 3=right)."""
    
def click(self, button: int = 1):
    """Click mouse button."""
    
def move(self, x: int, y: int):
    """Move mouse to absolute coordinates."""
```

**Note:** These methods forward to vncdotool's existing API implementation.

### Keyboard Operations

**Keyboard Operation Methods:**

The VM object provides keyboard automation methods:

```python
def keyPress(self, key: str):
    """Press and release a single key."""
    
def keyDown(self, key: str):
    """Press a single key."""
    
def keyUp(self, key: str):
    """Release a single key."""

def pause(self, seconds: float):
    """Pause for specified number of seconds."""
```

**Note:** These methods forward to vncdotool's existing API implementation.

**Custom Implementation Methods:**

```python
def type(self, text: str):
    """Type text with human-like timing.
    
    Implementation: For each character in text, call keyPress(char) with a 0.1 second delay between characters.
    """
    
def keyCombo(self, *keys: str):
    """Press multiple keys simultaneously then release in reverse order.
    
    Implementation: Call keyDown() for each key in sequence, then call keyUp() for each key in reverse order.
    """

def unlock(self):
    """Unlock the desktop session for the demo user.
    
    Implements the sequence: 
      keyCombo("super", "l") pause(1) keyPress("space") pause(1) 
      keyPress("bsp") keyPress("bsp") type("demokudasaidomo") keyPress("enter")
    """
```

**Note:** These methods require custom implementation to provide enhanced functionality beyond vncdotool's basic API.

### Screen Operations

**Screen Operation Methods:**

The VM object provides screen operations that forward to vncdotool's existing API:

```python
def captureScreen(self, filename: str):
    """Capture screenshot to specified filename."""
    
def expectScreen(self, image_path: str, maxrms: float = 10.0):
    """Wait for screen to match expected image."""
```

**Note:** These methods forward to vncdotool's existing API implementation.

## Error Handling

**Note:** Error handling follows the general coding requirements specified in `specs/00-general.md`. The desktop control system should log errors appropriately and propagate exceptions when automation operations fail. No complex retry logic or recovery strategies are required.

## Integration with Recording

### Recording Context Integration

**Automation During Recording:**

```python
with vm.record("demo-section") as recording:
    # All automation operations are recorded
    vm.type("2 + 2 = 4")
    vm.keyPress("enter")
```

**Non-Recorded Automation:**

```python
# Setup operations not recorded
vm.unlock()

with vm.record("demo-section") as recording:
    # Recorded automation operations
    vm.type("calculator")
    # ... demo automation
```

## Configuration

**Note:** This specification focuses on simple, straightforward automation without complex configuration options. Configuration is handled through vncdotool's existing API and the established demo session patterns.

## Dependencies

**Python Libraries:**

- `vncdotool` - VNC interaction and automation via Python bindings

**System Dependencies:**

- `vncdotool` - VNC automation tool
