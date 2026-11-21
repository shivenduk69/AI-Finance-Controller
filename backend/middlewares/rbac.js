function requireRole(...allowedRoles) {
  return (req, res, next) => {
    if (!req.user) {
      return res.status(401).json({ success: false, error: 'Authentication required' });
    }

    if (!allowedRoles.includes(req.user.role)) {
      return res.status(403).json({
        success: false,
        error: `Access denied. Requires role: ${allowedRoles.join(' or ')}.`
      });
    }

    next();
  };
}

function getTenantScope(req) {
  const user = req.user;
  if (!user) {
    return { merchantId: null, storeId: null, isAdmin: false };
  }

  if (user.role === 'ADMIN') {
    return {
      merchantId: req.query.merchant_id || null,
      storeId: req.query.store_id || null,
      isAdmin: true
    };
  }

  // MERCHANT role is strictly bound to user's assigned merchant and store
  return {
    merchantId: user.merchant_id,
    storeId: user.store_id,
    isAdmin: false
  };
}

module.exports = {
  requireRole,
  getTenantScope
};
