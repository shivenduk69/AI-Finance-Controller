const logger = require('../config/logger');

function errorHandler(err, req, res, next) {
  const status = err.status || err.statusCode || 500;
  const message = err.message || 'Internal Server Error';

  logger.error(`Error processing ${req.method} ${req.originalUrl}: ${message}`, {
    stack: err.stack,
    body: req.body,
    query: req.query,
    user: req.user ? req.user.user_id : 'anonymous'
  });

  res.status(status).json({
    success: false,
    error: message,
    ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
  });
}

module.exports = errorHandler;
