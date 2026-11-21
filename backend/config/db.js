const { Pool } = require('pg');
const logger = require('./logger');

const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  port: parseInt(process.env.DB_PORT || '5434', 10),
  database: process.env.DB_NAME || 'finance_controller',
  user: process.env.DB_USER || 'finance_backend_user',
  password: process.env.DB_PASSWORD || 'backend_secure_password',
  max: 20,
  idleTimeoutMillis: 30000,
  connectionTimeoutMillis: 5000,
});

pool.on('error', (err) => {
  logger.error('Unexpected error on idle PostgreSQL client:', err);
});

async function query(text, params) {
  const start = Date.now();
  try {
    const res = await pool.query(text, params);
    const duration = Date.now() - start;
    if (duration > 500) {
      logger.warn(`Slow query executed in ${duration}ms: ${text}`);
    }
    return res;
  } catch (error) {
    logger.error(`Database query failed: ${text}`, { error: error.message, params });
    throw error;
  }
}

async function getClient() {
  const client = await pool.connect();
  return client;
}

async function testConnection() {
  try {
    const res = await pool.query('SELECT NOW() as current_time, current_user, current_database()');
    logger.info(`PostgreSQL connected successfully as '${res.rows[0].current_user}' to '${res.rows[0].current_database}'`);
    return true;
  } catch (err) {
    logger.error('Failed to connect to PostgreSQL:', err);
    return false;
  }
}

module.exports = {
  pool,
  query,
  getClient,
  testConnection
};
