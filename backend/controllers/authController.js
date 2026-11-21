const argon2 = require('argon2');
const jwt = require('jsonwebtoken');
const db = require('../config/db');
const { logAction } = require('../utils/auditLogger');
const logger = require('../config/logger');

const JWT_SECRET = process.env.JWT_SECRET || 'finance_controller_jwt_super_secret_key_production_grade_2026';
const JWT_EXPIRES_IN = process.env.JWT_EXPIRES_IN || '7d';

async function login(req, res, next) {
  try {
    const { email, password } = req.body;
    if (!email || !password) {
      return res.status(400).json({ success: false, error: 'Email and password are required' });
    }

    const cleanEmail = email.trim().toLowerCase();
    const result = await db.query('SELECT * FROM users WHERE LOWER(email) = $1', [cleanEmail]);

    if (result.rows.length === 0) {
      return res.status(401).json({ success: false, error: 'Invalid corporate email or password' });
    }

    const user = result.rows[0];
    let passwordMatch = false;

    // Verify Argon2id password hash
    if (user.password_hash.startsWith('$argon2')) {
      try {
        passwordMatch = await argon2.verify(user.password_hash, password);
      } catch (e) {
        logger.error(`Argon2 verification error: ${e.message}`);
      }
    } else if (user.password_hash.includes(':')) {
      // Legacy salt:sha256 fallback verification
      const crypto = require('crypto');
      const [salt, hash] = user.password_hash.split(':');
      const computed = crypto.createHash('sha256').update(password + salt).digest('hex');
      passwordMatch = (computed === hash);
    } else {
      // Plaintext fallback
      passwordMatch = (user.password_hash === password);
    }

    if (!passwordMatch) {
      return res.status(401).json({ success: false, error: 'Invalid corporate email or password' });
    }

    // Generate JWT
    const tokenPayload = {
      user_id: user.user_id,
      email: user.email,
      role: user.role,
      merchant_id: user.merchant_id,
      store_id: user.store_id
    };

    const token = jwt.sign(tokenPayload, JWT_SECRET, { expiresIn: JWT_EXPIRES_IN });

    // Set secure cookie
    res.cookie('token', token, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax',
      maxAge: 7 * 24 * 60 * 60 * 1000 // 7 days
    });

    await logAction(user.user_id, 'User Login', `Role: ${user.role}, Merchant: ${user.merchant_id || 'N/A'}, Store: ${user.store_id || 'N/A'}`);

    return res.json({
      success: true,
      data: { user: tokenPayload, token },
      user: tokenPayload,
      token
    });
  } catch (error) {
    next(error);
  }
}

async function logout(req, res, next) {
  try {
    if (req.user) {
      await logAction(req.user.user_id, 'User Logout', 'Session terminated by user.');
    }
    res.clearCookie('token');
    return res.json({ success: true, message: 'Signed out successfully' });
  } catch (error) {
    next(error);
  }
}

async function me(req, res, next) {
  try {
    const result = await db.query(
      'SELECT user_id, email, role, merchant_id, store_id, created_at FROM users WHERE user_id = $1',
      [req.user.user_id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ success: false, error: 'User profile not found' });
    }

    return res.json({ success: true, data: result.rows[0], user: result.rows[0] });
  } catch (error) {
    next(error);
  }
}

async function changePassword(req, res, next) {
  try {
    const { currentPassword, newPassword } = req.body;
    if (!currentPassword || !newPassword) {
      return res.status(400).json({ success: false, error: 'Current and new password are required' });
    }

    if (newPassword.length < 6) {
      return res.status(400).json({ success: false, error: 'New password must be at least 6 characters' });
    }

    const result = await db.query('SELECT password_hash FROM users WHERE user_id = $1', [req.user.user_id]);
    const user = result.rows[0];

    const match = await argon2.verify(user.password_hash, currentPassword);
    if (!match) {
      return res.status(400).json({ success: false, error: 'Current password is incorrect' });
    }

    const newHash = await argon2.hash(newPassword);
    await db.query('UPDATE users SET password_hash = $1 WHERE user_id = $2', [newHash, req.user.user_id]);
    await logAction(req.user.user_id, 'Password Changed', 'User changed their corporate password.');

    return res.json({ success: true, message: 'Password updated successfully' });
  } catch (error) {
    next(error);
  }
}

module.exports = {
  login,
  logout,
  me,
  changePassword
};
