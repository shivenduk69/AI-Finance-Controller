const express = require('express');
const router = express.Router();
const reconciliationController = require('../controllers/reconciliationController');
const { authenticate } = require('../middlewares/auth');

router.use(authenticate);

router.get('/summary', reconciliationController.getSummaryMetrics);
router.get('/transactions', reconciliationController.getTransactions);
router.get('/transactions/:id/audit', reconciliationController.getTransactionAudit);

module.exports = router;
