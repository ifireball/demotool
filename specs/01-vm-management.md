# VM Management and Demo Creation Specification

## Overview

This specification defines the core architecture for automated demo creation using virtual machines. The system provides a Python-based framework for orchestrating VM lifecycle management, automated interactions, and demo generation workflows.

## Core Concepts

### Demo Session

A demo session represents a complete demo recording workflow, including:

- VM provisioning and management
- Automated interaction sequences
- Output organization and file management

**Demo Directory Structure:**

- Base directory: `demo-videos/` (relative to current working directory)
- Per-demo directory: `demo-videos/{demo-name}/`
- Example: `demo-videos/my-cool-demo/`

### VM Image Management

- Base images created using `virt-builder` templates
- Workstation environment packages pre-installed
- Images stored in XDG cache directory for reuse
- Copy-on-write (COW) layers for VM instances

**Base Image Details:**

- Image storage: Use XDG cache directory via `xdg` Python library
- Default path: `~/.cache/demotool/images/` (respects `$XDG_CACHE_HOME`)
- Image naming: `{distro}-{version}.qcow2` (e.g., `fedora-42.qcow2`)
- Required package: `@workstation-product-environment` (installed via virt-builder `--install` option)
- Image caching: Only create if not already present in cache
- Image validation: Check file exists, is readable, and has valid qcow2 format
- Corrupted image handling: Delete corrupted image and recreate

### Demo User Environment

- Pre-configured desktop session for demo user
- Automated login and session management
- Consistent starting state for reproducible demos

**Demo User Setup:**

- Username: `demo`
- Password: `demokudasaidomo`
- Group: Added to `wheel` group for sudo permissions
- Creation: Via virt-builder `--firstboot-command` option

## Architecture Components

### 1. Demo Session Manager (`demotool.startdemo`)

```python
with demotool.startdemo("demo-name") as demo:
    # Demo session context
    # Manages output directory creation
    # Handles session lifecycle
```

**Responsibilities:**

- Create and manage demo output directories (lazily, only when first output file is created)
- Coordinate VM lifecycle within demo context
- Handle session cleanup and resource management

**Demo Object Properties:**

- `demo.directory` - `pathlib.Path` object pointing to the demo output directory
- Example: `demo.directory` resolves to `./demo-videos/my-cool-demo/`

### 2. VM Lifecycle Manager (`demo.vm`)

```python
with demo.vm("fedora-42") as vm:
    # VM instance context
    # VM is fully booted and ready when context is entered
    # Handles VM creation, startup, and shutdown
    # Manages VM state
```

**Responsibilities:**

- VM creation from base images
- VM state management and cleanup
- VNC port detection and configuration
- Delete existing VM if found and create fresh instance for each demo
- Ensure VM is fully booted and desktop is ready before returning vm object

**VM Boot Sequence:**

1. Create VM from base image
2. Start VM and wait for libvirt to report running state
3. Wait for VNC port to become available
4. Wait for VM to complete boot process (configurable timeout)
5. Detect desktop ready state (see Desktop Ready Detection below)
6. Return vm object only when fully ready

**Boot Timeout Configuration:**

- Default timeout: 120 seconds
- Configurable via environment variable `DEMOTOOL_BOOT_TIMEOUT` (in seconds)
- Timeout applies to entire boot sequence (VM start + desktop ready)

**Desktop Ready Detection:**

- Wait for VNC port to respond to connection attempts
- Add 10-second delay after VNC port is responsive to allow desktop to fully load
- Consider VM ready when VNC is responsive plus delay period
- No need to wait for user login - demo user setup happens during image creation

**VM Naming Convention:**

- Format: `demo-{demo-name}`
- Example: `demo-my-cool-demo`
- Uniqueness: Ensured by deleting existing VM before creating new one

## Implementation Details

### Base Image Creation

- Use `virt-builder` for consistent base image generation
- Install workstation environment packages during image creation
- Store images in XDG cache directory (`~/.cache/demotool/images/`)
- Avoid creating an image if we already have it in cache

