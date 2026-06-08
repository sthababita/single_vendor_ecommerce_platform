// API Configuration
const API_BASE = 'http://localhost:8000/api';

// Get auth token from localStorage
function getAuthToken() {
    return localStorage.getItem('authToken');
}

// Get CSRF token if needed
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Helper function for API requests
async function apiCall(endpoint, method = 'GET', data = null) {
    const headers = {
        'Content-Type': 'application/json',
    };

    const token = getAuthToken();
    if (token) {
        headers['Authorization'] = `Token ${token}`;
    }

    const options = {
        method,
        headers,
    };

    if (data) {
        options.body = JSON.stringify(data);
    }

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, options);
        const json = await response.json();

        if (!response.ok) {
            throw {
                status: response.status,
                data: json
            };
        }

        return json;
    } catch (error) {
        throw error;
    }
}

// Auth API Calls
async function registerUser(username, email, password, shippingData, billingData) {
    const payload = {
        username,
        email,
        password,
        shipping_address_line1: shippingData.address_line1,
        shipping_address_line2: shippingData.address_line2 || '',
        shipping_city: shippingData.city,
        shipping_state: shippingData.state,
        shipping_postal_code: shippingData.postal_code,
        shipping_country: shippingData.country,
        billing_address_line1: billingData.address_line1,
        billing_address_line2: billingData.address_line2 || '',
        billing_city: billingData.city,
        billing_state: billingData.state,
        billing_postal_code: billingData.postal_code,
        billing_country: billingData.country,
    };

    return apiCall('/register/', 'POST', payload);
}

async function loginUser(username, password) {
    const data = await apiCall('/login/', 'POST', {
        username,
        password,
    });
    
    if (data.token) {
        localStorage.setItem('authToken', data.token);
        localStorage.setItem('currentUser', JSON.stringify(data.user));
    }
    
    return data;
}

function logoutUser() {
    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
}

function isLoggedIn() {
    return !!getAuthToken();
}

function getCurrentUser() {
    const user = localStorage.getItem('currentUser');
    return user ? JSON.parse(user) : null;
}

// Product API Calls
async function fetchProducts() {
    return apiCall('/products/');
}

// Cart API Calls
async function addToCart(productId, quantity) {
    return apiCall('/cart/add-to-cart/', 'POST', {
        product_id: productId,
        quantity,
    });
}

async function fetchCart() {
    return apiCall('/cart/');
}

async function updateCartItem(cartItemId, quantity) {
    return apiCall(`/cart/${cartItemId}/`, 'PATCH', {
        quantity,
    });
}

async function removeFromCart(cartItemId) {
    return apiCall(`/cart/${cartItemId}/`, 'DELETE');
}

// Order API Calls
async function createOrder(shippingAddressId, billingAddressId, shippingAmount) {
    const payload = {};
    if (shippingAddressId) payload.shipping_address_id = parseInt(shippingAddressId);
    if (billingAddressId) payload.billing_address_id = parseInt(billingAddressId);
    if (shippingAmount) payload.shipping_amount = parseFloat(shippingAmount);
    
    return apiCall('/orders/', 'POST', payload);
}

async function fetchOrders() {
    return apiCall('/orders/');
}

async function fetchOrderDetail(orderId) {
    return apiCall(`/orders/${orderId}/`);
}

async function fetchAddresses() {
    return apiCall('/addresses/');
}

// Payment API Calls
async function initiateKhaltiPayment(orderNumber) {
    return apiCall('/khalti-payment/initiate/', 'POST', {
        order_number: orderNumber,
    });
}

async function verifyKhaltiPayment(pidx, transactionId) {
    return apiCall('/khalti-payment/verify/', 'POST', {
        pidx,
        transaction_id: transactionId,
    });
}

// Khalti Payment Handler
function initializeKhaltiButton(pidx, orderNumber) {
    const config = {
        "publicKey": "test_public_key_dc74e0fd57cb46cd93832722e0997233",
        "productIdentity": orderNumber,
        "productName": "Order Payment",
        "productUrl": window.location.href,
        "eventHandler": {
            onSuccess(payload) {
                console.log('Khalti payment success:', payload);
                verifyPayment(pidx, payload.transaction_id, orderNumber);
            },
            onError(error) {
                console.error('Khalti payment error:', error);
                if (typeof showError === 'function') {
                    showError('❌ Payment failed. Please try again.');
                }
            },
            onClose() {
                console.log('Khalti payment window closed');
            }
        }
    };

    if (typeof Khalti !== 'undefined') {
        Khalti.checkout(config);
    } else {
        console.error('Khalti library not loaded');
        if (typeof showError === 'function') {
            showError('❌ Payment gateway not available. Please try again later.');
        }
    }
}

async function verifyPayment(pidx, transactionId, orderNumber) {
    try {
        const result = await verifyKhaltiPayment(pidx, transactionId);
        if (result.status === 'Completed' || result.payment_status === 'Completed') {
            if (typeof showSuccess === 'function') {
                showSuccess('✓ Payment successful! Your order has been confirmed.');
            }
            setTimeout(() => {
                if (typeof showPage === 'function') {
                    showPage('shop');
                }
            }, 2000);
        } else {
            if (typeof showError === 'function') {
                showError('❌ Payment verification failed');
            }
        }
    } catch (error) {
        console.error('Payment verification error:', error);
        if (typeof showError === 'function') {
            showError('❌ Payment verification failed. Please contact support.');
        }
    }
}
