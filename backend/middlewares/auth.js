const jwt = require('jsonwebtoken');

const JWT_SECRET = process.env.JWT_SECRET || 'finance_controller_jwt_super_secret_key_production_grade_2026';

function authenticate(req, res, next) {
  let token = null;

  // 1. Check HttpOnly cookie
  if (req.cookies && req.cookies.token) {
    token = req.cookies.token;
  }

  // 2. Fall back to Authorization: Bearer header
  if (!token && req.headers.authorization && req.headers.authorization.startsWith('Bearer ')) {
    token = req.headers.authorization.split(' ')[1];
  }

  if (!token) {
    return res.status(401).json({
      success: false,
      error: 'Authentication required. No session token provided.'
    });
  }

  try {
    const decoded = jwt.verify(token, JWT_SECRET);
    req.user = decoded;
    next();
  } catch (err) {
    return res.status(401).json({
      success: false,
      error: 'Invalid or expired session token. Please sign in again.'
    });
  }
}

module.exports = {
  authenticate
};