### VM Instance Management

- Create COW layers from base images for each VM instance
- Generate unique VM names based on demo identifier
- Delete existing VM if found and create fresh instance for each demo
- Handle VNC port allocation and configuration

**VNC Port Management:**

- Port allocation: Use libvirt's automatic VNC port allocation
- Port communication: Available via `vm.vnc_port` property
- Port cleanup: Automatically handled by libvirt when VM is deleted
- Setup the demo VM with CPU/Memory resources equivalent to 50% of the host machine
- Use the `libvirt` Python bindings
- Connect to `qemu:///session` for user session (no root privileges required)
- Delete the VM when exiting the `vm` context

**Resource Allocation Details:**

- CPU: 50% of host CPU cores (minimum 1, maximum 8)
- RAM: 50% of host RAM (minimum 4GB, maximum 32GB)
- Disk: COW layer on base image (no additional allocation)
- Network: libvirt usermode networking (no setup required)

**Resource Detection:**

- CPU cores: Use `os.cpu_count()` or `multiprocessing.cpu_count()`
- RAM: Use `psutil.virtual_memory().total` for total system memory
- Apply 50% calculation with min/max limits

**VM Performance Optimization:**

- Use virtio devices where possible (virtio-blk for disk, virtio-net for network)
- Enable KVM acceleration with appropriate CPU flags
- Use sparse COW images for efficient disk usage
- Minimize memory ballooning overhead
- Enable CPU pinning for consistent performance

### Demo Output Organization

- Create structured output directories for each demo (lazily, only when first output file is created)
- Organize files by demo name
- Implement output file naming conventions
- Handle cleanup of temporary files and VM instances

## VM Object Interface

The `vm` object yielded by `demo.vm()` is a minimal stub that provides:

**Properties:**

- `vm.vnc_port` - VNC port number for the VM
- `vm.demo` - Reference to the parent demo object for output location lookup

**Implementation:**

- Use `@contextmanager` decorator on `demo.vm()` method
- Simple object passed to `yield` for easy lifecycle management
- No context manager methods needed on the VM object itself

## Usage Patterns

### Basic Demo Workflow

```python
import demotool

with demotool.recordDemo("demo-name", "fedora-42") as vm:
    # Demo VM is ready for interaction
    # Interaction details defined elsewhere
```

### Advanced Demo with Multiple Sections

```python
import demotool

with demotool.startdemo("complex-demo") as demo:
    with demo.vm("fedora-42") as vm:
        # Setup phase, possibly some VM interactions we do not want
        # to record like installing needed software
        
        # Demo sections with interaction details defined elsewhere
        with vm.record("section1"):
            pass  # Interaction details defined elsewhere
        
        with vm.record("section2"):
            pass  # Interaction details defined elsewhere
```

## Error Handling

- VM creation failure recovery
- Network connectivity issues
- Resource cleanup on failures
- Graceful degradation for non-critical operations

**Specific Error Scenarios:**

- **virt-builder failure**: Log error with file:line, use cached image if available, fail demo if no cached image
- **libvirt operations failure**: Log error with file:line, attempt cleanup, fail demo with clear error message
- **VNC port allocation failure**: Try next available port, fail demo if no ports available
- **Resource allocation failure**: Reduce resource request by 25%, retry up to 3 times
- **Partial failures**: Clean up all created resources, provide detailed error report

**Cleanup Strategy:**

- Ensure cleanup is reliable and automatic
- No manual cleanup commands required
- Clean up only per-demo VM instances, preserve base images for reuse

## Dependencies

**Python Libraries:**

- `libvirt` - VM management and control
- `xdg` - XDG base directory handling

**System Dependencies:**

- `virt-builder` - Base image creation
- `qemu` - Virtualization backend
- `libvirt-daemon` - libvirt service

## Future Considerations

- Multi-VM demo scenarios
- Network topology management
- Advanced snapshot management
- Integration with CI/CD pipelines
