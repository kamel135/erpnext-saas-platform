import os
import subprocess
import time
import logging
from jinja2 import Environment, FileSystemLoader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(module)s: %(message)s'
)

# Constants
SITES_ROOT = "/var/saas_sites"
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Setup Jinja2 environment
env = Environment(loader=FileSystemLoader(TEMPLATES_DIR))

def run_command(command, site_name=""):
    """Runs a command and logs its output."""
    logging.info(f"provision: Running command: {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True)
    
    if result.returncode != 0:
        logging.error(f"provision: Command failed for '{site_name}'")
        logging.error(f"provision: Return code: {result.returncode}")
        if result.stdout:
            logging.error(f"provision: --- STDOUT ---")
            logging.error(result.stdout.strip())
        if result.stderr:
            logging.error(f"provision: --- STDERR ---")
            logging.error(result.stderr.strip())
        return False
    
    if result.stdout:
        logging.info(f"provision: Command output:")
        logging.info(result.stdout.strip())
    if result.stderr:
        logging.warning(f"provision: Command stderr:")
        logging.warning(result.stderr.strip())
    
    return True

def create_docker_compose(site_name, domain, db_password, erpnext_image):
    """Creates a docker-compose.yml file for a new site from a template."""
    site_dir = os.path.join(SITES_ROOT, site_name)
    os.makedirs(site_dir, exist_ok=True)
    
    # Load and render the template
    compose_template = env.get_template('erpnext-compose.yml.j2')
    compose_content = compose_template.render(
        site_name=site_name,
        domain=domain,
        db_root_password=db_password,
        erpnext_image=erpnext_image
    )
    
    # Write the docker-compose.yml file
    compose_file_path = os.path.join(site_dir, 'docker-compose.yml')
    with open(compose_file_path, 'w') as f:
        f.write(compose_content)
    
    logging.info(f"provision: Created docker-compose.yml for {site_name}")
    return compose_file_path

def start_services(compose_file_path, site_name):
    """Starts the docker containers using docker-compose up."""
    command = ["docker", "compose", "-f", compose_file_path, "up", "-d"]
    if not run_command(command, site_name):
        raise Exception(f"Failed to start services for {site_name}")

def install_erpnext_site(site_name, site_domain, db_password, admin_password):
    """Installs a new ERPNext site inside the running containers."""
    logging.info(f"provision: Installing ERPNext on site {site_domain}...")
    compose_file = os.path.join(SITES_ROOT, site_name, 'docker-compose.yml')
    
    # Step 1: Configure the common_site_config.json
    logging.info("provision: Configuring site settings...")
    config_cmd = [
        "docker", "compose", "-f", compose_file,
        "exec", "-T", "backend", "bash", "-c",
        "bench set-config -g db_host mariadb; "
        "bench set-config -g redis_cache 'redis://redis-cache:6379'; "
        "bench set-config -g redis_queue 'redis://redis-queue:6379'; "
        "bench set-config -g redis_socketio 'redis://redis-queue:6379'"
    ]
    
    if not run_command(config_cmd, site_name):
        logging.warning("provision: Configuration command failed, but continuing...")
    
    # Step 2: Wait for MariaDB to be fully ready
    logging.info("provision: Waiting for MariaDB to be ready...")
    for i in range(10):  # Try for 50 seconds
        check_db_cmd = [
            "docker", "compose", "-f", compose_file,
            "exec", "-T", "mariadb",
            "mysql", "-uroot", f"-p{db_password}", "-e", "SELECT 1"
        ]
        result = subprocess.run(check_db_cmd, capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("provision: MariaDB is ready!")
            break
        logging.info(f"provision: Waiting for MariaDB... ({i+1}/10)")
        time.sleep(5)
    else:
        logging.warning("provision: MariaDB might not be fully ready, but continuing...")
    
    # Step 3: Create the new site with ERPNext installed
    logging.info("provision: Creating new site with ERPNext...")
    create_site_cmd = [
        "docker", "compose", "-f", compose_file,
        "exec", "-T", "backend",
        "bench", "new-site", site_domain,
        "--mariadb-root-password", db_password,
        "--admin-password", admin_password,
        "--install-app", "erpnext"
    ]
    
    if not run_command(create_site_cmd, site_name):
        raise Exception(f"ERPNext installation failed for {site_domain}. Check logs for details.")
    
    # Step 4: Set the created site as default
    logging.info("provision: Setting site as default...")
    set_default_cmd = [
        "docker", "compose", "-f", compose_file,
        "exec", "-T", "backend",
        "bench", "use", site_domain
    ]
    run_command(set_default_cmd, site_name)
    
    # Step 5: Clear cache and restart services
    logging.info("provision: Clearing cache and optimizing...")
    clear_cache_cmd = [
        "docker", "compose", "-f", compose_file,
        "exec", "-T", "backend",
        "bench", "clear-cache"
    ]
    run_command(clear_cache_cmd, site_name)
    
    logging.info(f"provision: Successfully installed ERPNext on site {site_domain}.")

def cleanup_failed_site(site_name):
    """Cleans up resources for a failed site creation."""
    logging.info(f"provision: Starting cleanup for failed site: {site_name}")
    site_dir = os.path.join(SITES_ROOT, site_name)
    compose_file_path = os.path.join(site_dir, 'docker-compose.yml')

    if os.path.exists(compose_file_path):
        # Stop and remove containers, networks, and volumes
        command_down = [
            "docker", "compose", "-f", compose_file_path, 
            "down", "-v", "--remove-orphans"
        ]
        run_command(command_down, site_name)
        
        # Remove the site directory
        try:
            import shutil
            shutil.rmtree(site_dir)
            logging.info(f"provision: Removed site directory: {site_dir}")
        except Exception as e:
            logging.error(f"provision: Failed to remove directory: {e}")

    logging.info(f"provision: Cleanup finished for {site_name}")

def get_site_status(site_name):
    """Check if a site's containers are running."""
    compose_file = os.path.join(SITES_ROOT, site_name, 'docker-compose.yml')
    if not os.path.exists(compose_file):
        return "not_found"
    
    cmd = ["docker", "compose", "-f", compose_file, "ps", "--format", "json"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        return "error"
    
    try:
        import json
        containers = json.loads(result.stdout)
        if not containers:
            return "stopped"
        
        # Check if all containers are running
        all_running = all(c.get('State') == 'running' for c in containers)
        return "running" if all_running else "partial"
    except:
        return "unknown"

def stop_site(site_name):
    """Stop all containers for a site."""
    compose_file = os.path.join(SITES_ROOT, site_name, 'docker-compose.yml')
    if not os.path.exists(compose_file):
        raise Exception(f"Site {site_name} not found")
    
    cmd = ["docker", "compose", "-f", compose_file, "stop"]
    if not run_command(cmd, site_name):
        raise Exception(f"Failed to stop site {site_name}")
    
    logging.info(f"provision: Site {site_name} stopped successfully")

def start_site(site_name):
    """Start all containers for a site."""
    compose_file = os.path.join(SITES_ROOT, site_name, 'docker-compose.yml')
    if not os.path.exists(compose_file):
        raise Exception(f"Site {site_name} not found")
    
    cmd = ["docker", "compose", "-f", compose_file, "start"]
    if not run_command(cmd, site_name):
        raise Exception(f"Failed to start site {site_name}")
    
    logging.info(f"provision: Site {site_name} started successfully")
