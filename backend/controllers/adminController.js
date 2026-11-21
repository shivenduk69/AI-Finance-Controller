const argon2 = require('argon2');
const db = require('../config/db');
const { logAction } = require('../utils/auditLogger');
const { deleteCache } = require('../config/redis');

async function getPlatformMetrics(req, res, next) {
  try {
    const merchantsRes = await db.query('SELECT COUNT(*) FROM merchants WHERE status = $1', ['ACTIVE']);
    const storesRes = await db.query('SELECT COUNT(*) FROM stores WHERE status = $1', ['ACTIVE']);
    const txRes = await db.query(`
      SELECT 
        COUNT(*) as total_transactions,
        COALESCE(SUM(amount_inr), 0) as total_volume,
        COUNT(*) FILTER (WHERE exception_flag = 'YES') as raw_exceptions
      FROM transactions
    `);
    const resolvedRes = await db.query("SELECT COUNT(*) FROM exception_resolutions WHERE status = 'RESOLVED'");
    const ticketsRes = await db.query("SELECT COUNT(*) FROM support_tickets WHERE status IN ('OPEN', 'PENDING')");

    const totalTx = parseInt(txRes.rows[0].total_transactions, 10) || 0;
    const rawExc = parseInt(txRes.rows[0].raw_exceptions, 10) || 0;
    const resolvedCount = parseInt(resolvedRes.rows[0].count, 10) || 0;
    const activeExceptions = Math.max(0, rawExc - resolvedCount);

    // Compute daily volume trend series
    const trendRes = await db.query(`
      SELECT 
        expected_settlement_date as date,
        SUM(amount_inr) as current_volume
      FROM transactions
      WHERE expected_settlement_date IS NOT NULL AND expected_settlement_date != ''
      GROUP BY expected_settlement_date
      ORDER BY expected_settlement_date ASC
      LIMIT 14
    `);

    return res.json({
      success: true,
      data: {
        total_merchants: parseInt(merchantsRes.rows[0].count, 10) || 0,
        active_stores: parseInt(storesRes.rows[0].count, 10) || 0,
        total_transactions: totalTx,
        processing_volume_inr: parseFloat(txRes.rows[0].total_volume) || 0.0,
        unresolved_exceptions: activeExceptions,
        open_tickets: parseInt(ticketsRes.rows[0].count, 10) || 0,
        volume_trend: trendRes.rows.map(r => ({
          date: r.date,
          current_volume: parseFloat(r.current_volume),
          previous_volume: parseFloat((r.current_volume * 0.85).toFixed(2))
        }))
      }
    });
  } catch (error) {
    next(error);
  }
}

async function getMerchants(req, res, next) {
  try {
    const result = await db.query(`
      SELECT m.merchant_id, m.name, m.status, m.created_at,
             COUNT(s.store_id) as store_count
      FROM merchants m
      LEFT JOIN stores s ON m.merchant_id = s.merchant_id
      GROUP BY m.merchant_id, m.name, m.status, m.created_at
      ORDER BY m.name ASC
    `);
    return res.json({ success: true, data: result.rows });
  } catch (error) {
    next(error);
  }
}

async function createMerchant(req, res, next) {
  try {
    const { merchant_id, name, status = 'ACTIVE' } = req.body;
    if (!merchant_id || !name) {
      return res.status(400).json({ success: false, error: 'Merchant ID and Name are required' });
    }

    const q = 'INSERT INTO merchants (merchant_id, name, status, created_at) VALUES ($1, $2, $3, NOW()) RETURNING *';
    const result = await db.query(q, [merchant_id.trim().toLowerCase(), name.trim(), status]);

    await logAction(req.user.user_id, 'Merchant Created', `Created merchant ${name} (${merchant_id})`);
    return res.status(201).json({ success: true, data: result.rows[0] });
  } catch (error) {
    next(error);
  }
}

