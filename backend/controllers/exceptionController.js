const db = require('../config/db');
const { getTenantScope } = require('../middlewares/rbac');
const { logAction } = require('../utils/auditLogger');
const { deleteCache } = require('../config/redis');
const { getIO } = require('../sockets/socketHandler');

async function getExceptions(req, res, next) {
  try {
    const { merchantId, storeId, isAdmin } = getTenantScope(req);
    const { tab = 'active', severity, category, search } = req.query;

    let whereClause = 'WHERE 1=1';
    const params = [];
    let pIdx = 1;

    if (merchantId) {
      whereClause += ` AND er.merchant_id = $${pIdx++}`;
      params.push(merchantId);
    }
    if (storeId) {
      whereClause += ` AND er.store_id = $${pIdx++}`;
      params.push(storeId);
    }

    if (tab === 'pending_admin') {
      whereClause += ` AND er.status = 'PENDING_ADMIN'`;
    } else if (tab === 'resolved') {
      whereClause += ` AND er.status = 'RESOLVED'`;
    }

    if (search) {
      whereClause += ` AND (er.transaction_id ILIKE $${pIdx} OR er.order_id ILIKE $${pIdx})`;
      params.push(`%${search.trim()}%`);
      pIdx++;
    }

    if (tab === 'active') {
      // Active exceptions are transactions flagged with exception_flag = 'YES' that are NOT in pending or resolved
      let activeQ = `
        SELECT 
          t.transaction_id, t.order_id, t.type, t.status, t.method,
          t.amount_inr, t.fee_inr, t.tax_inr, t.settled_amount_inr,
          t.expected_settlement_date, t.timestamp, t.merchant_id, t.store_id
        FROM transactions t
        WHERE t.exception_flag = 'YES'
        AND t.transaction_id NOT IN (
          SELECT transaction_id FROM exception_resolutions WHERE status IN ('PENDING_ADMIN', 'RESOLVED')
        )
      `;
      const aParams = [];
      let aIdx = 1;
      if (merchantId) {
        activeQ += ` AND t.merchant_id = $${aIdx++}`;
        aParams.push(merchantId);
      }
      if (storeId) {
        activeQ += ` AND t.store_id = $${aIdx++}`;
        aParams.push(storeId);
      }
      if (search) {
        activeQ += ` AND (t.transaction_id ILIKE $${aIdx} OR t.order_id ILIKE $${aIdx})`;
        aParams.push(`%${search.trim()}%`);
      }
      activeQ += ' ORDER BY t.timestamp DESC';

      const activeRes = await db.query(activeQ, aParams);
      const formatted = activeRes.rows.map(r => ({
        id: r.transaction_id,
        transaction_id: r.transaction_id,
        order_id: r.order_id,
        type: 'Gateway Transaction',
        amount: parseFloat(r.amount_inr),
        severity: !r.order_id ? 'HIGH' : (r.status === 'disputed' ? 'HIGH' : 'MEDIUM'),
        status: 'OPEN',
        merchant_id: r.merchant_id,
        store_id: r.store_id,
        created_at: r.timestamp
      }));

      return res.json({ success: true, count: formatted.length, data: formatted });
    }

    // Tabs 'pending_admin' and 'resolved' from exception_resolutions table
    const query = `
      SELECT 
        resolution_id, transaction_id, order_id, merchant_id, store_id,
        amount_inr, issue_description, resolution_note, resolved_by_role,
        resolved_by_user, status, created_at
      FROM exception_resolutions er
      ${whereClause}
      ORDER BY created_at DESC
    `;
    const result = await db.query(query, params);

    return res.json({
      success: true,
      count: result.rows.length,
      data: result.rows
    });
  } catch (error) {
    next(error);
  }
}

