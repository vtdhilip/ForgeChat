-- Migration 058: Orders tracking table
CREATE TABLE IF NOT EXISTS coexistence.orders (
  id SERIAL PRIMARY KEY,
  order_number VARCHAR(64) UNIQUE NOT NULL,
  shopify_draft_order_id VARCHAR(128),
  shopify_order_number VARCHAR(64),
  wa_number VARCHAR(32),
  contact_number VARCHAR(32) NOT NULL,
  contact_name VARCHAR(255),
  delivery_address TEXT,
  items JSONB DEFAULT '[]'::jsonb,
  subtotal NUMERIC(10,2) DEFAULT 0.00,
  shipping_fee NUMERIC(10,2) DEFAULT 0.00,
  total_amount NUMERIC(10,2) DEFAULT 0.00,
  currency VARCHAR(10) DEFAULT 'INR',
  status VARCHAR(32) DEFAULT 'pending', -- pending, unpaid, paid, cancelled, failed
  razorpay_order_id VARCHAR(128),
  razorpay_payment_link_id VARCHAR(128),
  razorpay_payment_id VARCHAR(128),
  payment_link_url TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_orders_contact ON coexistence.orders(contact_number);
CREATE INDEX IF NOT EXISTS idx_orders_status ON coexistence.orders(status);
