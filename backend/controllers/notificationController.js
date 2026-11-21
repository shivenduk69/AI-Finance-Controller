const db = require('../config/db');

async function getNotifications(req, res, next) {
  try {
    const user = req.user;
    let query = 'SELECT * FROM notifications WHERE 1=1';
    const params = [];
    let pIdx = 1;

    if (user.role === 'ADMIN') {
      query += ` AND (role = 'ADMIN' OR user_id = $${pIdx++})`;
      params.push(user.user_id);
    } else {
      query += ` AND (role = 'MERCHANT' OR user_id = $${pIdx++})`;
      params.push(user.user_id);

      if (user.merchant_id) {
        query += ` AND (merchant_id IS NULL OR merchant_id = $${pIdx++})`;
        params.push(user.merchant_id);
      }
      if (user.store_id) {
        query += ` AND (store_id IS NULL OR store_id = $${pIdx++})`;
        params.push(user.store_id);
      }
    }

    query += ' ORDER BY created_at DESC LIMIT 50';
    const result = await db.query(query, params);

    const unreadCount = result.rows.filter(n => n.is_read === 0).length;

    return res.json({
      success: true,
      unreadCount,
      data: result.rows
    });
  } catch (error) {
    next(error);
  }
}

async function markAsRead(req, res, next) {
  try {
    const { id } = req.params;
    await db.query('UPDATE notifications SET is_read = 1 WHERE notification_id = $1', [id]);
    return res.json({ success: true, message: 'Notification marked as read' });
  } catch (error) {
    next(error);
  }
}

async function markAllAsRead(req, res, next) {
  try {
    const user = req.user;
    if (user.role === 'ADMIN') {
      await db.query("UPDATE notifications SET is_read = 1 WHERE role = 'ADMIN' OR user_id = $1", [user.user_id]);
    } else {
      await db.query(
        "UPDATE notifications SET is_read = 1 WHERE (role = 'MERCHANT' OR user_id = $1) AND (merchant_id = $2 OR merchant_id IS NULL)",
        [user.user_id, user.merchant_id]
      );
    }
    return res.json({ success: true, message: 'All notifications marked as read' });
  } catch (error) {
    next(error);
  }
}

module.exports = {
  getNotifications,
  markAsRead,
  markAllAsRead
};