async function getStores(req, res, next) {
  try {
    const { merchant_id } = req.query;
    let query = `
      SELECT s.store_id, s.merchant_id, s.name, s.location, s.status, s.created_at, m.name as merchant_name
      FROM stores s
      JOIN merchants m ON s.merchant_id = m.merchant_id
    `;
    const params = [];
    if (merchant_id) {
      query += ' WHERE s.merchant_id = $1';
      params.push(merchant_id);
    }
    query += ' ORDER BY s.name ASC';

    const result = await db.query(query, params);
    return res.json({ success: true, data: result.rows });
  } catch (error) {
    next(error);
  }
}

async function createStore(req, res, next) {
  try {
    const { store_id, merchant_id, name, location, status = 'ACTIVE' } = req.body;
    if (!store_id || !merchant_id || !name) {
      return res.status(400).json({ success: false, error: 'Store ID, Merchant ID and Name are required' });
    }

    const q = 'INSERT INTO stores (store_id, merchant_id, name, location, status, created_at) VALUES ($1, $2, $3, $4, $5, NOW()) RETURNING *';
    const result = await db.query(q, [store_id.trim().toLowerCase(), merchant_id.trim().toLowerCase(), name.trim(), location || '', status]);

    await logAction(req.user.user_id, 'Store Created', `Created store ${name} (${store_id}) for ${merchant_id}`);
    return res.status(201).json({ success: true, data: result.rows[0] });
  } catch (error) {
    next(error);
  }
}

async function getUsers(req, res, next) {
  try {
    const result = await db.query(`
      SELECT user_id, email, role, merchant_id, store_id, created_at
      FROM users
      ORDER BY role ASC, created_at DESC
    `);
    return res.json({ success: true, data: result.rows });
  } catch (error) {
    next(error);
  }
}

async function createUser(req, res, next) {
  try {
    const { user_id, email, password, role, merchant_id, store_id } = req.body;
    if (!user_id || !email || !password || !role) {
      return res.status(400).json({ success: false, error: 'User ID, Email, Password and Role are required' });
    }

    const hash = await argon2.hash(password);
    const q = `
      INSERT INTO users (user_id, email, password_hash, role, merchant_id, store_id, created_at)
      VALUES ($1, $2, $3, $4, $5, $6, NOW())
      RETURNING user_id, email, role, merchant_id, store_id, created_at
    `;
    const result = await db.query(q, [user_id.trim(), email.trim().toLowerCase(), hash, role, merchant_id || null, store_id || null]);

    await logAction(req.user.user_id, 'User Provisioned', `Created user ${email} with role ${role}`);
    return res.status(201).json({ success: true, data: result.rows[0] });
  } catch (error) {
    next(error);
  }
}

async function getAuditLogs(req, res, next) {
  try {
    const limit = parseInt(req.query.limit || '100', 10);
    const result = await db.query('SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT $1', [limit]);
    return res.json({ success: true, count: result.rows.length, data: result.rows });
  } catch (error) {
    next(error);
  }
}

async function getConfig(req, res, next) {
  try {
    const result = await db.query('SELECT config_key, config_value FROM configuration');
    const configMap = {};
    result.rows.forEach(r => {
      // Mask api key for safety
      if (r.config_key.includes('api_key') && r.config_value) {
        configMap[r.config_key] = '••••••••••••••••' + r.config_value.slice(-4);
      } else {
        configMap[r.config_key] = r.config_value;
      }
    });
    return res.json({ success: true, data: configMap });
  } catch (error) {
    next(error);
  }
}

async function updateConfig(req, res, next) {
  try {
    const { config_key, config_value } = req.body;
    if (!config_key || config_value === undefined) {
      return res.status(400).json({ success: false, error: 'Key and Value are required' });
    }

    await db.query(`
      INSERT INTO configuration (config_key, config_value)
      VALUES ($1, $2)
      ON CONFLICT (config_key) DO UPDATE SET config_value = EXCLUDED.config_value
    `, [config_key, String(config_value)]);

    await logAction(req.user.user_id, 'Config Updated', `Updated setting ${config_key}`);
    return res.json({ success: true, message: `Configuration '${config_key}' updated.` });
  } catch (error) {
    next(error);
  }
}

module.exports = {
  getPlatformMetrics,
  getMerchants,
  createMerchant,
  getStores,
  createStore,
  getUsers,
  createUser,
  getAuditLogs,
  getConfig,
  updateConfig
};
