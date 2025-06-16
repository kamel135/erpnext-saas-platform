from flask import Flask, jsonify, request, render_template, Response
import logging
import os
import subprocess
import threading
import time
from provision import (
    create_docker_compose,
    start_services,
    install_erpnext_site,
    cleanup_failed_site
)

# Configure logging
logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

# Constants
SITES_ROOT = "/var/saas_sites"

# Store site creation status
site_creation_status = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/sites')
def sites():
    sites_list = []
    if os.path.exists(SITES_ROOT):
        sites_list = [
            d for d in os.listdir(SITES_ROOT)
            if os.path.isdir(os.path.join(SITES_ROOT, d))
        ]
    return render_template('sites.html', sites=sites_list)

def create_site_background(site_name, domain, db_password, erpnext_image, admin_password):
    """Background task to create site"""
    try:
        # Update status
        site_creation_status[site_name] = {"status": "creating", "step": "Initializing..."}
        
        # Step 1: Create docker-compose file
        site_creation_status[site_name]["step"] = "Creating Docker configuration..."
        compose_file = create_docker_compose(
            site_name=site_name,
            domain=domain,
            db_password=db_password,
            erpnext_image=erpnext_image
        )
        logging.info(f"Docker compose file created at {compose_file}")
        
        # Step 2: Start services
        site_creation_status[site_name]["step"] = "Starting containers..."
        start_services(compose_file, site_name)
        logging.info(f"Services started for {site_name}")
        
        # Step 3: Install ERPNext
        site_creation_status[site_name]["step"] = "Installing ERPNext (this may take 5-10 minutes)..."
        install_erpnext_site(
            site_name=site_name,
            site_domain=domain,
            db_password=db_password,
            admin_password=admin_password
        )
        
        # Success
        site_creation_status[site_name] = {"status": "ready", "step": "Site ready!"}
        logging.info(f"Site {site_name} created successfully")
        
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error creating site '{site_name}': {error_msg}")
        site_creation_status[site_name] = {"status": "error", "step": error_msg}
        # Cleanup on failure
        try:
            cleanup_failed_site(site_name)
        except:
            pass

