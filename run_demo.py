#!/usr/bin/env python3
"""
Universal Caller Adapter - Demo Runner
=======================================

This script provides an easy way to run demos of the Universal Caller Adapter.
It automatically starts the server, runs the selected demo, and cleans up.

Usage:
    python run_demo.py              # Interactive mode - choose which demo to run
    python run_demo.py --simple     # Run simple educational demo only
    python run_demo.py --full       # Run comprehensive demo only
    python run_demo.py --both       # Run both demos in sequence
"""

import asyncio
import subprocess
import time
import sys
import signal
import argparse
from typing import Optional

# Color codes for pretty terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


class ServerManager:
    """Manages starting and stopping the demo server"""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None

    def start(self):
        """Start the server in the background"""
        print(f"{Colors.BLUE}Starting server...{Colors.END}")
        try:
            self.process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait for server to be ready
            print(f"{Colors.BLUE}Waiting for server to be ready...{Colors.END}")
            if not self._wait_for_server():
                print(f"{Colors.RED}Server failed to start!{Colors.END}")
                self.stop()
                sys.exit(1)

            print(f"{Colors.GREEN}✓ Server is running (PID: {self.process.pid}){Colors.END}\n")

        except Exception as e:
            print(f"{Colors.RED}Failed to start server: {e}{Colors.END}")
            sys.exit(1)

    def _wait_for_server(self, timeout: int = 10) -> bool:
        """Wait for server to respond to health checks"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Check if process is still running
                if self.process.poll() is not None:
                    return False

                # Try to connect to server
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', 8000))
                sock.close()

                if result == 0:
                    # Give it a moment to fully initialize
                    time.sleep(0.5)
                    return True

            except Exception:
                pass

            time.sleep(0.5)

        return False

    def stop(self):
        """Stop the server"""
        if self.process:
            print(f"\n{Colors.BLUE}Stopping server...{Colors.END}")
            try:
                self.process.terminate()
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
                print(f"{Colors.GREEN}✓ Server stopped{Colors.END}")
            except Exception as e:
                print(f"{Colors.YELLOW}Warning: Error stopping server: {e}{Colors.END}")


async def run_simple_demo():
    """
    Run the simple educational demo.

    This demo explains the concepts step-by-step with interactive prompts.
    Perfect for learning how the Universal Caller Adapter works.
    """
    # Import the simple demo module
    import simple_demo

    await simple_demo.main()


async def run_full_demo():
    """
    Run the comprehensive demo.

    This demo shows all authentication methods and authorization scenarios
    in a comprehensive, automated way.
    """
    # Import the full demo module
    import demo

    await demo.demo()


def print_banner():
    """Print the welcome banner"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'Universal Caller Adapter - Demo Runner'.center(80)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.END}\n")


def print_menu():
    """Print the demo selection menu"""
    print(f"{Colors.BOLD}Available Demos:{Colors.END}\n")

    print(f"{Colors.GREEN}1. Simple Educational Demo{Colors.END}")
    print("   - Interactive, step-by-step walkthrough")
    print("   - Explains concepts as you go")
    print("   - Best for learning\n")

    print(f"{Colors.GREEN}2. Comprehensive Demo{Colors.END}")
    print("   - Automated, complete demonstration")
    print("   - Shows all authentication methods")
    print("   - Shows all authorization scenarios\n")

    print(f"{Colors.GREEN}3. Both Demos{Colors.END}")
    print("   - Run simple demo first, then comprehensive demo\n")


def get_user_choice() -> str:
    """Get the user's demo choice"""
    while True:
        choice = input(f"{Colors.BOLD}Select demo (1-3, or 'q' to quit): {Colors.END}").strip()
        if choice in ['1', '2', '3', 'q', 'Q']:
            return choice
        print(f"{Colors.RED}Invalid choice. Please enter 1, 2, 3, or 'q'{Colors.END}")


async def main():
    """Main entry point for the demo runner"""

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Run Universal Caller Adapter demos')
    parser.add_argument('--simple', action='store_true', help='Run simple educational demo')
    parser.add_argument('--full', action='store_true', help='Run comprehensive demo')
    parser.add_argument('--both', action='store_true', help='Run both demos')
    args = parser.parse_args()

    # Determine which demo to run
    if args.simple:
        choice = '1'
    elif args.full:
        choice = '2'
    elif args.both:
        choice = '3'
    else:
        # Interactive mode
        print_banner()
        print_menu()
        choice = get_user_choice()

        if choice.lower() == 'q':
            print(f"\n{Colors.YELLOW}Goodbye!{Colors.END}\n")
            return

    # Start the server
    server = ServerManager()

    # Set up signal handlers for clean shutdown
    def signal_handler(signum, frame):
        print(f"\n\n{Colors.YELLOW}Interrupted! Cleaning up...{Colors.END}")
        server.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        server.start()

        # Run the selected demo(s)
        if choice == '1':
            await run_simple_demo()
        elif choice == '2':
            await run_full_demo()
        elif choice == '3':
            await run_simple_demo()
            print(f"\n{Colors.BOLD}Press ENTER to continue to comprehensive demo...{Colors.END}")
            input()
            await run_full_demo()

        print(f"\n{Colors.BOLD}{Colors.GREEN}{'=' * 80}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}{'Demo(s) complete!'.center(80)}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.GREEN}{'=' * 80}{Colors.END}\n")

    except KeyboardInterrupt:
        print(f"\n\n{Colors.YELLOW}Demo interrupted by user.{Colors.END}")
    except Exception as e:
        print(f"\n\n{Colors.RED}Error running demo: {e}{Colors.END}")
        import traceback
        traceback.print_exc()
    finally:
        server.stop()


if __name__ == "__main__":
    asyncio.run(main())
