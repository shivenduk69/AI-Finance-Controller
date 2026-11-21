require('dotenv').config();
const request = require('supertest');
const app = require('../app');
const { pool } = require('../config/db');
const { connectRedis, redisClient } = require('../config/redis');

describe('Backend API Integration Tests', () => {
  let adminToken = '';
  let merchantToken = '';
  let testTxId = '';

  beforeAll(async () => {
    await connectRedis();
    const res = await pool.query("SELECT transaction_id FROM transactions WHERE merchant_id = 'flipkart' AND store_id = 'fk_delhi' LIMIT 1");
    if (res.rows.length > 0) {
      testTxId = res.rows[0].transaction_id;
    }
  });

  afterAll(async () => {
    await pool.end();
    if (redisClient) {
      redisClient.disconnect();
    }
  });

  describe('Healthcheck Endpoint', () => {
    it('GET /api/health returns 200 and healthy status', async () => {
      const res = await request(app).get('/api/health');
      expect(res.statusCode).toBe(200);
      expect(res.body.status).toBe('healthy');
      expect(res.body.service).toBe('finance-backend');
    });
  });

  describe('Authentication & RBAC', () => {
    it('POST /api/auth/login fails with invalid credentials', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'admin@razorpay-demo.com', password: 'wrongpassword' });

      expect(res.statusCode).toBe(401);
      expect(res.body.success).toBe(false);
    });

    it('POST /api/auth/login succeeds for Admin with Argon2id hash', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'admin@razorpay-demo.com', password: 'admin123' });

      expect(res.statusCode).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.user.role).toBe('ADMIN');
      expect(res.body.token).toBeDefined();
      adminToken = res.body.token;
    });

    it('POST /api/auth/login succeeds for Merchant Store Manager', async () => {
      const res = await request(app)
        .post('/api/auth/login')
        .send({ email: 'flipkart.delhi@merchant-demo.com', password: 'flipkart123' });

      expect(res.statusCode).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.user.role).toBe('MERCHANT');
      expect(res.body.user.merchant_id).toBe('flipkart');
      expect(res.body.user.store_id).toBe('fk_delhi');
      merchantToken = res.body.token;
    });

    it('RBAC blocks Merchant from accessing /api/admin/metrics (403 Forbidden)', async () => {
      const res = await request(app)
        .get('/api/admin/metrics')
        .set('Authorization', `Bearer ${merchantToken}`);

      expect(res.statusCode).toBe(403);
      expect(res.body.success).toBe(false);
    });

    it('RBAC permits Admin to access /api/admin/metrics (200 OK)', async () => {
      const res = await request(app)
        .get('/api/admin/metrics')
        .set('Authorization', `Bearer ${adminToken}`);

      expect(res.statusCode).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.data.total_merchants).toBeDefined();
      expect(res.body.data.active_stores).toBeDefined();
    });
  });

  describe('Reconciliation & Transactions Ledger', () => {
    it('GET /api/reconciliation/summary returns calculated metrics', async () => {
      const res = await request(app)
        .get('/api/reconciliation/summary')
        .set('Authorization', `Bearer ${merchantToken}`);

      expect(res.statusCode).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.data.total_transactions).toBeGreaterThan(0);
      expect(res.body.data.auto_match_accuracy_pct).toBeDefined();
    });

    it('GET /api/reconciliation/transactions returns paginated records', async () => {
      const res = await request(app)
        .get('/api/reconciliation/transactions?page=1&limit=10')
        .set('Authorization', `Bearer ${merchantToken}`);

      expect(res.statusCode).toBe(200);
      expect(res.body.success).toBe(true);
      expect(Array.isArray(res.body.data)).toBe(true);
      expect(res.body.pagination).toBeDefined();
    });
  });

  describe('Exceptions Queue & Notifications', () => {
    it('GET /api/exceptions returns active exceptions', async () => {
      const res = await request(app)
        .get('/api/exceptions?tab=active')
        .set('Authorization', `Bearer ${merchantToken}`);

      expect(res.statusCode).toBe(200);
      expect(res.body.success).toBe(true);
      expect(Array.isArray(res.body.data)).toBe(true);
    });

    it('GET /api/notifications returns user notification stream', async () => {
      const res = await request(app)
        .get('/api/notifications')
        .set('Authorization', `Bearer ${merchantToken}`);

      expect(res.statusCode).toBe(200);
      expect(res.body.success).toBe(true);
      expect(Array.isArray(res.body.data)).toBe(true);
    });
  });

  describe('Phase 6 Integration: Redis Caching & Invalidation', () => {
    it('Caches summary metrics in Redis on subsequent requests', async () => {
      // First request (potential cache miss or fresh)
      const res1 = await request(app)
        .get('/api/reconciliation/summary')
        .set('Authorization', `Bearer ${merchantToken}`);
      expect(res1.statusCode).toBe(200);

      // Second request (guaranteed cache hit from Redis)
      const res2 = await request(app)
        .get('/api/reconciliation/summary')
        .set('Authorization', `Bearer ${merchantToken}`);
      expect(res2.statusCode).toBe(200);
      expect(res2.body.cached).toBe(true);
      expect(res2.body.data.total_transactions).toBe(res1.body.data.total_transactions);
    });
  });

  describe('Phase 6 Integration: Multi-Tenant Data Isolation', () => {
    it('Strictly scopes Merchant results to their own store_id and merchant_id', async () => {
      const resMerchant = await request(app)
        .get('/api/reconciliation/transactions?limit=100')
        .set('Authorization', `Bearer ${merchantToken}`);

      expect(resMerchant.statusCode).toBe(200);
      for (const tx of resMerchant.body.data) {
        expect(tx.merchant_id).toBe('flipkart');
        expect(tx.store_id).toBe('fk_delhi');
      }

      // Admin query returns global transactions across all stores
      const resAdmin = await request(app)
        .get('/api/reconciliation/transactions?limit=100')
        .set('Authorization', `Bearer ${adminToken}`);

      expect(resAdmin.statusCode).toBe(200);
      expect(resAdmin.body.data.length).toBeGreaterThan(resMerchant.body.data.length);
    });
  });

  describe('Phase 6 Integration: Exception Resolution Lifecycle & Real-Time Sync', () => {
    it('Merchant submits resolution note -> Status moves to PENDING_ADMIN', async () => {
      const res = await request(app)
        .post(`/api/exceptions/${testTxId}/resolve`)
        .set('Authorization', `Bearer ${merchantToken}`)
        .send({
          action: 'SUBMIT',
          resolution_note: 'Merchant submitted proof of physical delivery'
        });

      expect(res.statusCode).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.status).toBe('PENDING_ADMIN');
    });

    it('Admin reviews and approves exception -> Status moves to RESOLVED', async () => {
      const res = await request(app)
        .post(`/api/exceptions/${testTxId}/resolve`)
        .set('Authorization', `Bearer ${adminToken}`)
        .send({
          action: 'RESOLVE',
          resolution_note: 'Admin verified courier receipt. Discrepancy cleared.'
        });

      expect(res.statusCode).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.status).toBe('RESOLVED');
    });
  });

  describe('Phase 6 Integration: RabbitMQ Asynchronous Event Bus', () => {
    const { connectRabbitMQ, publishReconciliationJob, publishIngestionJob, closeRabbitMQ } = require('../config/rabbitmq');

    it('Connects to RabbitMQ and publishes reconciliation batch job', async () => {
      const connected = await connectRabbitMQ();
      expect(connected).toBe(true);

      const published = await publishReconciliationJob({
        jobId: 'test_reconciliation_batch_001',
        merchant_id: 'flipkart',
        store_id: 'fk_delhi'
      });
      expect(published).toBe(true);

      const ingPublished = await publishIngestionJob({
        jobId: 'test_csv_ingestion_001',
        reset: false
      });
      expect(ingPublished).toBe(true);

      await closeRabbitMQ();
    });
  });
});
