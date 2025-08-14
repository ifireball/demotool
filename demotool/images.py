"""
Base image management for demotool.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import xdg

from .exceptions import ImageError
from .logging import get_logger

logger = get_logger(__name__)


class ImageManager:
    """Manages base VM images for demotool."""
    
    def __init__(self) -> None:
        """Initialize the image manager."""
        self.cache_dir = Path(xdg.xdg_cache_home()) / "demotool" / "images"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Image cache directory: {self.cache_dir}")
    
    def get_image_path(self, image_id: str) -> Path:
        """
        Get the path to a base image.
        
        Args:
            image_id: Base image identifier (e.g., 'fedora-42')
            
        Returns:
            Path to the base image file
        """
        return self.cache_dir / f"{image_id}.qcow2"
    
    def image_exists(self, image_id: str) -> bool:
        """
        Check if a base image exists.
        
        Args:
            image_id: Base image identifier
            
        Returns:
            True if image exists and is valid, False otherwise
        """
        image_path = self.get_image_path(image_id)
        
        if not image_path.exists():
            return False
        
        # Check if file is readable
        if not os.access(image_path, os.R_OK):
            logger.warning(f"Image file not readable: {image_path}")
            return False
        
        # Validate qcow2 format
        try:
            result = subprocess.run(
                ["qemu-img", "info", str(image_path)],
                capture_output=True,
                text=True,
                check=True
            )
            return "file format: qcow2" in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning(f"Failed to validate qcow2 format: {image_path}")
            return False
    
    def create_image(self, image_id: str) -> Path:
        """
        Create a base image using virt-builder.
        
        Args:
            image_id: Base image identifier
            
        Returns:
            Path to the created image
            
        Raises:
            ImageError: If image creation fails
        """
        image_path = self.get_image_path(image_id)
        
        # Check if image already exists and is valid
        if self.image_exists(image_id):
            logger.info(f"Using existing image: {image_path}")
            return image_path
        
        # Delete corrupted image if it exists
        if image_path.exists():
            logger.warning(f"Deleting corrupted image: {image_path}")
            image_path.unlink()
        
        logger.info(f"Creating base image: {image_id}")
        
        try:
            # Create temporary file for virt-builder output
            with tempfile.NamedTemporaryFile(suffix=".qcow2", delete=False) as tmp_file:
                tmp_path = Path(tmp_file.name)
            
            # Build image using virt-builder
            cmd = [
                "virt-builder",
                image_id,
                "--output", str(tmp_path),
                "--format", "qcow2",
                "--install", "@workstation-product-environment",
                "--firstboot-command", self._get_firstboot_commands(),
                "--size", "100G",
                "--root-password", "password:demokudasaidomo",
                "--run-command", "systemctl enable gdm",
                "--run-command", "systemctl set-default graphical.target"
            ]
            
            logger.debug(f"Running virt-builder command: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Move temporary file to final location
            tmp_path.rename(image_path)
            
            logger.info(f"Successfully created image: {image_path}")
            return image_path
            
        except subprocess.CalledProcessError as e:
            logger.error(f"virt-builder failed: {e}")
            logger.error(f"stdout: {e.stdout}")
            logger.error(f"stderr: {e.stderr}")
            
            # Clean up temporary file
            if 'tmp_path' in locals() and tmp_path.exists():
                tmp_path.unlink()
            
            raise ImageError(f"Failed to create image {image_id}: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error creating image: {e}")
            
            # Clean up temporary file
            if 'tmp_path' in locals() and tmp_path.exists():
                tmp_path.unlink()
            
            raise ImageError(f"Failed to create image {image_id}: {e}")
    
    def _get_firstboot_commands(self) -> str:
        """
        Get the firstboot commands for setting up the demo user.
        
        Returns:
            Semicolon-separated command string
        """
        commands = [
            # Create demo user
            "useradd -m -s /bin/bash demo",
            # Set password
            "echo 'demo:demokudasaidomo' | chpasswd",
            # Add to wheel group for sudo
            "usermod -a -G wheel demo",
            # Set up auto-login for demo user
            "mkdir -p /etc/gdm/custom.conf.d",
            "echo '[daemon]' > /etc/gdm/custom.conf.d/autologin.conf",
            "echo 'AutomaticLogin=demo' >> /etc/gdm/custom.conf.d/autologin.conf",
            "echo 'AutomaticLoginEnable=true' >> /etc/gdm/custom.conf.d/autologin.conf"
        ]
        
        return "; ".join(commands)
    
    def cleanup_corrupted_images(self) -> None:
        """Remove any corrupted images from the cache."""
        for image_file in self.cache_dir.glob("*.qcow2"):
            if not self._is_valid_qcow2(image_file):
                logger.warning(f"Removing corrupted image: {image_file}")
                try:
                    image_file.unlink()
                except OSError as e:
                    logger.error(f"Failed to remove corrupted image {image_file}: {e}")
    
    def _is_valid_qcow2(self, image_path: Path) -> bool:
        """
        Check if a file is a valid qcow2 image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            True if valid qcow2, False otherwise
        """
        try:
            result = subprocess.run(
                ["qemu-img", "info", str(image_path)],
                capture_output=True,
                text=True,
                check=True
            )
            return "file format: qcow2" in result.stdout
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False
