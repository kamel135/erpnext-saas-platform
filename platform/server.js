const express = require('express');
const path = require('path');
const session = require('express-session');
const { Pool } = require('pg');
const Redis = require('redis');
const Docker = require('dockerode');
require('dotenv').config();

const app = express();
const docker = new Docker({ socketPath: '/var/run/docker.sock' });

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL
});

// Redis connection
const redis = Redis.createClient({
  url: process.env.REDIS_URL
});
redis.connect().catch(console.error);

// Middleware
app.use(express.json());
app.use(express.urlencoded({ extended: true }));
app.use(express.static(path.join(__dirname, 'public')));
app.set('view engine', 'ejs');
app.set('views', path.join(__dirname, 'views'));

app.use(session({
  secret: process.env.SESSION_SECRET || 'your-secret-key',
  resave: false,
  saveUninitialized: false
}));

// Routes
app.get('/', (req, res) => {
  res.render('index', { title: 'ERPNext SaaS Platform' });
});

// Health check
app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date() });
});

// API: Create new tenant
app.post('/api/tenants', async (req, res) => {
  const { name, subdomain, email, plan } = req.body;
  
  try {
    // حفظ في قاعدة البيانات
    const result = await pool.query(
      `INSERT INTO tenants (name, subdomain, email, plan, status) 
       VALUES ($1, $2, $3, $4, 'creating') 
       RETURNING id`,
      [name, subdomain, email, plan]
    );
    
    const tenantId = result.rows[0].id;
    
    // إنشاء ERPNext instance
    const { exec } = require('child_process');
    exec(`/app/scripts/create_tenant.sh "${name}" "${subdomain}" "${email}" "${plan}"`, 
      (error, stdout, stderr) => {
        if (error) {
          console.error(`Error: ${error}`);
          return;
        }
        console.log(`Tenant created: ${stdout}`);
      }
    );
    
    res.json({ 
      success: true, 
      tenantId,
      message: 'Tenant creation started',
      url: `http://${subdomain}.localhost:8080`
    });
    
  } catch (error) {
    console.error('Error creating tenant:', error);
    res.status(500).json({ success: false, error: error.message });
  }
});

// API: List all tenants
app.get('/api/tenants', async (req, res) => {
  try {
    const result = await pool.query('SELECT * FROM tenants ORDER BY created_at DESC');
    res.json(result.rows);
  } catch (error) {
    console.error('Error fetching tenants:', error);
    res.json([]); // Return empty array if table doesn't exist yet
  }
});

// API: Get tenant status
app.get('/api/tenants/:id/status', async (req, res) => {
  const { id } = req.params;
  
  try {
    const result = await pool.query('SELECT * FROM tenants WHERE id = $1', [id]);
    const tenant = result.rows[0];
    
    if (!tenant) {
      return res.status(404).json({ error: 'Tenant not found' });
    }
    
    // Check Docker container status
    const containers = await docker.listContainers({ all: true });
    const tenantContainers = containers.filter(c => 
      c.Names.some(name => name.includes(tenant.subdomain))
    );
    
    res.json({
      tenant,
      containers: tenantContainers.map(c => ({
        name: c.Names[0],
        state: c.State,
        status: c.Status
      }))
    });
    
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Start server
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`🚀 SaaS Platform running on port ${PORT}`);
  console.log(`📌 Access the platform at: http://localhost:${PORT}`);
});
