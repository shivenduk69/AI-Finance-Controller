const db = require('../config/db');
const logger = require('../config/logger');

async function logAction(userId, action, details = '') {
  try {
    const text = typeof details === 'object' ? JSON.stringify(details) : String(details);
    await db.query(
      'INSERT INTO audit_logs (user_id, action, details, timestamp) VALUES ($1, $2, $3, NOW())',
      [userId || 'system', action, text]
    );
  } catch (error) {
    logger.error(`Failed to record audit log: ${action}`, { error: error.message });
  }
}

module.exports = {
  logAction
};
