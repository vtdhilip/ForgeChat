/**
 * Shiprocket API Service
 *
 * Handles:
 *  1. Authentication with Shiprocket API (token caching)
 *  2. Creating adhoc orders in Shiprocket
 */

let cachedToken = null;
let tokenExpiresAt = 0;

/**
 * Authenticates with Shiprocket API using SHIPROCKET_EMAIL and SHIPROCKET_PASSWORD
 */
async function getShiprocketToken() {
  const email = (process.env.SHIPROCKET_EMAIL || '').trim();
  const password = (process.env.SHIPROCKET_PASSWORD || '').trim();
  const directToken = (process.env.SHIPROCKET_API_TOKEN || '').trim();

  if (directToken) return directToken;
  if (!email || !password) {
    console.log('[shiprocket] SHIPROCKET_EMAIL or SHIPROCKET_PASSWORD not set in .env — skipping auto-order creation');
    return null;
  }

  // Return cached token if still valid (valid for 10 days)
  if (cachedToken && Date.now() < tokenExpiresAt) {
    return cachedToken;
  }

  try {
    const res = await fetch('https://apiv2.shiprocket.in/v1/external/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();
    if (res.ok && data.token) {
      cachedToken = data.token;
      tokenExpiresAt = Date.now() + (9 * 24 * 60 * 60 * 1000); // 9 days
      console.log('[shiprocket] Authenticated with Shiprocket API successfully!');
      return cachedToken;
    } else {
      console.error('[shiprocket] Auth failed:', JSON.stringify(data));
      return null;
    }
  } catch (err) {
    console.error('[shiprocket] Auth error:', err.message);
    return null;
  }
}

/**
 * Creates an order in Shiprocket
 */
async function createShiprocketOrder(order) {
  const token = await getShiprocketToken();
  if (!token) return null;

  try {
    const pickupLocation = (process.env.SHIPROCKET_PICKUP_LOCATION || 'Primary').trim();
    const orderNumber = order.order_number || order.order_id || `LN-${Date.now()}`;
    const customerName = order.contact_name || order.customer_name || 'Customer';
    const phone = String(order.contact_number || order.phone || '').replace(/\D/g, '').slice(-10);
    const address = order.delivery_address || order.address || 'Address provided on WhatsApp';
    const subtotal = parseFloat(order.subtotal || order.total_amount || 359);
    const shipping = parseFloat(order.shipping_fee || order.shipping || 60);
    const total = parseFloat(order.total_amount || (subtotal + shipping));

    let items = [];
    if (order.items) {
      try {
        const raw = Array.isArray(order.items) ? order.items : JSON.parse(order.items);
        items = raw.map(i => ({
          name: i.title || i.name || 'LINNDEN Premium Modal Trunks',
          sku: i.product_retailer_id || `SKU-${orderNumber}`,
          units: parseInt(i.quantity, 10) || 1,
          selling_price: parseFloat(i.item_price || i.price || subtotal),
          discount: 0,
          tax: 0,
          hsn: 6207,
        }));
      } catch {}
    }

    if (items.length === 0) {
      items = [{
        name: 'LINNDEN Premium Apparel',
        sku: `SKU-${orderNumber}`,
        units: 1,
        selling_price: subtotal,
        discount: 0,
        tax: 0,
        hsn: 6207,
      }];
    }

    // Try to extract pincode from address (6 consecutive digits in India)
    const pinMatch = address.match(/\b\d{6}\b/);
    const pincode = pinMatch ? pinMatch[0] : (process.env.SHIPROCKET_DEFAULT_PINCODE || '600001');

    const payload = {
      order_id: orderNumber,
      order_date: new Date().toISOString().slice(0, 19).replace('T', ' '),
      pickup_location: pickupLocation,
      channel_id: '',
      comment: 'WhatsApp Order',
      billing_customer_name: customerName,
      billing_last_name: '',
      billing_address: address.slice(0, 250),
      billing_address_2: '',
      billing_city: 'City',
      billing_pincode: pincode,
      billing_state: 'State',
      billing_country: 'India',
      billing_email: 'order@thaniq.shop',
      billing_phone: phone,
      shipping_is_billing: true,
      order_items: items,
      payment_method: order.status === 'paid' ? 'Prepaid' : 'COD',
      shipping_charges: shipping,
      giftwrap_charges: 0,
      transaction_charges: 0,
      total_discount: 0,
      sub_total: subtotal,
      length: 15,
      breadth: 10,
      height: 5,
      weight: 0.2,
    };

    const res = await fetch('https://apiv2.shiprocket.in/v1/external/orders/create/adhoc', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (res.ok && data.order_id) {
      console.log(`[shiprocket] ✅ Order ${orderNumber} created in Shiprocket (ID: ${data.order_id}, Shipment ID: ${data.shipment_id})`);
      return data;
    } else {
      console.warn(`[shiprocket] Order creation returned HTTP ${res.status}:`, JSON.stringify(data));
      return data;
    }
  } catch (err) {
    console.error('[shiprocket] Error creating order:', err.message);
    return null;
  }
}

module.exports = {
  getShiprocketToken,
  createShiprocketOrder,
};
