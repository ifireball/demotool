"""
Command-line interface for demotool.
"""

import argparse
import sys
from pathlib import Path

from .logging import setup_logging
from .session import startdemo, recordDemo


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Automated demo creation using virtual machines",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start a demo session with a VM
  demotool start my-demo fedora 42
  
  # Quick demo recording
  demotool record quick-demo fedora 42
  
  # List available images
  demotool images list
  
  # Clean up corrupted images
  demotool images cleanup
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start a demo session")
    start_parser.add_argument("name", help="Demo session name")
    start_parser.add_argument("distro", help="Distribution name (e.g., fedora)")
    start_parser.add_argument("version", help="Distribution version (e.g., 42)")
    start_parser.add_argument("--timeout", type=int, default=120,
                             help="Boot timeout in seconds (default: 120)")
    
    # Record command
    record_parser = subparsers.add_parser("record", help="Quick demo recording")
    record_parser.add_argument("name", help="Demo session name")
    record_parser.add_argument("distro", help="Distribution name (e.g., fedora)")
    record_parser.add_argument("version", help="Distribution version (e.g., 42)")
    record_parser.add_argument("--timeout", type=int, default=120,
                              help="Boot timeout in seconds (default: 120)")
    
    # Images command
    images_parser = subparsers.add_parser("images", help="Manage base images")
    images_subparsers = images_parser.add_subparsers(dest="images_command", help="Image commands")
    
    images_list_parser = images_subparsers.add_parser("list", help="List available images")
    images_cleanup_parser = images_subparsers.add_parser("cleanup", help="Clean up corrupted images")
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Set up logging
    setup_logging()
    
    try:
        if args.command == "start":
            return _handle_start(args)
        elif args.command == "record":
            return _handle_record(args)
        elif args.command == "images":
            return _handle_images(args)
        else:
            parser.print_help()
            return 1
            
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _handle_start(args) -> int:
    """Handle the start command."""
    print(f"Starting demo session: {args.name}")
    print(f"Distribution: {args.distro} {args.version}")
    
    if args.timeout != 120:
        print(f"Boot timeout: {args.timeout} seconds")
    
    try:
        with startdemo(args.name) as demo:
            print(f"Demo directory: {demo.directory}")
            
            with demo.vm(args.distro, args.version) as vm:
                print(f"VM is ready!")
                print(f"VNC port: {vm.vnc_port}")
                print(f"Demo directory: {vm.directory}")
                print("\nPress Ctrl+C to stop the demo...")
                
                # Keep the demo running until interrupted
                try:
                    while True:
                        import time
                        time.sleep(1)
                except KeyboardInterrupt:
                    print("\nStopping demo...")
        
        print("Demo session completed successfully")
        return 0
        
    except Exception as e:
        print(f"Failed to start demo: {e}", file=sys.stderr)
        return 1


def _handle_record(args) -> int:
    """Handle the record command."""
    print(f"Starting quick demo recording: {args.name}")
    print(f"Distribution: {args.distro} {args.version}")
    
    if args.timeout != 120:
        print(f"Boot timeout: {args.timeout} seconds")
    
    try:
        with recordDemo(args.name, args.distro, args.version) as vm:
            print(f"VM is ready!")
            print(f"VNC port: {vm.vnc_port}")
            print(f"Demo directory: {vm.directory}")
            print("\nPress Ctrl+C to stop the demo...")
            
            # Keep the demo running until interrupted
            try:
                while True:
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping demo...")
        
        print("Demo recording completed successfully")
        return 0
        
    except Exception as e:
        print(f"Failed to record demo: {e}", file=sys.stderr)
        return 1


def _handle_images(args) -> int:
    """Handle the images command."""
    if args.images_command == "list":
        return _list_images()
    elif args.images_command == "cleanup":
        return _cleanup_images()
    else:
        print("Please specify an images command: list or cleanup")
        return 1


def _list_images() -> int:
    """List available base images."""
    try:
        from .images import ImageManager
        
        manager = ImageManager()
        cache_dir = manager.cache_dir
        
        if not cache_dir.exists():
            print("No images found")
            return 0
        
        images = list(cache_dir.glob("*.qcow2"))
        
        if not images:
            print("No images found")
            return 0
        
        print("Available base images:")
        print(f"{'Image':<30} {'Size':<15} {'Status'}")
        print("-" * 60)
        
        for image_path in sorted(images):
            try:
                size = image_path.stat().st_size
                size_mb = size / (1024 * 1024)
                
                if manager._is_valid_qcow2(image_path):
                    status = "Valid"
                else:
                    status = "Corrupted"
                
                print(f"{image_path.name:<30} {size_mb:>8.1f}MB {status}")
                
            except Exception as e:
                print(f"{image_path.name:<30} {'Error':<15} {e}")
        
        return 0
        
    except Exception as e:
        print(f"Failed to list images: {e}", file=sys.stderr)
        return 1


def _cleanup_images() -> int:
    """Clean up corrupted images."""
    try:
        from .images import ImageManager
        
        manager = ImageManager()
        print("Cleaning up corrupted images...")
        
        manager.cleanup_corrupted_images()
        
        print("Cleanup completed")
        return 0
        
    except Exception as e:
        print(f"Failed to cleanup images: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
