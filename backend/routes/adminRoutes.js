const express = require('express');
const router = express.Router();
const adminController = require('../controllers/adminController');
const { authenticate } = require('../middlewares/auth');
const { requireRole } = require('../middlewares/rbac');

// All admin routes strictly enforce ADMIN role
router.use(authenticate);
router.use(requireRole('ADMIN'));

router.get('/metrics', adminController.getPlatformMetrics);

router.get('/merchants', adminController.getMerchants);
router.post('/merchants', adminController.createMerchant);

router.get('/stores', adminController.getStores);
router.post('/stores', adminController.createStore);

router.get('/users', adminController.getUsers);
router.post('/users', adminController.createUser);

router.get('/audit-logs', adminController.getAuditLogs);

router.get('/config', adminController.getConfig);
router.put('/config', adminController.updateConfig);

module.exports = router;
