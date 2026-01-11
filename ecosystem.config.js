// ==========================================
// CONFIGURATION - Modifiez ces valeurs
// ==========================================
const CONFIG = {
  API_PORT: 8151,        // Port de l'API backend
  GUI_PORT: 8150,        // Port de l'interface web
  SECRET_KEY: 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx', // Clé secrète pour la sécurité
  NPM_API_URL: 'http://localhost:81/api',
  NPM_EMAIL: 'admin@example.com',
  NPM_PASSWORD: 'changeme',
  DEPLOY_HOST: '217.154.6.178',
  DEPLOY_USER: 'root'
}
// ==========================================

module.exports = {
  apps: [
    {
      name: 'firewall-ui-backend',
      cwd: './backend',
      script: 'bash',
      args: '-c "python3 -m venv venv 2>/dev/null || true; . venv/bin/activate; pip install -q -r requirements.txt 2>/dev/null; exec python -u main.py"',
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
        API_PORT: CONFIG.API_PORT,
        SECRET_KEY: CONFIG.SECRET_KEY,
        DATABASE_URL: 'sqlite+aiosqlite:///./firewall_manager.db',
        CORS_ORIGINS: `http://localhost:${CONFIG.GUI_PORT},http://127.0.0.1:${CONFIG.GUI_PORT},http://0.0.0.0:${CONFIG.GUI_PORT}`,
        NPM_API_URL: CONFIG.NPM_API_URL,
        NPM_EMAIL: CONFIG.NPM_EMAIL,
        NPM_PASSWORD: CONFIG.NPM_PASSWORD
      },
      watch: false,
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      error_file: './logs/backend-error.log',
      out_file: './logs/backend-out.log',
      merge_logs: true,
      max_memory_restart: '500M'
    },
    {
      name: 'firewall-ui-frontend',
      cwd: './frontend',
      script: 'bash',
      args: `-c "[ ! -d node_modules ] && npm install; [ ! -d dist ] && npm run build; exec npx vite preview --host --port ${CONFIG.GUI_PORT}"`,
      interpreter: 'none',
      env: {
        NODE_ENV: 'production',
        PORT: CONFIG.GUI_PORT,
        VITE_API_URL: `http://localhost:${CONFIG.API_PORT}`
      },
      watch: false,
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      max_restarts: 10,
      restart_delay: 3000,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      error_file: './logs/frontend-error.log',
      out_file: './logs/frontend-out.log',
      merge_logs: true
    }
  ],

  deploy: {
    production: {
      user: CONFIG.DEPLOY_USER,
      host: CONFIG.DEPLOY_HOST,
      ref: 'origin/main',
      repo: 'git@github.com:your-username/firewall-ui-linux.git',
      path: '/opt/firewall-ui',
      'pre-deploy-local': '',
      'post-deploy': 'cd backend && python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt && cd ../frontend && npm install && npm run build && pm2 reload ecosystem.config.js --env production',
      'pre-setup': ''
    }
  }
}
