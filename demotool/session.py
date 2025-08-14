"""
Demo session management for demotool.
"""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from .exceptions import SessionError
from .logging import get_logger
from .vm import VMManager

logger = get_logger(__name__)


class DemoSession:
    """Manages a demo session and its output directory."""
    
    def __init__(self, name: str):
        """
        Initialize demo session.
        
        Args:
            name: Name of the demo session
        """
        self.name = name
        self._directory: Optional[Path] = None
        self._vm_manager: Optional[VMManager] = None
        self._output_files_created = False
    
    @property
    def directory(self) -> Path:
        """
        Get the demo output directory.
        
        Creates the directory lazily when first accessed.
        
        Returns:
            Path to the demo output directory
        """
        if self._directory is None:
            # Create directory relative to current working directory
            self._directory = Path.cwd() / "demo-videos" / self.name
            logger.debug(f"Demo directory path: {self._directory}")
        
        return self._directory
    
    def _ensure_directory_exists(self) -> None:
        """Create the demo output directory if it doesn't exist."""
        if not self._output_files_created:
            self.directory.mkdir(parents=True, exist_ok=True)
            self._output_files_created = True
            logger.info(f"Created demo output directory: {self.directory}")
    
    def _get_vm_manager(self) -> VMManager:
        """Get or create VM manager instance."""
        if self._vm_manager is None:
            self._vm_manager = VMManager()
        return self._vm_manager
    
    @contextmanager
    def vm(self, image_id: str):
        """
        Create and manage a VM instance within the demo session.
        
        Args:
            image_id: Base image identifier (e.g., 'fedora-42')
            
        Yields:
            VM object when ready
            
        Example:
            with demo.vm("fedora-42") as vm:
                # VM is ready for interaction
                print(f"VNC port: {vm.vnc_port}")
        """
        vm_manager = self._get_vm_manager()
        
        with vm_manager.create_vm(self.name, image_id) as vm_obj:
            # Set the demo session reference
            vm_obj.demo = self
            yield vm_obj
    
    def create_output_file(self, filename: str) -> Path:
        """
        Create an output file in the demo directory.
        
        Args:
            filename: Name of the output file
            
        Returns:
            Path to the created file
            
        Note:
            This method ensures the demo directory exists before creating files.
        """
        self._ensure_directory_exists()
        file_path = self.directory / filename
        logger.debug(f"Created output file: {file_path}")
        return file_path
    
    def cleanup(self) -> None:
        """Clean up demo session resources."""
        if self._vm_manager is not None:
            try:
                del self._vm_manager
                self._vm_manager = None
            except Exception as e:
                logger.warning(f"Failed to cleanup VM manager: {e}")


@contextmanager
def startdemo(name: str):
    """
    Start a demo session.
    
    Args:
        name: Name of the demo session
        
    Yields:
        DemoSession object for managing the demo
        
    Example:
        with demotool.startdemo("my-cool-demo") as demo:
            with demo.vm("fedora-42") as vm:
                # Demo VM is ready for interaction
                pass
    """
    session = DemoSession(name)
    
    try:
        logger.info(f"Started demo session: {name}")
        yield session
    finally:
        session.cleanup()
        logger.info(f"Ended demo session: {name}")


# Convenience function for simple demo workflows
@contextmanager
def recordDemo(name: str, image_id: str):
    """
    Convenience function for simple demo workflows.
    
    Args:
        name: Name of the demo session
        image_id: Base image identifier (e.g., 'fedora-42')
        
    Yields:
        VM object when ready
        
    Example:
        with demotool.recordDemo("demo-name", "fedora-42") as vm:
            # Demo VM is ready for interaction
            pass
    """
    with startdemo(name) as demo:
        with demo.vm(image_id) as vm:
            yield vm
