const db = require('../config/db');
const { getTenantScope } = require('../middlewares/rbac');
const { getCache, setCache } = require('../config/redis');
const logger = require('../config/logger');

async function getSummaryMetrics(req, res, next) {
  try {
    const { merchantId, storeId } = getTenantScope(req);
    const { start_date, end_date } = req.query;

    const cacheKey = `metrics:${merchantId || 'all'}:${storeId || 'all'}:${start_date || 'all'}:${end_date || 'all'}`;
    const cachedData = await getCache(cacheKey);
    if (cachedData) {
      return res.json({ success: true, data: cachedData, cached: true });
    }

    // Build SQL query conditions based on tenant scoping
    let whereClause = 'WHERE 1=1';
    const params = [];
    let paramIndex = 1;

    if (merchantId) {
      whereClause += ` AND merchant_id = $${paramIndex++}`;
      params.push(merchantId);
    }
    if (storeId) {
      whereClause += ` AND store_id = $${paramIndex++}`;
      params.push(storeId);
    }

    // Transactions Aggregations
    const txQuery = `
      SELECT 
        COUNT(*) as total_transactions,
        COUNT(*) FILTER (WHERE type = 'PAYMENT') as total_payments_processed,
        COALESCE(SUM(amount_inr) FILTER (WHERE type = 'PAYMENT' AND status = 'captured'), 0) as gross_collections_inr,
        COALESCE(SUM(amount_inr) FILTER (WHERE type = 'REFUND'), 0) as refunds_inr,
        COALESCE(SUM(fee_inr + tax_inr), 0) as fees_gst_inr,
        COUNT(*) FILTER (WHERE exception_flag = 'NO' OR exception_flag IS NULL) as auto_resolved_tx,
        COUNT(*) FILTER (WHERE exception_flag = 'YES') as needs_review_tx
      FROM transactions
      ${whereClause}
    `;
    const txResult = await db.query(txQuery, params);
    const txRow = txResult.rows[0] || {};

    // Internal Orders Aggregation
    const ordersQuery = `
      SELECT 
        COUNT(*) FILTER (WHERE status = 'completed') as total_orders
      FROM internal_orders
      ${whereClause}
    `;
    const ordersResult = await db.query(ordersQuery, params);
    const ordersRow = ordersResult.rows[0] || {};

    // Bank Statements Aggregation
    const bankQuery = `
      SELECT 
        COALESCE(SUM(amount_inr), 0) as settled_to_bank_inr
      FROM bank_statements
      ${whereClause}
    `;
    const bankResult = await db.query(bankQuery, params);
    const bankRow = bankResult.rows[0] || {};

    // Expected next 2 days calculation (pending captured settlements)
    const pendingQuery = `
      SELECT COALESCE(SUM(settled_amount_inr), 0) as expected_next_2_days_inr
      FROM transactions
      ${whereClause} AND type = 'PAYMENT' AND status = 'captured'
      AND expected_settlement_date >= TO_CHAR(NOW(), 'DD-MM-YYYY')
    `;
    const pendingResult = await db.query(pendingQuery, params);
    const pendingRow = pendingResult.rows[0] || {};

    // Resolved exceptions from exception_resolutions table
    let resClause = 'WHERE status = $1';
    const resParams = ['RESOLVED'];
    let rIdx = 2;
    if (merchantId) {
      resClause += ` AND merchant_id = $${rIdx++}`;
      resParams.push(merchantId);
    }
    if (storeId) {
      resClause += ` AND store_id = $${rIdx++}`;
      resParams.push(storeId);
    }
    const resolvedResult = await db.query(`SELECT COUNT(*) as count FROM exception_resolutions ${resClause}`, resParams);
    const resolvedCount = parseInt(resolvedResult.rows[0].count, 10) || 0;

    const totalTx = parseInt(txRow.total_transactions, 10) || 0;
    const baseReview = parseInt(txRow.needs_review_tx, 10) || 0;
    const activeNeedsReview = Math.max(0, baseReview - resolvedCount);
    const autoResolved = Math.min(totalTx, (parseInt(txRow.auto_resolved_tx, 10) || 0) + resolvedCount);
    const autoMatchAccuracy = totalTx > 0 ? Number(((autoResolved / totalTx) * 100).toFixed(1)) : 100.0;

    const summaryMetrics = {
      total_payments_processed: parseInt(txRow.total_payments_processed, 10) || 0,
      total_transactions: totalTx,
      auto_resolved_count: autoResolved,
      needs_review_count: activeNeedsReview,
      auto_match_accuracy_pct: autoMatchAccuracy,
      gross_collections_inr: parseFloat(txRow.gross_collections_inr) || 0.0,
      refunds_inr: parseFloat(txRow.refunds_inr) || 0.0,
      fees_gst_inr: parseFloat(txRow.fees_gst_inr) || 0.0,
      settled_to_bank_inr: parseFloat(bankRow.settled_to_bank_inr) || 0.0,
      expected_next_2_days_inr: parseFloat(pendingRow.expected_next_2_days_inr) || 0.0,
      unreconciled_review_inr: 0.0
    };

    await setCache(cacheKey, summaryMetrics, 60);

    return res.json({ success: true, data: summaryMetrics, cached: false });
  } catch (error) {
    next(error);
  }
}

