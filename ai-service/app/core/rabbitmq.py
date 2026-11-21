import os
import json
import logging
import threading
import pika
from app.core.config import settings

logger = logging.getLogger("ai_service.rabbitmq")

EXCHANGE_NAME = "finance_events"
RECONCILIATION_QUEUE = "reconciliation_batch_queue"
INGESTION_QUEUE = "csv_ingestion_queue"

class RabbitMQWorker:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.is_connected = False
        self.worker_thread = None
        self.stop_requested = False

    def connect(self):
        try:
            params = pika.URLParameters(settings.RABBITMQ_URL)
            params.socket_timeout = 5
            self.connection = pika.BlockingConnection(params)
            self.channel = self.connection.channel()

            self.channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='direct', durable=True)
            self.channel.queue_declare(queue=RECONCILIATION_QUEUE, durable=True)
            self.channel.queue_declare(queue=INGESTION_QUEUE, durable=True)

            self.channel.queue_bind(queue=RECONCILIATION_QUEUE, exchange=EXCHANGE_NAME, routing_key='reconciliation.job')
            self.channel.queue_bind(queue=INGESTION_QUEUE, exchange=EXCHANGE_NAME, routing_key='ingestion.job')

            self.is_connected = True
            logger.info("RabbitMQ worker successfully connected and subscribed to queues.")
            return True
        except Exception as e:
            self.is_connected = False
            logger.warning(f"RabbitMQ connection failed: {e}. Worker will not process async messages.")
            return False

    def start_consumer_thread(self):
        if not self.connect():
            return
        
        self.worker_thread = threading.Thread(target=self._consume_loop, daemon=True)
        self.worker_thread.start()
        logger.info("RabbitMQ background consumer thread started.")

    def _consume_loop(self):
        try:
            def on_reconciliation_message(ch, method, properties, body):
                try:
                    payload = json.loads(body.decode())
                    logger.info(f"Processing asynchronous reconciliation message: {payload.get('jobId', 'unnamed')}")
                    from app.reconciliation.engine import run_3way_reconciliation
                    merchant_id = payload.get("merchant_id")
                    store_id = payload.get("store_id")
                    run_3way_reconciliation(merchant_id=merchant_id, store_id=store_id)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info(f"Successfully processed and acknowledged reconciliation job.")
                except Exception as ex:
                    logger.error(f"Error handling reconciliation queue message: {ex}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            def on_ingestion_message(ch, method, properties, body):
                try:
                    payload = json.loads(body.decode())
                    logger.info(f"Processing asynchronous CSV ingestion message: {payload.get('jobId', 'unnamed')}")
                    from app.ingestion.pipeline import run_ingestion_pipeline
                    run_ingestion_pipeline(reset=payload.get("reset", False))
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info("Successfully processed and acknowledged CSV ingestion job.")
                except Exception as ex:
                    logger.error(f"Error handling CSV ingestion queue message: {ex}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            self.channel.basic_consume(queue=RECONCILIATION_QUEUE, on_message_callback=on_reconciliation_message)
            self.channel.basic_consume(queue=INGESTION_QUEUE, on_message_callback=on_ingestion_message)
            self.channel.start_consuming()
        except Exception as e:
            logger.warning(f"RabbitMQ consumer loop terminated: {e}")
            self.is_connected = False

    def publish_job(self, routing_key, job_data):
        if not self.is_connected or not self.channel:
            if not self.connect():
                return False
        try:
            body = json.dumps(job_data)
            self.channel.basic_publish(
                exchange=EXCHANGE_NAME,
                routing_key=routing_key,
                body=body.encode(),
                properties=pika.BasicProperties(delivery_mode=2)
            )
            return True
        except Exception as e:
            logger.error(f"Failed to publish RabbitMQ message: {e}")
            return False

    def close(self):
        try:
            self.stop_requested = True
            if self.channel and self.channel.is_open:
                self.channel.stop_consuming()
                self.channel.close()
            if self.connection and self.connection.is_open:
                self.connection.close()
            logger.info("RabbitMQ worker connection stopped.")
        except Exception as e:
            logger.warning(f"Error closing RabbitMQ connection: {e}")

rabbitmq_worker = RabbitMQWorker()
