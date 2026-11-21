require('dotenv').config();
const http = require('http');
const app = require('./app');
const { testConnection, pool } = require('./config/db');
const { connectRedis, redisClient } = require('./config/redis');
const { connectRabbitMQ, closeRabbitMQ } = require('./config/rabbitmq');
const { initSocket } = require('./sockets/socketHandler');
const logger = require('./config/logger');

const PORT = parseInt(process.env.PORT || '5000', 10);
const server = http.createServer(app);

// Initialize Socket.IO
const allowedOrigins = (process.env.CORS_ORIGIN || 'http://localhost:3000,http://127.0.0.1:3000').split(',');
initSocket(server, allowedOrigins);

async function startServer() {
  try {
    // 1. Verify Database Connection
    const dbOk = await testConnection();
    if (!dbOk) {
      logger.warn('Initial PostgreSQL connection check failed. Will retry on request.');
    }

    // 2. Connect Redis (Graceful failure handled internally)
    await connectRedis();

    // 3. Connect RabbitMQ Event Bus
    await connectRabbitMQ();

    // 4. Start Listening
    server.listen(PORT, '0.0.0.0', () => {
      logger.info(`Finance Backend Service listening on port ${PORT} (Environment: ${process.env.NODE_ENV || 'development'})`);
      logger.info(`Health check available at http://localhost:${PORT}/api/health`);
    });
  } catch (error) {
    logger.error('Failed to start server:', error);
    process.exit(1);
  }
}

// Graceful Shutdown Handlers
async function shutdown(signal) {
  logger.info(`Received ${signal}. Shutting down gracefully...`);
  server.close(async () => {
    logger.info('HTTP server closed.');
    try {
      await pool.end();
      logger.info('PostgreSQL pool drained.');
      if (redisClient) {
        redisClient.disconnect();
        logger.info('Redis connection closed.');
      }
      await closeRabbitMQ();
    } catch (e) {
      logger.error('Error during shutdown:', e);
    }
    process.exit(0);
  });
}

process.on('SIGTERM', () => shutdown('SIGTERM'));
process.on('SIGINT', () => shutdown('SIGINT'));

startServer();