async function resolveException(req, res, next) {
  try {
    const { id } = req.params; // transaction_id
    const { resolution_note, action = 'SUBMIT' } = req.body;
    const user = req.user;

    if (!resolution_note || resolution_note.trim().length === 0) {
      return res.status(400).json({ success: false, error: 'Resolution explanation note is required' });
    }

    // Retrieve transaction details
    const txRes = await db.query('SELECT * FROM transactions WHERE transaction_id = $1', [id]);
    if (txRes.rows.length === 0) {
      return res.status(404).json({ success: false, error: 'Transaction not found' });
    }
    const tx = txRes.rows[0];

    const io = getIO();
    let newStatus = 'RESOLVED';
    let message = '';

    if (user.role === 'MERCHANT') {
      newStatus = 'PENDING_ADMIN';
      message = `Merchant store submitted resolution for transaction ${id}. Awaiting admin review.`;

      // Insert or update exception_resolutions
      await db.query(`
        INSERT INTO exception_resolutions (
          transaction_id, order_id, merchant_id, store_id, amount_inr,
          issue_description, resolution_note, resolved_by_role, resolved_by_user, status, created_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
        ON CONFLICT (resolution_id) DO UPDATE SET
          resolution_note = EXCLUDED.resolution_note,
          status = EXCLUDED.status,
          resolved_by_user = EXCLUDED.resolved_by_user;
      `, [id, tx.order_id, tx.merchant_id, tx.store_id, tx.amount_inr, 'Discrepancy review submitted', resolution_note, user.role, user.user_id, newStatus]);

      // Notify Admins
      await db.query(`
        INSERT INTO notifications (user_id, merchant_id, store_id, role, title, message)
        VALUES (NULL, $1, $2, 'ADMIN', $3, $4)
      `, [tx.merchant_id, tx.store_id, `Resolution Pending: ${id}`, resolution_note]);

      if (io) {
        io.to('admin_room').emit('exception_submitted', { transaction_id: id, store_id: tx.store_id, note: resolution_note });
      }
    } else {
      // ADMIN role approving or directly resolving
      newStatus = action === 'REJECT' ? 'REJECTED' : 'RESOLVED';
      message = `Admin ${newStatus.toLowerCase()} exception for transaction ${id}.`;

      // Check if resolution record exists
      const existing = await db.query('SELECT * FROM exception_resolutions WHERE transaction_id = $1', [id]);
      if (existing.rows.length > 0) {
        await db.query(`
          UPDATE exception_resolutions SET
            status = $1,
            resolution_note = $2,
            resolved_by_user = $3,
            resolved_by_role = $4,
            created_at = NOW()
          WHERE transaction_id = $5
        `, [newStatus, resolution_note, user.user_id, user.role, id]);
      } else {
        await db.query(`
          INSERT INTO exception_resolutions (
            transaction_id, order_id, merchant_id, store_id, amount_inr,
            issue_description, resolution_note, resolved_by_role, resolved_by_user, status, created_at
          ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, NOW())
        `, [id, tx.order_id, tx.merchant_id, tx.store_id, tx.amount_inr, 'Admin manual exception resolution', resolution_note, user.role, user.user_id, newStatus]);
      }

      // Notify Store User
      await db.query(`
        INSERT INTO notifications (user_id, merchant_id, store_id, role, title, message)
        VALUES (NULL, $1, $2, 'MERCHANT', $3, $4)
      `, [tx.merchant_id, tx.store_id, `Exception ${newStatus}: ${id}`, resolution_note]);

      if (io) {
        io.to(`store_${tx.store_id}`).emit('exception_resolved', { transaction_id: id, status: newStatus, note: resolution_note });
        io.to('admin_room').emit('exception_resolved', { transaction_id: id, status: newStatus, note: resolution_note });
      }
    }

    await logAction(user.user_id, `Exception ${newStatus}`, `Transaction ${id}: ${resolution_note}`);
    await deleteCache(`metrics:${tx.merchant_id}:${tx.store_id}:all:all`);

    return res.json({
      success: true,
      message,
      status: newStatus
    });
  } catch (error) {
    next(error);
  }
}

module.exports = {
  getExceptions,
  resolveException
};
