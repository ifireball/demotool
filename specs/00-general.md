# General Coding Requirements

## Overview

This specification defines general coding requirements and patterns that apply across all demotool components.

## Configuration

Prefer well-picked or auto-detected optimal values over adding configuration options to the code.

## Integration

When integrating with external tools, use this order of preference:

1. Python bindings provided by the tool or library authors
2. Third-party Python bindings
3. Remote control APIs (TCP, DBUS, REST, etc.) with Python networking code or client-side libraries
4. CLI/shell command execution

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

### Test Strategy

- **Integration-focused testing**: Prefer testing actual functionality over extensive mocking
- **Minimal mocking**: Only mock system-level dependencies that can't be easily tested
- **Real tool integration**: Test actual integration with external tools (libvirt, virt-builder, qemu-img)
- **Performance optimization**: Limit slow operations to one test per major functionality area

### Test Organization

- **Unit test classes**: Fast tests focusing on library logic and error handling
- **Integration test classes**: Slower tests requiring actual system tools and resources
- **Clear separation**: Easy to run fast tests vs. full integration tests
- **Test naming**: Descriptive names that clearly indicate what's being tested

### Test Requirements

- Unit tests for all public methods and edge cases
- Integration tests for actual tool integration (VM lifecycle, image creation)
- Test error conditions and resource cleanup scenarios
- Mock only when necessary (subprocess calls, file system operations)

### Performance Guidelines

- **Fast tests**: Most tests should complete in seconds
- **Slow tests**: Only one test per major functionality should run slow operations
- **Resource management**: Use temporary directories and proper cleanup
- **Test isolation**: Each test should be independent and clean up after itself

### Test Fixtures and Mocking

- **Temporary resources**: Use pytest fixtures for temporary directories and resources
- **Mocking strategy**: Mock subprocess calls, file system operations, and network calls
- **Real tools**: Use actual libvirt, virt-builder, and qemu-img when testing integration
- **Fixture scope**: Use session-scoped fixtures for expensive setup operations

## Performance

### Resource Management

- Efficient resource usage
- Proper cleanup of resources
- Avoid memory leaks
- Use context managers for resource management
- Use `@contextmanager` decorator for simple resource management
- Use class-based context managers for complex resource hierarchies
- Ensure cleanup happens even when exceptions occur

## Dependency Management

- Use the `uv` tool for Python dependency management
- Use `mise` for any non-Python tool dependencies
