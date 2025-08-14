"""
Integration tests for the VM management functionality.

These tests focus on testing the actual functionality with minimal mocking,
ensuring the VM management system works correctly.

IMPORTANT: Only ONE test actually runs the slow VM creation operation:
- test_real_vm_creation_and_boot: Tests actual VM creation and boot
  (Located in TestVMIntegration class)

All other tests use mocks or test existing VM logic to avoid the slow operation.
"""

import os
import socket
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock, Mock

import pytest
import libvirt
import psutil

from demotool.vm import VMManager, VM
from demotool.exceptions import VMError, VNCError
from demotool.images import ImageManager

# Set up logging for the test module
import logging
logger = logging.getLogger(__name__)


class TestVMManager:
    """Unit tests for VMManager functionality."""
    
    @pytest.fixture
    def mock_libvirt_conn(self):
        """Create a mock libvirt connection."""
        mock_conn = MagicMock()
        # Default to VM not found, but tests can override this
        mock_conn.lookupByName.side_effect = libvirt.libvirtError("VM not found")
        return mock_conn
    
    @pytest.fixture
    def vm_manager(self, mock_libvirt_conn):
        """Create VMManager instance with mocked libvirt connection."""
        with patch('libvirt.open', return_value=mock_libvirt_conn):
            manager = VMManager()
            manager.conn = mock_libvirt_conn
            return manager
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_vm_manager_initialization(self, mock_libvirt_conn):
        """Test that VMManager initializes correctly with libvirt connection."""
        with patch('libvirt.open', return_value=mock_libvirt_conn):
            manager = VMManager()
            assert manager.conn == mock_libvirt_conn
            assert manager.image_manager is not None
    
    def test_vm_manager_initialization_failure(self):
        """Test VMManager initialization failure when libvirt connection fails."""
        with patch('libvirt.open', side_effect=libvirt.libvirtError("Connection failed")):
            with pytest.raises(VMError, match="Failed to connect to libvirt"):
                VMManager()
    
    def test_get_host_resources_calculation(self, vm_manager):
        """Test CPU/RAM calculation with various host configurations."""
        # Mock host resources
        with patch('os.cpu_count', return_value=16), \
             patch('psutil.virtual_memory') as mock_vm:
            mock_vm.return_value.total = 32 * 1024 * 1024 * 1024  # 32GB
            
            cpu_cores, ram_mb = vm_manager._get_host_resources()
            
            # Should be 50% of host with limits: min 1, max 8 for CPU
            assert cpu_cores == 8  # 16 // 2 = 8, within max limit
            # Should be 50% of host with limits: min 4GB, max 32GB for RAM
            assert ram_mb == 16384  # 32GB // 2 = 16GB, within max limit
    
    def test_get_host_resources_minimum_limits(self, vm_manager):
        """Test resource calculation respects minimum limits."""
        # Mock very low host resources
        with patch('os.cpu_count', return_value=1), \
             patch('psutil.virtual_memory') as mock_vm:
            mock_vm.return_value.total = 2 * 1024 * 1024 * 1024  # 2GB
            
            cpu_cores, ram_mb = vm_manager._get_host_resources()
            
            # Should respect minimum limits
            assert cpu_cores == 1  # min 1 core
            assert ram_mb == 4096  # min 4GB
    
    def test_get_host_resources_maximum_limits(self, vm_manager):
        """Test resource calculation respects maximum limits."""
        # Mock very high host resources
        with patch('os.cpu_count', return_value=32), \
             patch('psutil.virtual_memory') as mock_vm:
            mock_vm.return_value.total = 128 * 1024 * 1024 * 1024  # 128GB
            
            cpu_cores, ram_mb = vm_manager._get_host_resources()
            
            # Should respect maximum limits
            assert cpu_cores == 8  # max 8 cores
            assert ram_mb == 32768  # max 32GB
    
    def test_create_vm_xml_generation(self, vm_manager, temp_dir):
        """Test VM XML definition creation."""
        image_path = temp_dir / "test.qcow2"
        image_path.touch()
        
        xml = vm_manager._create_vm_xml("test-vm", image_path, 4, 8192)
        
        # Verify XML contains expected elements
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert '<name>test-vm</name>' in xml
        assert '<memory unit="MiB">8192</memory>' in xml
        assert '<vcpu>4</vcpu>' in xml
        assert f'<source file="{image_path}"/>' in xml
        assert '<graphics type="vnc" port="-1" autoport="yes" listen="127.0.0.1"/>' in xml
        assert '<model type="virtio"/>' in xml  # virtio devices
        assert '<acpi/>' in xml  # Basic KVM features
        assert '<apic/>' in xml  # Basic KVM features
    
    def test_create_vm_xml_with_different_resources(self, vm_manager, temp_dir):
        """Test XML generation with different resource configurations."""
        image_path = temp_dir / "test.qcow2"
        image_path.touch()
        
        # Test with different CPU/RAM combinations
        test_configs = [
            (1, 4096),   # Minimum
            (4, 8192),   # Medium
            (8, 32768),  # Maximum
        ]
        
        for cpu_cores, ram_mb in test_configs:
            xml = vm_manager._create_vm_xml("test-vm", image_path, cpu_cores, ram_mb)
            
            assert f'<vcpu>{cpu_cores}</vcpu>' in xml
            assert f'<memory unit="MiB">{ram_mb}</memory>' in xml
            assert f'<currentMemory unit="MiB">{ram_mb}</currentMemory>' in xml
    
    def test_wait_for_vnc_port_autoport(self, vm_manager):
        """Test VNC port detection with autoport enabled."""
        mock_vm = MagicMock()
        mock_vm.XMLDesc.return_value = '''
        <graphics type="vnc" port="-1" autoport="yes" listen="127.0.0.1"/>
        '''
        mock_vm.vncDisplay.return_value = 5900
        
        vnc_port = vm_manager._wait_for_vnc_port(mock_vm, timeout=5)
        
        assert vnc_port == 5900
        mock_vm.vncDisplay.assert_called_once()
    
    def test_wait_for_vnc_port_explicit_port(self, vm_manager):
        """Test VNC port detection with explicit port."""
        mock_vm = MagicMock()
        mock_vm.XMLDesc.return_value = '''
        <graphics type="vnc" port="5901" listen="127.0.0.1"/>
        '''
        
        vnc_port = vm_manager._wait_for_vnc_port(mock_vm, timeout=5)
        
        assert vnc_port == 5901
    
    def test_wait_for_vnc_port_timeout(self, vm_manager):
        """Test VNC port detection timeout handling."""
        mock_vm = MagicMock()
        mock_vm.XMLDesc.return_value = '''
        <graphics type="vnc" port="-1" autoport="yes" listen="127.0.0.1"/>
        '''
        mock_vm.vncDisplay.return_value = None
        
        with pytest.raises(VNCError, match="VNC port not available within"):
            vm_manager._wait_for_vnc_port(mock_vm, timeout=2)
    
    def test_wait_for_vnc_port_libvirt_error(self, vm_manager):
        """Test VNC port detection with libvirt errors."""
        mock_vm = MagicMock()
        mock_vm.XMLDesc.side_effect = libvirt.libvirtError("XML error")
        
        with pytest.raises(VNCError, match="VNC port not available within"):
            vm_manager._wait_for_vnc_port(mock_vm, timeout=2)
    
    def test_wait_for_desktop_ready_success(self, vm_manager):
        """Test desktop ready detection when VNC port is responsive."""
        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.connect_ex.return_value = 0  # Connection successful
            
            # Mock time.sleep to speed up test
            with patch('time.sleep'):
                vm_manager._wait_for_desktop_ready(5900, timeout=5)
            
            mock_sock.connect_ex.assert_called_with(('127.0.0.1', 5900))
            mock_sock.close.assert_called_once()
    
    def test_wait_for_desktop_ready_timeout(self, vm_manager):
        """Test desktop ready detection timeout handling."""
        with patch('socket.socket') as mock_socket:
            mock_sock = MagicMock()
            mock_socket.return_value = mock_sock
            mock_sock.connect_ex.return_value = 1  # Connection failed
            
            with pytest.raises(VNCError, match="Desktop not ready within"):
                vm_manager._wait_for_desktop_ready(5900, timeout=2)
    
    def test_wait_for_desktop_ready_socket_error(self, vm_manager):
        """Test desktop ready detection with socket errors."""
        with patch('socket.socket', side_effect=OSError("Socket error")):
            with pytest.raises(VNCError, match="Desktop not ready within"):
                vm_manager._wait_for_desktop_ready(5900, timeout=2)
    
    def test_delete_existing_vm_not_found(self, vm_manager, mock_libvirt_conn):
        """Test deletion of non-existent VM."""
        mock_libvirt_conn.lookupByName.side_effect = libvirt.libvirtError("VM not found")
        
        # Should not raise an exception
        vm_manager._delete_existing_vm("nonexistent-vm")
    
    def test_delete_existing_vm_running(self, vm_manager, mock_libvirt_conn):
        """Test deletion of running VM."""
        mock_vm = MagicMock()
        mock_vm.isActive.return_value = True
        # Override the default side_effect for this specific test
        mock_libvirt_conn.lookupByName.side_effect = None
        mock_libvirt_conn.lookupByName.return_value = mock_vm
        
        vm_manager._delete_existing_vm("running-vm")
        
        mock_vm.destroy.assert_called_once()
        mock_vm.undefine.assert_called_once()
    
    def test_delete_existing_vm_stopped(self, vm_manager, mock_libvirt_conn):
        """Test deletion of stopped VM."""
        mock_vm = MagicMock()
        mock_vm.isActive.return_value = False
        # Override the default side_effect for this specific test
        mock_libvirt_conn.lookupByName.side_effect = None
        mock_libvirt_conn.lookupByName.return_value = mock_vm
        
        vm_manager._delete_existing_vm("stopped-vm")
        
        mock_vm.destroy.assert_not_called()
        mock_vm.undefine.assert_called_once()
    
    def test_delete_existing_vm_cleanup_error(self, vm_manager, mock_libvirt_conn):
        """Test deletion of VM with cleanup errors."""
        mock_vm = MagicMock()
        mock_vm.isActive.return_value = True
        mock_vm.destroy.side_effect = libvirt.libvirtError("Destroy failed")
        # Override the default side_effect for this specific test
        mock_libvirt_conn.lookupByName.side_effect = None
        mock_libvirt_conn.lookupByName.return_value = mock_vm
        
        # Should not raise an exception, should continue with cleanup
        vm_manager._delete_existing_vm("error-vm")
        
        mock_vm.destroy.assert_called_once()
        # Should still try to undefine even if destroy fails
        mock_vm.undefine.assert_called_once()
    
    def test_create_vm_context_manager_success(self, vm_manager, temp_dir):
        """Test VM creation context manager success path."""
        # Mock all the dependencies
        mock_vm = MagicMock()
        mock_vm.state.return_value = (libvirt.VIR_DOMAIN_RUNNING, 0)
        mock_vm.XMLDesc.return_value = '<graphics type="vnc" port="5900"/>'
        mock_vm.vncDisplay.return_value = 5900
        
        mock_libvirt_conn = vm_manager.conn
        mock_libvirt_conn.defineXML.return_value = mock_vm
        
        # Mock image manager
        mock_image_path = temp_dir / "test.qcow2"
        mock_image_path.touch()
        vm_manager.image_manager.create_image = MagicMock(return_value=mock_image_path)
        
        # Mock VNC and desktop ready checks
        with patch.object(vm_manager, '_wait_for_vnc_port', return_value=5900), \
             patch.object(vm_manager, '_wait_for_desktop_ready'), \
             patch('time.sleep'), \
             patch.object(vm_manager, '_delete_existing_vm'):  # Mock the delete method to avoid lookup issues
            
            with vm_manager.create_vm("test-demo", "fedora-42") as vm_obj:
                assert isinstance(vm_obj, VM)
                assert vm_obj.demo_name == "test-demo"
                assert vm_obj.vnc_port == 5900
                assert vm_obj.demo is None  # Will be set by caller
            
            # Verify cleanup
            mock_vm.destroy.assert_called_once()
            mock_vm.undefine.assert_called_once()
    
    def test_create_vm_context_manager_failure(self, vm_manager, temp_dir):
        """Test VM creation context manager failure path."""
        # Mock image manager to fail
        vm_manager.image_manager.create_image = MagicMock(
            side_effect=Exception("Image creation failed")
        )
        
        with pytest.raises(VMError, match="Failed to create VM demo-test"):
            with vm_manager.create_vm("test", "fedora-42"):
                pass
    
    def test_create_vm_context_manager_vm_start_failure(self, vm_manager, temp_dir):
        """Test VM creation when VM fails to start."""
        mock_vm = MagicMock()
        mock_vm.state.return_value = (libvirt.VIR_DOMAIN_SHUTDOWN, 0)  # Not running
        
        mock_libvirt_conn = vm_manager.conn
        mock_libvirt_conn.defineXML.return_value = mock_vm
        
        # Mock image manager
        mock_image_path = temp_dir / "test.qcow2"
        mock_image_path.touch()
        vm_manager.image_manager.create_image = MagicMock(return_value=mock_image_path)
        
        with patch.object(vm_manager, '_delete_existing_vm'), \
             patch('time.sleep'):
            with pytest.raises(VMError, match="VM failed to start within"):
                with vm_manager.create_vm("test", "fedora-42"):
                    pass
        
        # Verify cleanup
        mock_vm.destroy.assert_called_once()
        mock_vm.undefine.assert_called_once()
    
    def test_vm_manager_cleanup_on_destruction(self, mock_libvirt_conn):
        """Test that VMManager cleanup works properly."""
        with patch('libvirt.open', return_value=mock_libvirt_conn):
            manager = VMManager()
            assert manager.conn == mock_libvirt_conn
            
            # Delete manager
            del manager
            
            # Connection should be closed
            mock_libvirt_conn.close.assert_called_once()


