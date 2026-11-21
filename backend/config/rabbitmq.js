const amqp = require('amqplib');
const logger = require('./logger');

let connection = null;
let channel = null;
let isRabbitAvailable = false;

const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://finance_admin:rabbitmq_secure_password@localhost:5672';
const EXCHANGE_NAME = 'finance_events';
const RECONCILIATION_QUEUE = 'reconciliation_batch_queue';
const INGESTION_QUEUE = 'csv_ingestion_queue';

async function connectRabbitMQ() {
  try {
    connection = await amqp.connect(RABBITMQ_URL);
    channel = await connection.createChannel();

    // Setup exchange and queues
    await channel.assertExchange(EXCHANGE_NAME, 'direct', { durable: true });
    await channel.assertQueue(RECONCILIATION_QUEUE, { durable: true });
    await channel.assertQueue(INGESTION_QUEUE, { durable: true });

    await channel.bindQueue(RECONCILIATION_QUEUE, EXCHANGE_NAME, 'reconciliation.job');
    await channel.bindQueue(INGESTION_QUEUE, EXCHANGE_NAME, 'ingestion.job');

    isRabbitAvailable = true;
    logger.info('RabbitMQ connected and message queues verified successfully');

    connection.on('error', (err) => {
      isRabbitAvailable = false;
      logger.warn(`RabbitMQ connection error: ${err.message}`);
    });

    connection.on('close', () => {
      isRabbitAvailable = false;
      logger.warn('RabbitMQ connection closed. Asynchronous queue fallback active.');
    });

    return true;
  } catch (err) {
    isRabbitAvailable = false;
    logger.warn(`Failed to connect to RabbitMQ: ${err.message}. Running in direct mode.`);
    return false;
  }
}

async function publishReconciliationJob(jobData) {
  if (!isRabbitAvailable || !channel) {
    logger.warn('RabbitMQ not available; processing job synchronously.');
    return false;
  }
  try {
    const payload = Buffer.from(JSON.stringify(jobData));
    channel.publish(EXCHANGE_NAME, 'reconciliation.job', payload, { persistent: true });
    logger.info(`Dispatched reconciliation job to RabbitMQ: ${jobData.jobId || 'job'}`);
    return true;
  } catch (err) {
    logger.error(`Error publishing to RabbitMQ: ${err.message}`);
    return false;
  }
}

async function publishIngestionJob(jobData) {
  if (!isRabbitAvailable || !channel) {
    logger.warn('RabbitMQ not available; processing ingestion synchronously.');
    return false;
  }
  try {
    const payload = Buffer.from(JSON.stringify(jobData));
    channel.publish(EXCHANGE_NAME, 'ingestion.job', payload, { persistent: true });
    logger.info(`Dispatched CSV ingestion job to RabbitMQ: ${jobData.jobId || 'job'}`);
    return true;
  } catch (err) {
    logger.error(`Error publishing ingestion job: ${err.message}`);
    return false;
  }
}

async function closeRabbitMQ() {
  try {
    if (channel) await channel.close();
    if (connection) await connection.close();
    isRabbitAvailable = false;
    logger.info('RabbitMQ connection closed cleanly.');
  } catch (e) {
    logger.warn(`RabbitMQ shutdown error: ${e.message}`);
  }
}

module.exports = {
  connectRabbitMQ,
  publishReconciliationJob,
  publishIngestionJob,
  closeRabbitMQ,
  isAvailable: () => isRabbitAvailable,
  EXCHANGE_NAME,
  RECONCILIATION_QUEUE,
  INGESTION_QUEUE
};
