const express = require('express');
const router = express.Router();
const exceptionController = require('../controllers/exceptionController');
const { authenticate } = require('../middlewares/auth');

router.use(authenticate);

router.get('/', exceptionController.getExceptions);
router.post('/:id/resolve', exceptionController.resolveException);

module.exports = router;
