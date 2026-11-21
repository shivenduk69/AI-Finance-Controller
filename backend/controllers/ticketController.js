const db = require('../config/db');
const { getTenantScope } = require('../middlewares/rbac');
const { logAction } = require('../utils/auditLogger');
const { getIO } = require('../sockets/socketHandler');

async function getTickets(req, res, next) {
  try {
    const { merchantId, storeId, isAdmin } = getTenantScope(req);
    const { status } = req.query;

    let query = `
      SELECT 
        ticket_id, transaction_id, merchant_name, subject, message,
        status, resolution_comments, timestamp, merchant_id, store_id,
        user_id, category, priority
      FROM support_tickets
      WHERE 1=1
    `;
    const params = [];
    let pIdx = 1;

    if (merchantId) {
      query += ` AND merchant_id = $${pIdx++}`;
      params.push(merchantId);
    }
    if (storeId) {
      query += ` AND store_id = $${pIdx++}`;
      params.push(storeId);
    }
    if (status && status !== 'All') {
      query += ` AND status = $${pIdx++}`;
      params.push(status);
    }

    query += ' ORDER BY timestamp DESC';
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

async function createTicket(req, res, next) {
  try {
    const { transaction_id, subject, message, category, priority } = req.body;
    const user = req.user;

    if (!subject || !message) {
      return res.status(400).json({ success: false, error: 'Subject and message description are required' });
    }

    const merchantName = user.merchant_id ? user.merchant_id.charAt(0).toUpperCase() + user.merchant_id.slice(1) : 'Merchant';

    const insertQ = `
      INSERT INTO support_tickets (
        transaction_id, merchant_name, subject, message, status,
        merchant_id, store_id, user_id, category, priority, timestamp
      ) VALUES ($1, $2, $3, $4, 'OPEN', $5, $6, $7, $8, $9, NOW())
      RETURNING *
    `;
    const result = await db.query(insertQ, [
      transaction_id || null,
      merchantName,
      subject.trim(),
      message.trim(),
      user.merchant_id || null,
      user.store_id || null,
      user.user_id,
      category || 'General Operations',
      priority || 'Medium'
    ]);

    const ticket = result.rows[0];

    // Create notification for Admin
    await db.query(`
      INSERT INTO notifications (user_id, merchant_id, store_id, role, title, message)
      VALUES (NULL, $1, $2, 'ADMIN', $3, $4)
    `, [user.merchant_id, user.store_id, `New Ticket #${ticket.ticket_id}: ${subject}`, message]);

    const io = getIO();
    if (io) {
      io.to('admin_room').emit('notification_dispatched', {
        title: `New Ticket #${ticket.ticket_id}`,
        message: subject,
        role: 'ADMIN'
      });
    }

    await logAction(user.user_id, 'Ticket Raised', `Ticket #${ticket.ticket_id}: ${subject}`);

    return res.status(201).json({
      success: true,
      data: ticket,
      message: 'Support ticket raised successfully.'
    });
  } catch (error) {
    next(error);
  }
}

async function resolveTicket(req, res, next) {
  try {
    const { id } = req.params;
    const { resolution_comments, status = 'RESOLVED' } = req.body;
    const user = req.user;

    const findQ = 'SELECT * FROM support_tickets WHERE ticket_id = $1';
    const findRes = await db.query(findQ, [id]);
    if (findRes.rows.length === 0) {
      return res.status(404).json({ success: false, error: 'Ticket not found' });
    }
    const ticket = findRes.rows[0];

    const updateQ = `
      UPDATE support_tickets SET
        status = $1,
        resolution_comments = $2
      WHERE ticket_id = $3
      RETURNING *
    `;
    const result = await db.query(updateQ, [status, resolution_comments || 'Resolved by Razorpay Admin', id]);
    const updated = result.rows[0];

    // Notify the Store User
    if (ticket.store_id) {
      await db.query(`
        INSERT INTO notifications (user_id, merchant_id, store_id, role, title, message)
        VALUES (NULL, $1, $2, 'MERCHANT', $3, $4)
      `, [ticket.merchant_id, ticket.store_id, `Ticket #${id} ${status}`, resolution_comments || 'Ticket updated by Admin']);

      const io = getIO();
      if (io) {
        io.to(`store_${ticket.store_id}`).emit('notification_dispatched', {
          title: `Ticket #${id} ${status}`,
          message: resolution_comments,
          role: 'MERCHANT'
        });
      }
    }

    await logAction(user.user_id, `Ticket ${status}`, `Ticket #${id} resolved.`);

    return res.json({
      success: true,
      data: updated,
      message: `Ticket #${id} marked as ${status}.`
    });
  } catch (error) {
    next(error);
  }
}

module.exports = {
  getTickets,
  createTicket,
  resolveTicket
};
