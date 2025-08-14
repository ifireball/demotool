# Demotool

Automated demo creation using virtual machines.

Demotool provides a Python-based framework for orchestrating VM lifecycle management, automated interactions, and demo generation workflows. It's designed to make it easy to create reproducible demos with consistent environments.

## Features

- **Automated VM Management**: Create and manage VMs from base images using libvirt
- **Base Image Caching**: Efficient image management with XDG cache directory
- **Demo Session Management**: Organized output directories for each demo
- **Resource Optimization**: Automatic resource allocation (50% of host resources)
- **Desktop Ready Detection**: Smart waiting for VM desktop to be fully loaded
- **Clean Resource Management**: Automatic cleanup of VMs and temporary resources

## Quick Start

### Installation

1. **System Dependencies**:

   ```bash
   # Fedora/RHEL
   sudo dnf install libvirt-daemon qemu virt-builder
   
   # Ubuntu/Debian
   sudo apt install libvirt-daemon-system qemu-kvm virt-builder
   ```

2. **Python Dependencies**:

   ```bash
   # Using uv (recommended)
   uv sync
   
   # Or using pip
   pip install -e .
   ```

### Basic Usage

```python
import demotool

# Simple demo workflow
with demotool.recordDemo("my-demo", "fedora", "42") as vm:
    print(f"VM is ready! VNC port: {vm.vnc_port}")
    # Your demo code here
```

### Advanced Usage

```python
import demotool

with demotool.startdemo("complex-demo") as demo:
    with demo.vm("fedora", "42") as vm:
        # Setup phase
        setup_file = demo.create_output_file("setup.txt")
        
        # Demo sections
        with vm.record("section1"):
            # Interaction details defined elsewhere
            pass
        
        with vm.record("section2"):
            # More interactions
            pass
```

## Command Line Interface

```bash
# Start a demo session
demotool start my-demo fedora 42

# Quick demo recording
demotool record quick-demo fedora 42

# List available base images
demotool images list

# Clean up corrupted images
demotool images cleanup
```

## Architecture

### Core Components

1. **Demo Session Manager** (`demotool.startdemo`)
   - Manages demo output directories
   - Coordinates VM lifecycle
   - Handles session cleanup

2. **VM Lifecycle Manager** (`demo.vm`)
   - VM creation from base images
   - Resource allocation and management
   - VNC port detection and configuration
   - Desktop ready state detection

3. **Image Manager** (`demotool.images`)
   - Base image creation using virt-builder
   - XDG cache directory management
   - Image validation and corruption handling

### Demo Directory Structure

```
demo-videos/
└── {demo-name}/
    ├── setup.txt
    ├── main-demo.txt
    └── cleanup.txt
```

### VM Resource Allocation

- **CPU**: 50% of host cores (minimum 1, maximum 8)
- **RAM**: 50% of host RAM (minimum 4GB, maximum 32GB)
- **Disk**: COW layer on base image
- **Network**: libvirt usermode networking

## Configuration

### Environment Variables

- `DEMOTOOL_LOG_LEVEL`: Log level (default: INFO)
- `DEMOTOOL_BOOT_TIMEOUT`: VM boot timeout in seconds (default: 120)

### Logging

All log messages include source file name and line number:

```
INFO: vm_manager.py:45: VM is ready
ERROR: image_manager.py:23: Failed to create image
```

## Examples

See the `examples/` directory for complete working examples:

- `basic_demo.py`: Simple demo workflow
- `quick_demo.py`: Using the convenience function
- `multi_section_demo.py`: Multi-phase demo with sections

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/ifireball/demotool.git
cd demotool

# Install development dependencies
uv sync --extra dev

# Run tests
pytest

# Format code
black demotool/ tests/
isort demotool/ tests/
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=demotool

# Run specific test file
pytest tests/test_vm.py
```

## Requirements

- Python 3.11+
- libvirt with qemu backend
- virt-builder for base image creation
- KVM virtualization support

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request