async function getTransactions(req, res, next) {
  try {
    const { merchantId, storeId } = getTenantScope(req);
    const page = parseInt(req.query.page || '1', 10);
    const limit = parseInt(req.query.limit || '50', 10);
    const offset = (page - 1) * limit;

    const { status, type, method, search } = req.query;

    let whereClause = 'WHERE 1=1';
    const params = [];
    let pIdx = 1;

    if (merchantId) {
      whereClause += ` AND t.merchant_id = $${pIdx++}`;
      params.push(merchantId);
    }
    if (storeId) {
      whereClause += ` AND t.store_id = $${pIdx++}`;
      params.push(storeId);
    }
    if (status && status !== 'All') {
      whereClause += ` AND t.status = $${pIdx++}`;
      params.push(status);
    }
    if (type && type !== 'All') {
      whereClause += ` AND t.type = $${pIdx++}`;
      params.push(type);
    }
    if (method && method !== 'All') {
      whereClause += ` AND t.method = $${pIdx++}`;
      params.push(method);
    }
    if (search) {
      whereClause += ` AND (t.transaction_id ILIKE $${pIdx} OR t.order_id ILIKE $${pIdx})`;
      params.push(`%${search.trim()}%`);
      pIdx++;
    }

    const countQuery = `SELECT COUNT(*) FROM transactions t ${whereClause}`;
    const countRes = await db.query(countQuery, params);
    const total = parseInt(countRes.rows[0].count, 10);

    const listQuery = `
      SELECT 
        t.transaction_id, t.order_id, t.type, t.status, t.method,
        t.amount_inr, t.fee_inr, t.tax_inr, t.settled_amount_inr,
        t.expected_settlement_date, t.timestamp, t.exception_flag,
        t.merchant_id, t.store_id,
        er.status as resolution_status, er.resolution_note
      FROM transactions t
      LEFT JOIN exception_resolutions er ON t.transaction_id = er.transaction_id
      ${whereClause}
      ORDER BY t.timestamp DESC, t.transaction_id DESC
      LIMIT $${pIdx++} OFFSET $${pIdx++}
    `;
    params.push(limit, offset);

    const listRes = await db.query(listQuery, params);

    // Compute derived calculated_exceptions for UI display
    const rows = listRes.rows.map(row => {
      const exceptions = [];
      const isResolved = row.resolution_status === 'RESOLVED';
      
      if (!isResolved && row.exception_flag === 'YES') {
        if (!row.order_id) exceptions.push('MISSING_ORDER_ID');
        if (row.status === 'disputed') exceptions.push('DISPUTED_TRANSACTION');
        
        const expectedFee = Number((row.amount_inr * 0.02).toFixed(2));
        if (Math.abs(row.fee_inr - expectedFee) > 0.05 && row.type === 'PAYMENT') {
          exceptions.push(`FEE_MISMATCH (Expected: ₹${expectedFee.toFixed(2)}, Recorded: ₹${Number(row.fee_inr).toFixed(2)})`);
        }
        
        const expectedSettled = Number((row.amount_inr - row.fee_inr - row.tax_inr).toFixed(2));
        if (Math.abs(row.settled_amount_inr - expectedSettled) > 0.05 && row.type === 'PAYMENT') {
          exceptions.push(`SETTLED_AMOUNT_MISMATCH (Expected: ₹${expectedSettled.toFixed(2)}, Recorded: ₹${Number(row.settled_amount_inr).toFixed(2)})`);
        }
      }

      return {
        ...row,
        calculated_exceptions: exceptions,
        resolution_status: isResolved ? 'AUTO_RESOLVED' : (row.exception_flag === 'YES' ? 'NEEDS_REVIEW' : 'AUTO_RESOLVED'),
        confidence_score: isResolved ? 1.0 : (row.exception_flag === 'YES' ? 0.30 : 1.0)
      };
    });

    return res.json({
      success: true,
      data: rows,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit)
      }
    });
  } catch (error) {
    next(error);
  }
}

