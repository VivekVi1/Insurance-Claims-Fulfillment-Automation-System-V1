#!/usr/bin/env python3
"""
AI Insurance Claim Processing System - Startup Script

This script starts all the microservices and the main monitoring system.
Use this for development and testing purposes.
"""

import os
import sys
import time
import signal
import subprocess
from pathlib import Path

class SystemStarter:
    def __init__(self):
        self.processes = []
        self.services = [
            {
                'name': 'User Validator API',
                'script': 'apis/user_validator.py',
                'port': 8000,
                'health_endpoint': 'http://localhost:8000/'
            },
            {
                'name': 'Mail Service API',
                'script': 'apis/mail_service.py', 
                'port': 8001,
                'health_endpoint': 'http://localhost:8001/'
            },
            {
                'name': 'Fulfillment API',
                'script': 'apis/fulfillment_api.py',
                'port': 8002,
                'health_endpoint': 'http://localhost:8002/'
            }
        ]
        
    def check_prerequisites(self):
        """Check if all required files exist"""
        print("[CHECK] Checking prerequisites...")
        
        # Check if .env file exists
        if not Path('.env').exists():
            print("[ERROR] .env file not found!")
            print("[INFO] Please create a .env file using the template in setup_guide.md")
            return False
            
        # Check if all API scripts exist
        for service in self.services:
            script_path = Path(service['script'])
            if not script_path.exists():
                print(f"[ERROR] {service['script']} not found!")
                return False
                
        # Check if main scripts exist
        required_scripts = ['mail_monitor.py', 'fulfillment_processor.py', 's3_uploader.py']
        for script in required_scripts:
            if not Path(script).exists():
                print(f"[ERROR] {script} not found!")
                return False
                
        print("[OK] All prerequisites met!")
        return True
        
    def start_service(self, service):
        """Start a single service"""
        print(f"[START] Starting {service['name']} on port {service['port']}...")
        
        try:
            process = subprocess.Popen(
                [sys.executable, service['script']],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes.append({
                'process': process,
                'name': service['name'],
                'port': service['port']
            })
            
            # Give the service a moment to start
            time.sleep(2)
            
            # Check if process is still running
            if process.poll() is None:
                print(f"[OK] {service['name']} started successfully")
                return True
            else:
                stdout, stderr = process.communicate()
                print(f"[ERROR] {service['name']} failed to start")
                print(f"Error: {stderr}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to start {service['name']}: {e}")
            return False
            
    def start_all_services(self):
        """Start all API services"""
        print("\n[PROCESS] Starting API services...")
        
        success_count = 0
        for service in self.services:
            if self.start_service(service):
                success_count += 1
            else:
                print(f"[WARN] Failed to start {service['name']}")
                
        print(f"\n[DATA] Started {success_count}/{len(self.services)} services")
        
        if success_count == len(self.services):
            print("[OK] All API services started successfully!")
            return True
        else:
            print("[WARN] Some services failed to start. Check the errors above.")
            return False
            
    def start_mail_monitor(self):
        """Start the main mail monitoring system"""
        print("\n[START] Starting Mail Monitor (main system)...")
        
        try:
            process = subprocess.Popen(
                [sys.executable, 'mail_monitor.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self.processes.append({
                'process': process,
                'name': 'Mail Monitor',
                'port': 'N/A'
            })
            
            print("[OK] Mail Monitor started!")
            print("[EMAIL] System is now monitoring emails...")
            print("\n" + "="*60)
            print("[READY] SYSTEM READY - AI Insurance Claim Processing Active")
            print("="*60)
            
            # Stream output from mail monitor
            try:
                for line in iter(process.stdout.readline, ''):
                    if line:
                        print(line.rstrip())
                        
            except KeyboardInterrupt:
                print("\n[STOP] Received interrupt signal...")
                
        except Exception as e:
            print(f"[ERROR] Failed to start Mail Monitor: {e}")
            return False
            
    def stop_all_services(self):
        """Stop all running services"""
        print("\n[STOP] Stopping all services...")
        
        for proc_info in self.processes:
            try:
                process = proc_info['process']
                name = proc_info['name']
                
                if process.poll() is None:  # Process is still running
                    print(f"[PROCESS] Stopping {name}...")
                    process.terminate()
                    
                    # Wait up to 5 seconds for graceful shutdown
                    try:
                        process.wait(timeout=5)
                        print(f"[OK] {name} stopped gracefully")
                    except subprocess.TimeoutExpired:
                        print(f"[WARN] Force killing {name}...")
                        process.kill()
                        process.wait()
                        print(f"[KILLED] {name} force stopped")
                        
            except Exception as e:
                print(f"[ERROR] Error stopping {proc_info['name']}: {e}")
                
        print("[CLOSED] All services stopped")
        
    def show_status(self):
        """Show status of all services"""
        print("\n[DATA] Service Status:")
        print("-" * 50)
        
        for service in self.services:
            print(f"[API] {service['name']:<20} Port {service['port']:<5} {service['health_endpoint']}")
            
        print(f"[EMAIL] Mail Monitor          Main System")
        print("-" * 50)
        
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            print(f"\n[SIGNAL] Received signal {signum}")
            self.stop_all_services()
            sys.exit(0)
            
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
    def run(self):
        """Main execution method"""
        print("[SYSTEM] AI Insurance Claim Processing System - Startup")
        print("=" * 55)
        
        # Check prerequisites
        if not self.check_prerequisites():
            print("\n[ERROR] Prerequisites not met. Please fix the issues above.")
            sys.exit(1)
            
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Start API services
        if not self.start_all_services():
            print("\n[ERROR] Failed to start all API services.")
            print("[TIP] Try starting services individually to debug issues.")
            self.stop_all_services()
            sys.exit(1)
            
        # Show service status
        self.show_status()
        
        # Start mail monitor (this will run indefinitely)
        print("\n[WAIT] Waiting 5 seconds for all services to stabilize...")
        time.sleep(5)
        
        try:
            self.start_mail_monitor()
        except KeyboardInterrupt:
            pass
        finally:
            self.stop_all_services()

def main():
    """Main entry point"""
    try:
        starter = SystemStarter()
        starter.run()
    except Exception as e:
        print(f"\n[FATAL] Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 