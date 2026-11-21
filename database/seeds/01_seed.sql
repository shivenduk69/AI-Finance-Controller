-- ====================================================================
-- AI Finance Controller — Database Seed Data (01_seed.sql)
-- Pre-populates Merchants, Stores, Users, Initial Config, Tickets & Alerts
-- ====================================================================

-- 1. Seed Merchants
INSERT INTO merchants (merchant_id, name, status) VALUES
('flipkart', 'Flipkart', 'ACTIVE'),
('amazon', 'Amazon', 'ACTIVE')
ON CONFLICT (merchant_id) DO NOTHING;

-- 2. Seed Stores
INSERT INTO stores (store_id, merchant_id, name, location, status) VALUES
-- Flipkart Stores
('fk_delhi', 'flipkart', 'Delhi Store', 'Delhi, IN', 'ACTIVE'),
('fk_mumbai', 'flipkart', 'Mumbai Store', 'Mumbai, IN', 'ACTIVE'),
('fk_bangalore', 'flipkart', 'Bangalore Store', 'Bangalore, IN', 'ACTIVE'),
('fk_kolkata', 'flipkart', 'Kolkata Store', 'Kolkata, IN', 'ACTIVE'),
-- Amazon Stores
('az_delhi', 'amazon', 'Delhi Store', 'Delhi, IN', 'ACTIVE'),
('az_mumbai', 'amazon', 'Mumbai Store', 'Mumbai, IN', 'ACTIVE'),
('az_bangalore', 'amazon', 'Bangalore Store', 'Bangalore, IN', 'ACTIVE'),
('az_hyderabad', 'amazon', 'Hyderabad Store', 'Hyderabad, IN', 'ACTIVE')
ON CONFLICT (store_id) DO NOTHING;

-- 3. Seed Users (with Argon2id password hashes)
INSERT INTO users (user_id, email, password_hash, role, merchant_id, store_id) VALUES
-- Admin User (admin123)
('admin', 'admin@razorpay-demo.com', '$argon2id$v=19$m=65536,t=3,p=4$2DGRCZfLQ+ehZFoIpO7AwA$AQBNA0cj69LTe+wVGy/BP4AlAMvTwhRPkwx5X1x9FAQ', 'ADMIN', NULL, NULL),
-- Flipkart Store Managers (flipkart123)
('fk_user_delhi', 'flipkart.delhi@merchant-demo.com', '$argon2id$v=19$m=65536,t=3,p=4$7BJZAPPGOWT8UfqK8xaCow$eNB1oa6itZyVa6HCMNC+G6Ede1j2j8IgmEDEd8CMhHQ', 'MERCHANT', 'flipkart', 'fk_delhi'),
('fk_user_mumbai', 'flipkart.mumbai@merchant-demo.com', '$argon2id$v=19$m=65536,t=3,p=4$7BJZAPPGOWT8UfqK8xaCow$eNB1oa6itZyVa6HCMNC+G6Ede1j2j8IgmEDEd8CMhHQ', 'MERCHANT', 'flipkart', 'fk_mumbai'),
('fk_user_bangalore', 'flipkart.bangalore@merchant-demo.com', '$argon2id$v=19$m=65536,t=3,p=4$7BJZAPPGOWT8UfqK8xaCow$eNB1oa6itZyVa6HCMNC+G6Ede1j2j8IgmEDEd8CMhHQ', 'MERCHANT', 'flipkart', 'fk_bangalore'),
-- Amazon Store Managers (amazon123)
('az_user_delhi', 'amazon.delhi@merchant-demo.com', '$argon2id$v=19$m=65536,t=3,p=4$3G5oiefJ4P5EtJjW68cS8w$nzehGlzDUDTFpbQhof+qdqThQYd5hhleKFjOgZxXslk', 'MERCHANT', 'amazon', 'az_delhi'),
('az_user_mumbai', 'amazon.mumbai@merchant-demo.com', '$argon2id$v=19$m=65536,t=3,p=4$3G5oiefJ4P5EtJjW68cS8w$nzehGlzDUDTFpbQhof+qdqThQYd5hhleKFjOgZxXslk', 'MERCHANT', 'amazon', 'az_mumbai'),
('az_user_bangalore', 'amazon.bangalore@merchant-demo.com', '$argon2id$v=19$m=65536,t=3,p=4$3G5oiefJ4P5EtJjW68cS8w$nzehGlzDUDTFpbQhof+qdqThQYd5hhleKFjOgZxXslk', 'MERCHANT', 'amazon', 'az_bangalore')
ON CONFLICT (user_id) DO NOTHING;

