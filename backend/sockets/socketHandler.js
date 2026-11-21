const { Server } = require('socket.io');
const jwt = require('jsonwebtoken');
const logger = require('../config/logger');

let io = null;
const JWT_SECRET = process.env.JWT_SECRET || 'finance_controller_jwt_super_secret_key_production_grade_2026';

function initSocket(server, allowedOrigins = []) {
  io = new Server(server, {
    cors: {
      origin: allowedOrigins,
      credentials: true
    }
  });

  // Socket authentication middleware
  io.use((socket, next) => {
    let token = socket.handshake.auth?.token || socket.handshake.query?.token;

    // Check cookies from handshake headers
    if (!token && socket.handshake.headers?.cookie) {
      const cookieHeader = socket.handshake.headers.cookie;
      const parts = cookieHeader.split(';');
      for (const part of parts) {
        const [k, v] = part.trim().split('=');
        if (k === 'token' && v) {
          token = decodeURIComponent(v);
          break;
        }
      }
    }

    if (!token) {
      return next(new Error('Authentication token required for WebSocket'));
    }

    try {
      const decoded = jwt.verify(token, JWT_SECRET);
      socket.user = decoded;
      next();
    } catch (err) {
      next(new Error('Invalid WebSocket token'));
    }
  });

  io.on('connection', (socket) => {
    const user = socket.user;
    logger.info(`WebSocket client connected: ${user.email} (${socket.id})`);

    // Join user-specific room
    socket.join(`user_${user.user_id}`);

    // Join role-specific rooms
    if (user.role === 'ADMIN') {
      socket.join('admin_room');
      logger.info(`User ${user.email} joined admin_room`);
    } else if (user.role === 'MERCHANT' && user.store_id) {
      socket.join(`store_${user.store_id}`);
      logger.info(`User ${user.email} joined store_${user.store_id}`);
    }

    socket.on('disconnect', () => {
      logger.info(`WebSocket client disconnected: ${socket.id}`);
    });
  });

  return io;
}

function getIO() {
  return io;
}

module.exports = {
  initSocket,
  getIO
};
