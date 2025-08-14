# General Coding Requirements

## Overview

This specification defines general coding requirements and patterns that apply across all demotool components.

## Configuration

Prefere well-picked or auto-detected optimal values to adding configuration options to the code.

## Integration

When integrating with external tools, this is the ordere of preference for integration options:

1. Python bindings provided by the tool or library authors
2. 3rd party Python pindings
3. Remote control APIs (TCP, DBUS, REST, etc.), with Python networking code on the client side or
   cliend-side libraries with Python bindinds.
4. Calling over CLI/shell.

## Error Handling

### Logging Requirements

- Use Python's standard `logging` package
- All log messages must include source file name and line number
- Format: `{level}: {filename}:{lineno}: {message}`
- Example: `ERROR: vm_manager.py:45: Failed to create VM: libvirt error`
- Output to stderr by default
- Support structured logging with context information
- Configurable log levels via environment variable `DEMOTOOL_LOG_LEVEL` (default: INFO)

### Error Handling Patterns

- Log all errors with appropriate log levels (ERROR, WARNING, INFO, DEBUG)
- Include context information in error messages
- Fail fast with clear error messages
- Clean up resources on errors
- Provide actionable error information for debugging
- Use custom exception classes for demotool-specific errors
- Catch and handle external library exceptions (libvirt, virt-builder)
- Let unexpected exceptions propagate with full stack trace

## Code Organization

### File Structure

- One class per file
- Clear separation of concerns
- Consistent naming conventions
- Proper import organization

### Documentation

- Docstrings for all public methods
- Type hints where appropriate
- Clear parameter and return value documentation
- Examples in docstrings for complex operations

## Testing

### Test Requirements

- Unit tests for all public methods
- Integration tests for VM lifecycle
- Mock external dependencies (libvirt, virt-builder)
- Test error conditions and edge cases
- Ensure cleanup happens in all scenarios

## Performance

### Resource Management

- Efficient resource usage
- Proper cleanup of resources
- Avoid memory leaks
- Use context managers for resource management
- Use `@contextmanager` decorator for simple resource management
- Use class-based context managers for complex resource hierarchies
- Ensure cleanup happens even when exceptions occur

## Dependency management

- Use the `uv` tool for Python dependency management
- Use `mise` for any non-Python tool dependencies
