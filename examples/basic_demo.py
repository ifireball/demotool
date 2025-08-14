#!/usr/bin/env python3
"""
Basic demo example using demotool.

This script demonstrates the basic usage of demotool for creating
automated demos with virtual machines.
"""

import time
from pathlib import Path

# Import demotool
import demotool


def basic_demo():
    """Basic demo workflow."""
    print("Starting basic demo...")
    
    with demotool.startdemo("basic-example") as demo:
        print(f"Demo directory: {demo.directory}")
        
        with demo.vm("fedora", "42") as vm:
            print(f"VM is ready!")
            print(f"VNC port: {vm.vnc_port}")
            print(f"Demo directory: {vm.directory}")
            
            # Create a sample output file
            output_file = demo.create_output_file("demo-info.txt")
            with open(output_file, "w") as f:
                f.write(f"Demo: basic-example\n")
                f.write(f"VM VNC Port: {vm.vnc_port}\n")
                f.write(f"Created: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            
            print(f"Created output file: {output_file}")
            
            # Simulate some demo work
            print("Demo is running... (press Ctrl+C to stop)")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nDemo interrupted by user")
    
    print("Basic demo completed!")


def quick_demo():
    """Quick demo using the convenience function."""
    print("Starting quick demo...")
    
    with demotool.recordDemo("quick-example", "fedora", "42") as vm:
        print(f"Quick demo VM is ready!")
        print(f"VNC port: {vm.vnc_port}")
        print(f"Demo directory: {vm.directory}")
        
        # Simulate demo work
        print("Quick demo is running... (press Ctrl+C to stop)")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nQuick demo interrupted by user")
    
    print("Quick demo completed!")


def multi_section_demo():
    """Demo with multiple sections."""
    print("Starting multi-section demo...")
    
    with demotool.startdemo("multi-section-example") as demo:
        print(f"Demo directory: {demo.directory}")
        
        with demo.vm("fedora", "42") as vm:
            print(f"VM is ready!")
            print(f"VNC port: {vm.vnc_port}")
            
            # Section 1: Setup
            print("\n=== Section 1: Setup ===")
            setup_file = demo.create_output_file("setup.txt")
            with open(setup_file, "w") as f:
                f.write("Setup phase completed\n")
            print("Setup phase completed")
            
            # Section 2: Main demo
            print("\n=== Section 2: Main Demo ===")
            main_file = demo.create_output_file("main-demo.txt")
            with open(main_file, "w") as f:
                f.write("Main demo phase completed\n")
            print("Main demo phase completed")
            
            # Section 3: Cleanup
            print("\n=== Section 3: Cleanup ===")
            cleanup_file = demo.create_output_file("cleanup.txt")
            with open(cleanup_file, "w") as f:
                f.write("Cleanup phase completed\n")
            print("Cleanup phase completed")
            
            print("\nMulti-section demo completed!")
    
    print("Multi-section demo finished!")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        demo_type = sys.argv[1]
        if demo_type == "basic":
            basic_demo()
        elif demo_type == "quick":
            quick_demo()
        elif demo_type == "multi":
            multi_section_demo()
        else:
            print(f"Unknown demo type: {demo_type}")
            print("Available types: basic, quick, multi")
            sys.exit(1)
    else:
        print("Running basic demo...")
        print("You can specify demo type: basic, quick, or multi")
        print()
        basic_demo()
