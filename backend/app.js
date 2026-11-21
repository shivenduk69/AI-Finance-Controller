const express = require('express');
const helmet = require('helmet');
const cors = require('cors');
const cookieParser = require('cookie-parser');
const errorHandler = require('./middlewares/errorHandler');

// Route Imports
const authRoutes = require('./routes/authRoutes');
const reconciliationRoutes = require('./routes/reconciliationRoutes');
const exceptionRoutes = require('./routes/exceptionRoutes');
const ticketRoutes = require('./routes/ticketRoutes');
const notificationRoutes = require('./routes/notificationRoutes');
const adminRoutes = require('./routes/adminRoutes');
const aiRoutes = require('./routes/aiRoutes');

const app = express();

// 1. Security & Core Middleware
app.use(helmet({
  contentSecurityPolicy: false, // Allows flexible API & WebSocket access
}));

const allowedOrigins = (process.env.CORS_ORIGIN || 'http://localhost:3000,http://127.0.0.1:3000').split(',');
app.use(cors({
  origin: (origin, callback) => {
    if (!origin || allowedOrigins.includes(origin) || process.env.NODE_ENV === 'development') {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS policy'));
    }
  },
  credentials: true
}));

app.use(cookieParser());
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// 2. Health Check
app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'finance-backend',
    timestamp: new Date().toISOString()
  });
});

// 3. API Route Registrations
app.use('/api/auth', authRoutes);
app.use('/api/reconciliation', reconciliationRoutes);
app.use('/api/exceptions', exceptionRoutes);
app.use('/api/tickets', ticketRoutes);
app.use('/api/notifications', notificationRoutes);
app.use('/api/admin', adminRoutes);
app.use('/api/ai', aiRoutes);

// 4. Central Error Handler
app.use(errorHandler);

module.exports = app;