async function getTransactionAudit(req, res, next) {
  try {
    const { id } = req.params;
    const { merchantId, storeId } = getTenantScope(req);

    let txQ = 'SELECT * FROM transactions WHERE transaction_id = $1';
    const txParams = [id];
    if (merchantId) {
      txQ += ' AND merchant_id = $2';
      txParams.push(merchantId);
    }
    const txRes = await db.query(txQ, txParams);

    if (txRes.rows.length === 0) {
      return res.status(404).json({ success: false, error: 'Transaction record not found' });
    }

    const tx = txRes.rows[0];

    // Node 1: Internal Order
    let internalOrder = null;
    let ordNodeClass = 'error-node';
    if (tx.order_id) {
      const ordRes = await db.query('SELECT * FROM internal_orders WHERE order_id = $1', [tx.order_id]);
      if (ordRes.rows.length > 0) {
        internalOrder = ordRes.rows[0];
        ordNodeClass = 'active-node';
      }
    }

    // Node 2: Gateway Details
    const expectedFee = Number((tx.amount_inr * 0.02).toFixed(2));
    const expectedTax = Number((expectedFee * 0.18).toFixed(2));
    const expectedSettled = Number((tx.amount_inr - tx.fee_inr - tx.tax_inr).toFixed(2));
    const feeMatch = Math.abs(tx.fee_inr - expectedFee) <= 0.05;
    const taxMatch = Math.abs(tx.tax_inr - expectedTax) <= 0.05;
    const settledMatch = Math.abs(tx.settled_amount_inr - expectedSettled) <= 0.05;
    const gateNodeClass = (feeMatch && taxMatch && settledMatch) ? 'active-node' : 'error-node';

    // Node 3: Bank Credit
    let bankStatement = null;
    let bankNodeClass = 'error-node';
    if (tx.expected_settlement_date) {
      const bRes = await db.query(
        'SELECT * FROM bank_statements WHERE date = $1 AND merchant_id = $2 AND store_id = $3',
        [tx.expected_settlement_date, tx.merchant_id, tx.store_id]
      );
      if (bRes.rows.length > 0) {
        bankStatement = bRes.rows[0];
        bankNodeClass = bankStatement.status === 'RECONCILED' ? 'active-node' : 'error-node';
      }
    }

    // Check resolution status
    const resRes = await db.query('SELECT * FROM exception_resolutions WHERE transaction_id = $1', [id]);
    const resolution = resRes.rows.length > 0 ? resRes.rows[0] : null;

    return res.json({
      success: true,
      transaction_id: id,
      nodes: {
        internal_order: {
          order_id: tx.order_id || 'Not Assigned',
          amount_inr: internalOrder ? parseFloat(internalOrder.amount_inr) : 0.0,
          status: internalOrder ? internalOrder.status.toUpperCase() : 'NOT_FOUND',
          state: ordNodeClass
        },
        gateway: {
          transaction_id: tx.transaction_id,
          amount_inr: parseFloat(tx.amount_inr),
          fee_inr: parseFloat(tx.fee_inr),
          tax_inr: parseFloat(tx.tax_inr),
          settled_amount_inr: parseFloat(tx.settled_amount_inr),
          state: gateNodeClass
        },
        bank_credit: {
          date: tx.expected_settlement_date,
          bank_reference: bankStatement ? bankStatement.bank_reference : 'No Reference Found',
          amount_inr: bankStatement ? parseFloat(bankStatement.amount_inr) : 0.0,
          status: bankStatement ? bankStatement.status : 'MISSING_BANK_CREDIT',
          state: bankNodeClass
        }
      },
      math_check: {
        passed: feeMatch && taxMatch && settledMatch,
        expected_fee: expectedFee,
        recorded_fee: parseFloat(tx.fee_inr),
        expected_tax: expectedTax,
        recorded_tax: parseFloat(tx.tax_inr),
        expected_settled: expectedSettled,
        recorded_settled: parseFloat(tx.settled_amount_inr)
      },
      resolution,
      raw_transaction: tx
    });
  } catch (error) {
    next(error);
  }
}

module.exports = {
  getSummaryMetrics,
  getTransactions,
  getTransactionAudit
};
