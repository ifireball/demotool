"""
VM lifecycle management for demotool.
"""

import os
import socket
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional, Tuple

import libvirt
import psutil

from .exceptions import VMError, VNCError
from .images import ImageManager
from .logging import get_logger

logger = get_logger(__name__)


class VM:
    """Represents a VM instance for demotool."""
    
    def __init__(self, demo_name: str, vnc_port: int, demo_session):
        """
        Initialize VM instance.
        
        Args:
            demo_name: Name of the demo session
            vnc_port: VNC port for the VM
            demo_session: Reference to the demo session
        """
        self.demo_name = demo_name
        self.vnc_port = vnc_port
        self.demo = demo_session
    
    @property
    def directory(self) -> Path:
        """Get the demo output directory."""
        return self.demo.directory


class VMManager:
    """Manages VM lifecycle and operations."""
    
    def __init__(self) -> None:
        """Initialize the VM manager."""
        self.image_manager = ImageManager()
        self.conn: Optional[libvirt.virConnect] = None
        self._connect()
    
    def _connect(self) -> None:
        """Connect to libvirt."""
        try:
            self.conn = libvirt.open("qemu:///session")
            logger.debug("Connected to libvirt qemu:///session")
        except libvirt.libvirtError as e:
            logger.error(f"Failed to connect to libvirt: {e}")
            raise VMError(f"Failed to connect to libvirt: {e}")
    
    def _get_host_resources(self) -> Tuple[int, int]:
        """
        Get host system resources.
        
        Returns:
            Tuple of (cpu_cores, ram_mb)
        """
        cpu_cores = os.cpu_count() or 1
        ram_bytes = psutil.virtual_memory().total
        ram_mb = ram_bytes // (1024 * 1024)
        
        # Calculate 50% of host resources with limits
        vm_cpu = max(1, min(8, cpu_cores // 2))
        vm_ram = max(4096, min(32768, ram_mb // 2))
        
        logger.debug(f"Host: {cpu_cores} cores, {ram_mb}MB RAM")
        logger.debug(f"VM allocation: {vm_cpu} cores, {vm_ram}MB RAM")
        
        return vm_cpu, vm_ram
    
    def _create_vm_xml(self, name: str, image_path: Path, cpu_cores: int, ram_mb: int) -> str:
        """
        Generate libvirt XML for VM creation.
        
        Args:
            name: VM name
            image_path: Path to base image
            cpu_cores: Number of CPU cores
            ram_mb: RAM in MB
            
        Returns:
            XML string for VM definition
        """
        xml_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<domain type="kvm">
  <name>{name}</name>
  <memory unit="MiB">{ram_mb}</memory>
  <currentMemory unit="MiB">{ram_mb}</currentMemory>
  <vcpu>{cpu_cores}</vcpu>
  <os>
    <type arch="x86_64" machine="q35">hvm</type>
    <boot dev="hd"/>
  </os>
  <features>
    <acpi/>
    <apic/>
  </features>
  <devices>
    <disk type="file" device="disk">
      <driver name="qemu" type="qcow2"/>
      <source file="{image_path}"/>
      <target dev="vda" bus="virtio"/>
    </disk>
    <interface type="user">
      <model type="virtio"/>
    </interface>
    <graphics type="vnc" port="-1" autoport="yes" listen="127.0.0.1"/>
    <console type="pty"/>
    <input type="tablet" bus="usb"/>
    <input type="keyboard" bus="usb"/>
  </devices>
</domain>"""
        
        return xml_template
    
    def _wait_for_vnc_port(self, vm: libvirt.virDomain, timeout: int = 120) -> int:
        """
        Wait for VNC port to become available.
        
        Args:
            vm: libvirt domain object
            timeout: Timeout in seconds
            
        Returns:
            VNC port number
            
        Raises:
            VNCError: If VNC port doesn't become available within timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Get VNC port from libvirt
                xml_desc = vm.XMLDesc()
                if 'graphics type="vnc"' in xml_desc:
                    # Extract port from XML - handle multi-line format
                    for line in xml_desc.split('\n'):
                        if 'graphics type="vnc"' in line:
                            # Check if this line has port information
                            if 'port=' in line:
                                if 'autoport="yes"' in line:
                                    # Port is auto-allocated, need to get it from libvirt
                                    port = vm.vncDisplay()
                                    if port is not None:
                                        logger.info(f"VNC port allocated: {port}")
                                        return port
                                else:
                                    # Port is explicitly set
                                    import re
                                    match = re.search(r'port="(\d+)"', line)
                                    if match:
                                        port = int(match.group(1))
                                        logger.info(f"VNC port: {port}")
                                        return port
                            else:
                                # This line has graphics type but no port, check for autoport
                                if 'autoport="yes"' in line:
                                    # Port is auto-allocated, need to get it from libvirt
                                    port = vm.vncDisplay()
                                    if port is not None:
                                        logger.info(f"VNC port allocated: {port}")
                                        return port
                
                time.sleep(1)
                
            except libvirt.libvirtError as e:
                logger.debug(f"Waiting for VNC port: {e}")
                time.sleep(1)
        
        raise VNCError(f"VNC port not available within {timeout} seconds")
    
    def _wait_for_desktop_ready(self, vnc_port: int, timeout: int = 120) -> None:
        """
        Wait for desktop to be ready by checking VNC connectivity.
        
        Args:
            vnc_port: VNC port number
            timeout: Timeout in seconds
            
        Raises:
            VNCError: If desktop doesn't become ready within timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to connect to VNC port
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex(('127.0.0.1', vnc_port))
                sock.close()
                
                if result == 0:
                    logger.info(f"VNC port {vnc_port} is responsive")
                    # Add 10-second delay to allow desktop to fully load
                    logger.info("Waiting 10 seconds for desktop to fully load...")
                    time.sleep(10)
                    return
                
            except Exception as e:
                logger.debug(f"VNC check failed: {e}")
            
            time.sleep(2)
        
        raise VNCError(f"Desktop not ready within {timeout} seconds")
    
    def _delete_existing_vm(self, name: str) -> None:
        """
        Delete existing VM if it exists.
        
        Args:
            name: VM name to delete
        """
        try:
            existing_vm = self.conn.lookupByName(name)
            logger.info(f"Deleting existing VM: {name}")
            
            # Try to destroy if running, but continue even if it fails
            if existing_vm.isActive():
                try:
                    existing_vm.destroy()
                except libvirt.libvirtError as e:
                    logger.warning(f"Failed to destroy VM {name}: {e}")
                    # Continue with undefine even if destroy fails
            
            # Always try to undefine
            existing_vm.undefine()
            logger.info(f"Successfully deleted VM: {name}")
            
        except libvirt.libvirtError:
            # VM doesn't exist, which is fine
            pass
    
    @contextmanager
    def create_vm(self, demo_name: str, image_id: str):
        """
        Create and manage a VM instance.
        
        Args:
            demo_name: Name of the demo session
            image_id: Base image identifier (e.g., 'fedora-42')
            
        Yields:
            VM object when ready
            
        Raises:
            VMError: If VM creation fails
        """
        vm_name = f"demo-{demo_name}"
        vm: Optional[libvirt.virDomain] = None
        
        try:
            # Delete existing VM if found
            self._delete_existing_vm(vm_name)
            
            # Get or create base image
            image_path = self.image_manager.create_image(image_id)
            
            # Get host resources
            cpu_cores, ram_mb = self._get_host_resources()
            
            # Create VM XML
            xml = self._create_vm_xml(vm_name, image_path, cpu_cores, ram_mb)
            
            # Create and start VM
            logger.info(f"Creating VM: {vm_name}")
            vm = self.conn.defineXML(xml)
            
            logger.info(f"Starting VM: {vm_name}")
            vm.create()
            
            # Wait for VM to be running
            start_time = time.time()
            timeout = int(os.environ.get("DEMOTOOL_BOOT_TIMEOUT", "120"))
            
            while time.time() - start_time < timeout:
                if vm.state()[0] == libvirt.VIR_DOMAIN_RUNNING:
                    break
                time.sleep(1)
            else:
                raise VMError(f"VM failed to start within {timeout} seconds")
            
            logger.info(f"VM {vm_name} is running")
            
            # Wait for VNC port
            vnc_port = self._wait_for_vnc_port(vm, timeout)
            
            # Wait for desktop to be ready
            self._wait_for_desktop_ready(vnc_port, timeout)
            
            logger.info(f"VM {vm_name} is ready")
            
            # Create VM object and yield it
            vm_obj = VM(demo_name, vnc_port, None)  # demo_session will be set by caller
            yield vm_obj
            
        except Exception as e:
            logger.error(f"Failed to create VM {vm_name}: {e}")
            raise VMError(f"Failed to create VM {vm_name}: {e}")
        
        finally:
            # Clean up VM
            if vm is not None:
                try:
                    logger.info(f"Cleaning up VM: {vm_name}")
                    if vm.isActive():
                        vm.destroy()
                    vm.undefine()
                    logger.info(f"Successfully cleaned up VM: {vm_name}")
                except libvirt.libvirtError as e:
                    logger.error(f"Failed to clean up VM {vm_name}: {e}")
    
    def __del__(self) -> None:
        """Cleanup when VM manager is destroyed."""
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
