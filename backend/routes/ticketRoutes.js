const express = require('express');
const router = express.Router();
const ticketController = require('../controllers/ticketController');
const { authenticate } = require('../middlewares/auth');
const { requireRole } = require('../middlewares/rbac');

router.use(authenticate);

router.get('/', ticketController.getTickets);
router.post('/', ticketController.createTicket);
router.put('/:id/resolve', requireRole('ADMIN'), ticketController.resolveTicket);

module.exports = router;