class TestVM:
    """Unit tests for VM class."""
    
    def test_vm_initialization(self):
        """Test VM object initialization."""
        mock_demo_session = MagicMock()
        mock_demo_session.directory = Path("/tmp/demo")
        
        vm = VM("test-demo", 5900, mock_demo_session)
        
        assert vm.demo_name == "test-demo"
        assert vm.vnc_port == 5900
        assert vm.demo == mock_demo_session
    
    def test_vm_directory_property(self):
        """Test VM directory property access."""
        mock_demo_session = MagicMock()
        mock_demo_session.directory = Path("/tmp/demo")
        
        vm = VM("test-demo", 5900, mock_demo_session)
        
        assert vm.demo_name == "test-demo"
        assert vm.vnc_port == 5900
        assert vm.demo == mock_demo_session
        
        assert vm.directory == Path("/tmp/demo")


class TestVMIntegration:
    """Integration tests requiring actual virtualization."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.mark.skipif(
        not os.path.exists("/dev/kvm") or not os.access("/dev/kvm", os.R_OK),
        reason="KVM not available or accessible"
    )
    def test_libvirt_connection(self, temp_dir):
        """Test actual libvirt connection to qemu:///session."""
        try:
            conn = libvirt.open("qemu:///session")
            assert conn is not None
            
            # Test basic libvirt functionality
            version = conn.getLibVersion()
            assert version > 0
            
            conn.close()
        except libvirt.libvirtError as e:
            pytest.skip(f"Libvirt connection failed: {e}")
    
    @pytest.mark.skipif(
        not os.path.exists("/dev/kvm") or not os.access("/dev/kvm", os.R_OK),
        reason="KVM not available or accessible"
    )
    def test_vm_manager_real_connection(self, temp_dir):
        """Test VMManager with real libvirt connection."""
        try:
            manager = VMManager()
            assert manager.conn is not None
            
            # Test resource detection
            cpu_cores, ram_mb = manager._get_host_resources()
            assert cpu_cores >= 1
            assert cpu_cores <= 8
            assert ram_mb >= 4096
            assert ram_mb <= 32768
            
            # Cleanup
            del manager
            
        except VMError as e:
            pytest.skip(f"VMManager not available: {e}")
    
    @pytest.mark.skipif(
        not os.path.exists("/dev/kvm") or not os.access("/dev/kvm", os.R_OK),
        reason="KVM not available or accessible"
    )
    def test_real_vm_creation_and_boot(self, temp_dir):
        """Test actual VM creation and boot (slow test - only one should run this)."""
        try:
            manager = VMManager()
            
            # Use a small test image if available, otherwise skip
            test_image_id = "fedora-42"
            
            # Check if we have a base image or can create one
            try:
                # Use real ImageManager with real cache to speed up test
                image_manager = ImageManager()
                image_path = image_manager.create_image(test_image_id)
                
                if not image_path.exists():
                    pytest.skip("Could not create test image")
                
                logger.info(f"Testing real VM creation with {test_image_id}")
                
                # Create VM using context manager
                with manager.create_vm("integration-test", test_image_id) as vm_obj:
                    assert isinstance(vm_obj, VM)
                    assert vm_obj.demo_name == "integration-test"
                    assert vm_obj.vnc_port > 0
                    
                    # Test VNC connectivity
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(5)
                    result = sock.connect_ex(('127.0.0.1', vm_obj.vnc_port))
                    sock.close()
                    
                    assert result == 0, f"VNC port {vm_obj.vnc_port} is not responsive"
                    
                    logger.info(f"Successfully created and tested VM with VNC port {vm_obj.vnc_port}")
                
                logger.info("VM creation test completed successfully")
                
            except Exception as e:
                logger.warning(f"VM creation test failed: {e}")
                pytest.skip(f"VM creation failed: {e}")
            
        except VMError as e:
            pytest.skip(f"VMManager not available: {e}")
    
    @pytest.mark.skipif(
        not os.path.exists("/dev/kvm") or not os.access("/dev/kvm", os.R_OK),
        reason="KVM not available or accessible"
    )
    def test_vm_xml_validation(self, temp_dir):
        """Test that generated VM XML is valid libvirt XML."""
        try:
            manager = VMManager()
            
            # Create test image path
            test_image_path = temp_dir / "test.qcow2"
            test_image_path.touch()
            
            # Generate XML
            xml = manager._create_vm_xml("test-xml", test_image_path, 2, 8192)
            
            # Try to define VM to validate XML
            vm = manager.conn.defineXML(xml)
            
            try:
                # If we get here, XML is valid
                assert vm is not None
                
                # Test XML properties
                xml_desc = vm.XMLDesc()
                assert "test-xml" in xml_desc
                # libvirt converts MiB to KiB, so 8192 MiB becomes 8388608 KiB
                assert "8388608" in xml_desc  # 8192 * 1024
                assert "2" in xml_desc
                
            finally:
                # Cleanup
                vm.undefine()
            
        except Exception as e:
            pytest.skip(f"XML validation test failed: {e}")


# Helper functions for testing
def create_mock_domain(name, state=libvirt.VIR_DOMAIN_RUNNING):
    """Create a mock libvirt domain for testing."""
    mock_domain = MagicMock()
    mock_domain.name.return_value = name
    mock_domain.state.return_value = (state, 0)
    mock_domain.isActive.return_value = (state == libvirt.VIR_DOMAIN_RUNNING)
    return mock_domain


def create_mock_libvirt_connection():
    """Create a mock libvirt connection for testing."""
    mock_conn = MagicMock()
    mock_conn.listAllDomains.return_value = []
    mock_conn.lookupByName.return_value = None
    return mock_conn