@app.route('/api/create-site', methods=['POST'])
def api_create_site():
    site_name = None
    try:
        data = request.get_json(force=True)
        site_name = data.get('name')
        if not site_name:
            raise ValueError("Site name is required")
        admin_password = data.get('password')
        if not admin_password:
            raise ValueError("Admin password is required")

        domain = f"{site_name}.orbscope.local"
        db_password = "123"
        erpnext_image = "frappe/erpnext:v15.19.1"

        logging.info(f"Starting site creation for {site_name}")
        os.makedirs(SITES_ROOT, exist_ok=True)

        # Check if site already exists
        if site_name in site_creation_status and site_creation_status[site_name]["status"] == "creating":
            return jsonify({
                "status": "error",
                "message": "Site creation already in progress"
            }), 400

        # Start background thread for site creation
        thread = threading.Thread(
            target=create_site_background,
            args=(site_name, domain, db_password, erpnext_image, admin_password)
        )
        thread.daemon = True
        thread.start()

        return jsonify({
            "status": "success",
            "message": "Site creation started",
            "domain": domain
        }), 200

    except Exception as e:
        logging.error(f"API Error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/site/<site_name>/status')
def api_site_status(site_name):
    """Check the status of a site creation."""
    try:
        # Check creation status first
        if site_name in site_creation_status:
            status_info = site_creation_status[site_name]
            return jsonify({
                "status": status_info["status"],
                "message": status_info["step"]
            })
        
        # Check if site exists on disk
        compose_file = os.path.join(SITES_ROOT, site_name, 'docker-compose.yml')
        if not os.path.exists(compose_file):
            return jsonify({"status": "not_found"})
        
        # Check container status
        cmd = ["docker", "compose", "-f", compose_file, "ps", "--format", "json"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({"status": "error", "message": "Failed to check container status"})
        
        # Parse container status
        import json as json_lib
        try:
            containers = json_lib.loads(result.stdout) if result.stdout else []
            
            # Check if all required containers are running
            required_services = ['backend', 'frontend', 'mariadb', 'redis-cache']
            running_services = [c['Service'] for c in containers if c.get('State') == 'running']
            
            all_running = all(any(service in svc for svc in running_services) for service in required_services)
            
            if all_running:
                # Try to check if site is accessible
                site_check_cmd = [
                    "docker", "compose", "-f", compose_file,
                    "exec", "-T", "backend",
                    "bench", "--site", f"{site_name}.orbscope.local", "version"
                ]
                site_result = subprocess.run(site_check_cmd, capture_output=True, text=True, timeout=10)
                
                if site_result.returncode == 0:
                    return jsonify({"status": "ready", "message": "Site is ready!"})
                else:
                    return jsonify({"status": "installing", "message": "Installing ERPNext..."})
            else:
                return jsonify({"status": "starting", "message": "Starting containers..."})
                
        except Exception as e:
            logging.error(f"Status check error: {e}")
            return jsonify({"status": "unknown", "message": "Unable to determine status"})
            
    except Exception as e:
        logging.error(f"Status API error: {e}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/logs/<site_name>')
def api_logs(site_name):
    """Get logs for a specific site."""
    try:
        compose_file = os.path.join(SITES_ROOT, site_name, "docker-compose.yml")
        if not os.path.exists(compose_file):
            return jsonify({"error": "Site not found"}), 404
        
        cmd = [
            "docker", "compose",
            "-f", compose_file,
            "logs", "--no-color", "--tail", "100"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            return jsonify({"error": result.stderr}), 500
            
        return jsonify({"logs": result.stdout})
    except Exception as e:
        logging.error(f"Logs API error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/logs/<site_name>')
def logs_page(site_name):
    """Display logs page for a site."""
    return render_template('logs.html', site_name=site_name)

@app.route('/api/site/<site_name>/delete', methods=['POST'])
def api_delete_site(site_name):
    try:
        if not site_name:
            raise ValueError("Site name is required")
        
        # Remove from status tracking
        if site_name in site_creation_status:
            del site_creation_status[site_name]
        
        cleanup_failed_site(site_name)
        return jsonify({
            "status": "success",
            "message": f"Site {site_name} deleted successfully"
        }), 200
    except Exception as e:
        logging.error(f"Error deleting site {site_name}: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/sites/list')
def api_sites_list():
    """Get list of all sites with their status."""
    try:
        sites_info = []
        if os.path.exists(SITES_ROOT):
            for site_name in os.listdir(SITES_ROOT):
                site_path = os.path.join(SITES_ROOT, site_name)
                if os.path.isdir(site_path):
                    # Get site status
                    status = "unknown"
                    compose_file = os.path.join(site_path, 'docker-compose.yml')
                    if os.path.exists(compose_file):
                        # Check if containers are running
                        cmd = ["docker", "compose", "-f", compose_file, "ps", "-q"]
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        if result.stdout.strip():
                            status = "running"
                        else:
                            status = "stopped"
                    
                    sites_info.append({
                        "name": site_name,
                        "domain": f"{site_name}.orbscope.local",
                        "status": status
                    })
        return jsonify({"sites": sites_info})
    except Exception as e:
        logging.error(f"Sites list API error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/site/<site_name>/start', methods=['POST'])
def api_start_site(site_name):
    """Start a stopped site."""
    try:
        compose_file = os.path.join(SITES_ROOT, site_name, 'docker-compose.yml')
        if not os.path.exists(compose_file):
            return jsonify({"status": "error", "message": "Site not found"}), 404
        
        cmd = ["docker", "compose", "-f", compose_file, "up", "-d"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to start site: {result.stderr}")
        
        return jsonify({
            "status": "success",
            "message": f"Site {site_name} started successfully"
        }), 200
    except Exception as e:
        logging.error(f"Error starting site {site_name}: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/site/<site_name>/stop', methods=['POST'])
def api_stop_site(site_name):
    """Stop a running site."""
    try:
        compose_file = os.path.join(SITES_ROOT, site_name, 'docker-compose.yml')
        if not os.path.exists(compose_file):
            return jsonify({"status": "error", "message": "Site not found"}), 404
        
        cmd = ["docker", "compose", "-f", compose_file, "stop"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to stop site: {result.stderr}")
        
        return jsonify({
            "status": "success",
            "message": f"Site {site_name} stopped successfully"
        }), 200
    except Exception as e:
        logging.error(f"Error stopping site {site_name}: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/site/<site_name>/restart', methods=['POST'])
def api_restart_site(site_name):
    """Restart a site."""
    try:
        compose_file = os.path.join(SITES_ROOT, site_name, 'docker-compose.yml')
        if not os.path.exists(compose_file):
            return jsonify({"status": "error", "message": "Site not found"}), 404
        
        cmd = ["docker", "compose", "-f", compose_file, "restart"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise Exception(f"Failed to restart site: {result.stderr}")
        
        return jsonify({
            "status": "success",
            "message": f"Site {site_name} restarted successfully"
        }), 200
    except Exception as e:
        logging.error(f"Error restarting site {site_name}: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 400

@app.route('/api/docker/pull-progress')
def docker_pull_progress():
    """Stream Docker pull progress using Server-Sent Events."""
    def generate():
        # This is a placeholder for actual Docker pull progress
        # In production, you would track actual Docker pull events
        yield f"data: {{'status': 'pulling', 'progress': 'Starting pull...'}}\n\n"
        time.sleep(1)
        yield f"data: {{'status': 'complete', 'progress': 'Pull complete'}}\n\n"
    
    return Response(generate(), mimetype="text/event-stream")

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "ERPNext SaaS Control Plane",
        "timestamp": time.time()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
