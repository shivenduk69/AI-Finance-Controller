const express = require('express');
const router = express.Router();
const aiProxyController = require('../controllers/aiProxyController');
const { authenticate } = require('../middlewares/auth');

router.use(authenticate);

router.post('/chat', aiProxyController.chat);
router.get('/conversations', aiProxyController.getConversations);
router.get('/conversations/:id/messages', aiProxyController.getConversationMessages);
router.delete('/conversations/:id', aiProxyController.deleteConversation);

router.post('/tax-audit', aiProxyController.taxAudit);
router.get('/forecast', aiProxyController.cashForecast);

module.exports = router;
