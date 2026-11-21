const Redis = require('ioredis');
const logger = require('./logger');

let redisClient = null;
let isRedisAvailable = false;

try {
  redisClient = new Redis({
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6380', 10),
    password: process.env.REDIS_PASSWORD || 'redis_secure_password',
    retryStrategy(times) {
      if (times > 5) {
        logger.warn('Redis reconnection limit reached. Falling back to direct database queries.');
        return null;
      }
      return Math.min(times * 1000, 3000);
    },
    lazyConnect: true,
  });

  redisClient.on('connect', () => {
    isRedisAvailable = true;
    logger.info('Redis client connected successfully');
  });

  redisClient.on('error', (err) => {
    isRedisAvailable = false;
    logger.warn(`Redis connection error: ${err.message}`);
  });
} catch (err) {
  logger.warn('Failed to initialize Redis client. Caching will be disabled.');
}

async function connectRedis() {
  if (redisClient && !isRedisAvailable) {
    try {
      await redisClient.connect();
    } catch (e) {
      logger.warn(`Redis initial connection failed: ${e.message}. Continuing without cache.`);
    }
  }
}

async function getCache(key) {
  if (!isRedisAvailable || !redisClient) return null;
  try {
    const data = await redisClient.get(key);
    return data ? JSON.parse(data) : null;
  } catch (err) {
    logger.warn(`Error reading from Redis key ${key}: ${err.message}`);
    return null;
  }
}

async function setCache(key, value, ttlSeconds = 60) {
  if (!isRedisAvailable || !redisClient) return false;
  try {
    const str = JSON.stringify(value);
    await redisClient.set(key, str, 'EX', ttlSeconds);
    return true;
  } catch (err) {
    logger.warn(`Error setting Redis key ${key}: ${err.message}`);
    return false;
  }
}

async function deleteCache(key) {
  if (!isRedisAvailable || !redisClient) return false;
  try {
    await redisClient.del(key);
    return true;
  } catch (err) {
    logger.warn(`Error deleting Redis key ${key}: ${err.message}`);
    return false;
  }
}

module.exports = {
  redisClient,
  connectRedis,
  getCache,
  setCache,
  deleteCache,
  isAvailable: () => isRedisAvailable
};