-- 4. Seed Initial System Configuration
INSERT INTO configuration (config_key, config_value) VALUES
('sys_gemini_api_key', ''),
('sys_gemini_model', 'gemini-2.0-flash'),
('sys_gateway_fee', '2.0'),
('sys_gst_rate', '18.0'),
('sys_payout_fee', '5.0'),
('sys_settlement_delay', 'T+2 Days'),
('sys_system_prompt_template', 'You are an AI Finance Controller and Senior Compliance Auditor specializing in multi-source reconciliation, payment gateway operations (Razorpay), Section 194-O TDS compliance, and settlement policies.\n\nEVIDENCE AND RECONCILIATION SUMMARY:\n{evidence_prompt}\n\nRETRIEVED KNOWLEDGE BASE EXCERPTS:\n{retrieved_context}\n{history_context}\n\nGuidelines:\n1. Base your answer strictly on the provided financial evidence and retrieved context.\n2. Cite specific source policies, transaction IDs, or calculations when explaining discrepancies.\n3. Keep your tone professional, authoritative, and concise.')
ON CONFLICT (config_key) DO NOTHING;

-- 5. Seed Initial Notifications
INSERT INTO notifications (user_id, merchant_id, store_id, role, title, message, is_read) VALUES
('admin', NULL, NULL, 'ADMIN', 'Daily Settlement Batches Cleared', 'Nodal settlement batches for Flipkart and Amazon reconciled successfully with zero clearing delay.', 0),
('admin', 'flipkart', 'fk_delhi', 'ADMIN', 'Fee Rate Discrepancy Flagged', 'Detected 2 fee rate mismatches on Flipkart Delhi store transactions requiring operations review.', 0),
('admin', 'amazon', 'az_mumbai', 'ADMIN', 'Section 194-O TDS Threshold Approaching', 'Amazon gross platform collections crossed 85% of monthly compliance threshold.', 0),
('admin', NULL, NULL, 'ADMIN', 'Automated 3-Way Reconciliation Run', '24,850 gateway, order, and bank records reconciled with 98.4% auto-match rate.', 0),
('fk_user_delhi', 'flipkart', 'fk_delhi', 'MERCHANT', 'August Settlement Statement Ready', 'Your bank deposit statement for Aug 2026 has been matched against gateway captures.', 0)
ON CONFLICT DO NOTHING;

-- 6. Seed Support Tickets
INSERT INTO support_tickets (merchant_id, store_id, transaction_id, merchant_name, subject, message, status, priority, category) VALUES
('flipkart', 'fk_delhi', 'pay_95822412', 'Flipkart', 'Gateway fee charged at 3% instead of contracted 2%', 'We noticed fee discrepancy on order_24942603 where 3% MDR was charged. Please adjust credit.', 'OPEN', 'High', 'Gateway Exception Review'),
('amazon', 'az_mumbai', 'pay_42780411', 'Amazon', 'Delayed bank settlement for August 10 batch', 'Bank settlement amount was credited as ₹9,952.26 instead of expected ₹10,202.26. Please verify nodal transfer.', 'OPEN', 'Medium', 'Settlement Inquiry'),
('flipkart', 'fk_mumbai', 'pay_89254563', 'Flipkart', 'Missing credit advice for payout batch #892', 'Bank credit reference advice missing for Mumbai store batch on Aug 18.', 'OPEN', 'Low', 'Payout Status')
ON CONFLICT DO NOTHING;
