// ====================== GLOBAL STATE ======================
let currentPage = 'shop';
let currentOrder = null;
let allProducts = [];
let filteredProducts = [];

// ====================== PAGE NAVIGATION ======================
function showPage(page) {
    // Hide all pages
    document.querySelectorAll('.page').forEach(p => {
        p.classList.remove('active');
        p.style.display = 'none';
    });

    // Show requested page
    const pageElement = document.getElementById(`${page}-page`);
    if (pageElement) {
        pageElement.classList.add('active');
        pageElement.style.display = 'block';
    }

    currentPage = page;

    // Load page-specific data
    if (page === 'shop') {
        loadProducts();
    } else if (page === 'cart') {
        loadCart();
    } else if (page === 'checkout') {
        loadCheckout();
    }

    // Update auth link
    updateAuthLink();

    clearErrors();
    window.scrollTo(0, 0);
}

// ====================== AUTH MANAGEMENT ======================
function updateAuthLink() {
    const authLink = document.getElementById('auth-link');
    if (isLoggedIn()) {
        const user = getCurrentUser();
        authLink.textContent = `👤 ${user.username}`;
        authLink.onclick = (e) => {
            e.preventDefault();
            if (confirm('Are you sure you want to logout?')) {
                logoutUser();
                showSuccess('Logged out successfully');
                updateAuthLink();
                showPage('shop');
            }
        };
    } else {
        authLink.textContent = '🔐 Login';
        authLink.onclick = (e) => {
            e.preventDefault();
            showPage('login');
        };
    }
}

// ====================== SHOP PAGE ======================
async function loadProducts() {
    try {
        const response = await fetchProducts();
        allProducts = response.results || response;
        filteredProducts = allProducts;
        renderProducts(filteredProducts);
    } catch (error) {
        console.error('Error loading products:', error);
        showError('❌ Failed to load products. Please try again.');
    }
}

function renderProducts(products) {
    const grid = document.getElementById('products-grid');
    grid.innerHTML = '';

    if (!products || products.length === 0) {
        grid.innerHTML = `
            <div style="grid-column: 1/-1; text-align: center; padding: 3rem;">
                <p style="font-size: 1.2rem; color: #7f8c8d;">No products found</p>
            </div>
        `;
        return;
    }

    products.forEach(product => {
        const stockStatus = product.stock_quantity > 10 ? 'In Stock' : 
                          product.stock_quantity > 0 ? 'Low Stock' : 'Out of Stock';
        const stockClass = product.stock_quantity > 10 ? '' : 
                         product.stock_quantity > 0 ? 'low' : 'out';
        
        const card = document.createElement('div');
        card.className = 'product-card';
        card.innerHTML = `
            ${product.stock_quantity === 0 ? '<div class="product-badge">Out of Stock</div>' : ''}
            <div class="product-image">📦</div>
            <div class="product-info">
                <div class="product-name">${product.name}</div>
                <div class="product-description">${product.description || 'High quality product'}</div>
                <div class="product-price">$${parseFloat(product.price).toFixed(2)}</div>
                <div class="product-stock">
                    <span class="stock-indicator ${stockClass}"></span>
                    ${stockStatus} (${product.stock_quantity})
                </div>
                <div class="product-actions">
                    <input type="number" id="qty-${product.id}" value="1" min="1" max="${product.stock_quantity}" ${product.stock_quantity === 0 ? 'disabled' : ''}>
                    <button class="btn btn-primary btn-small" onclick="addProductToCart(${product.id})" ${product.stock_quantity === 0 ? 'disabled' : ''}>
                        Add to Cart
                    </button>
                </div>
            </div>
        `;
        grid.appendChild(card);
    });
}

function filterProducts() {
    const searchTerm = document.getElementById('search-input').value.toLowerCase();
    
    if (!searchTerm) {
        filteredProducts = allProducts;
    } else {
        filteredProducts = allProducts.filter(product => 
            product.name.toLowerCase().includes(searchTerm) ||
            (product.description && product.description.toLowerCase().includes(searchTerm))
        );
    }
    
    renderProducts(filteredProducts);
}

function toggleFilters() {
    showSuccess('ℹ️ More filter options coming soon!');
}

async function addProductToCart(productId) {
    if (!isLoggedIn()) {
        showSuccess('💡 Please login first to add items to cart');
        setTimeout(() => showPage('login'), 500);
        return;
    }

    try {
        const qtyInput = document.getElementById(`qty-${productId}`);
        const quantity = parseInt(qtyInput.value);

        if (quantity < 1) {
            showError('❌ Please enter a valid quantity');
            return;
        }

        await addToCart(productId, quantity);
        await updateCartCount();
        showSuccess('✓ Product added to cart!');
        qtyInput.value = 1;
    } catch (error) {
        console.error('Error adding to cart:', error);
        showError('❌ Failed to add product to cart');
    }
}

// ====================== AUTH PAGES ======================
async function handleRegister(event) {
    event.preventDefault();
    clearErrors();

    const username = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const password = document.getElementById('reg-password').value;

    if (password.length < 8) {
        document.getElementById('register-error').textContent = '❌ Password must be at least 8 characters';
        document.getElementById('register-error').style.display = 'block';
        return;
    }

    const shippingData = {
        address_line1: document.getElementById('reg-shipping-addr1').value.trim(),
        address_line2: document.getElementById('reg-shipping-addr2').value.trim(),
        city: document.getElementById('reg-shipping-city').value.trim(),
        state: document.getElementById('reg-shipping-state').value.trim(),
        postal_code: document.getElementById('reg-shipping-postal').value.trim(),
        country: document.getElementById('reg-shipping-country').value.trim(),
    };

    const billingData = {
        address_line1: document.getElementById('reg-billing-addr1').value.trim(),
        address_line2: document.getElementById('reg-billing-addr2').value.trim(),
        city: document.getElementById('reg-billing-city').value.trim(),
        state: document.getElementById('reg-billing-state').value.trim(),
        postal_code: document.getElementById('reg-billing-postal').value.trim(),
        country: document.getElementById('reg-billing-country').value.trim(),
    };

    try {
        await registerUser(username, email, password, shippingData, billingData);
        showSuccess('✓ Registration successful! Please login.');
        document.getElementById('register-form').reset();
        setTimeout(() => showPage('login'), 1000);
    } catch (error) {
        console.error('Registration error:', error);
        let message = '❌ Registration failed';
        if (error.data) {
            message = '❌ ' + Object.values(error.data).flat().join(', ');
        }
        document.getElementById('register-error').textContent = message;
        document.getElementById('register-error').style.display = 'block';
    }
}

async function handleLogin(event) {
    event.preventDefault();
    clearErrors();

    const username = document.getElementById('login-username').value.trim();
    const password = document.getElementById('login-password').value;

    try {
        await loginUser(username, password);
        showSuccess('✓ Login successful!');
        document.getElementById('login-form').reset();
        updateAuthLink();
        setTimeout(() => showPage('shop'), 500);
    } catch (error) {
        console.error('Login error:', error);
        let message = '❌ Login failed';
        if (error.data && error.data.detail) {
            message = '❌ ' + error.data.detail;
        }
        document.getElementById('login-error').textContent = message;
        document.getElementById('login-error').style.display = 'block';
    }
}

// ====================== CART PAGE ======================
async function loadCart() {
    if (!isLoggedIn()) {
        showPage('login');
        return;
    }

    try {
        const cart = await fetchCart();
        const listDiv = document.getElementById('cart-items-list');
        const summaryDiv = document.getElementById('cart-summary');
        const emptyDiv = document.getElementById('empty-cart');

        if (!cart.items || cart.items.length === 0) {
            listDiv.innerHTML = '';
            summaryDiv.style.display = 'none';
            emptyDiv.style.display = 'block';
            return;
        }

        emptyDiv.style.display = 'none';
        listDiv.innerHTML = '<div class="cart-items-container">';

        let subtotal = 0;
        cart.items.forEach(item => {
            const itemSubtotal = item.quantity * item.product_price;
            subtotal += itemSubtotal;

            const itemHtml = `
                <div class="cart-item">
                    <div class="cart-item-image">📦</div>
                    <div class="cart-item-info">
                        <div class="cart-item-name">${item.product_name}</div>
                        <div class="cart-item-price">$${parseFloat(item.product_price).toFixed(2)}</div>
                        <div class="cart-item-quantity">
                            <label>Quantity: </label>
                            <input type="number" value="${item.quantity}" min="1" onchange="updateCartItemQty(${item.id}, this.value)">
                        </div>
                    </div>
                    <div class="cart-item-subtotal">$${itemSubtotal.toFixed(2)}</div>
                    <div class="cart-item-actions">
                        <button class="btn btn-danger btn-small" onclick="removeCartItem(${item.id})">🗑️ Remove</button>
                    </div>
                </div>
            `;
            listDiv.innerHTML += itemHtml;
        });

        listDiv.innerHTML += '</div>';
        
        document.getElementById('cart-subtotal').textContent = `$${subtotal.toFixed(2)}`;
        document.getElementById('cart-shipping').textContent = '$0.00';
        document.getElementById('cart-total').textContent = `$${subtotal.toFixed(2)}`;
        summaryDiv.style.display = 'block';

    } catch (error) {
        console.error('Error loading cart:', error);
        showError('❌ Failed to load cart');
    }
}

async function updateCartItemQty(itemId, quantity) {
    quantity = parseInt(quantity);
    if (quantity < 1) {
        showError('❌ Quantity must be at least 1');
        return;
    }

    try {
        await updateCartItem(itemId, quantity);
        await loadCart();
        await updateCartCount();
    } catch (error) {
        console.error('Error updating cart:', error);
        showError('❌ Failed to update cart');
    }
}

async function removeCartItem(itemId) {
    if (!confirm('Are you sure you want to remove this item from your cart?')) return;

    try {
        await removeFromCart(itemId);
        await loadCart();
        await updateCartCount();
        showSuccess('✓ Item removed from cart');
    } catch (error) {
        console.error('Error removing from cart:', error);
        showError('❌ Failed to remove item');
    }
}

async function updateCartCount() {
    try {
        const cart = await fetchCart();
        const count = cart.items ? cart.items.length : 0;
        document.getElementById('cart-count').textContent = count;
    } catch (error) {
        console.error('Error updating cart count:', error);
    }
}

// ====================== CHECKOUT PAGE ======================
async function loadCheckout() {
    if (!isLoggedIn()) {
        showPage('login');
        return;
    }

    try {
        // Load addresses
        const addresses = await fetchAddresses();
        const shippingDiv = document.getElementById('shipping-address-options');
        const billingDiv = document.getElementById('billing-address-options');

        shippingDiv.innerHTML = '';
        billingDiv.innerHTML = '';

        const shippingAddrs = addresses.filter(a => a.address_type === 'shipping');
        const billingAddrs = addresses.filter(a => a.address_type === 'billing');

        shippingAddrs.forEach((addr, idx) => {
            const html = `
                <div class="checkout-address-option ${idx === 0 ? 'selected' : ''}" onclick="selectAddress('shipping', ${addr.id}, this)">
                    <input type="radio" name="shipping_address" value="${addr.id}" ${idx === 0 ? 'checked' : ''}>
                    <div style="flex: 1;">
                        <strong>${addr.address_line1}</strong><br>
                        <span style="color: #7f8c8d;">
                            ${addr.city}, ${addr.state} ${addr.postal_code}<br>
                            ${addr.country}
                        </span>
                    </div>
                </div>
            `;
            shippingDiv.innerHTML += html;
        });

        billingAddrs.forEach((addr, idx) => {
            const html = `
                <div class="checkout-address-option ${idx === 0 ? 'selected' : ''}" onclick="selectAddress('billing', ${addr.id}, this)">
                    <input type="radio" name="billing_address" value="${addr.id}" ${idx === 0 ? 'checked' : ''}>
                    <div style="flex: 1;">
                        <strong>${addr.address_line1}</strong><br>
                        <span style="color: #7f8c8d;">
                            ${addr.city}, ${addr.state} ${addr.postal_code}<br>
                            ${addr.country}
                        </span>
                    </div>
                </div>
            `;
            billingDiv.innerHTML += html;
        });

        // Load cart items for review
        const cart = await fetchCart();
        const itemsDiv = document.getElementById('checkout-items');
        itemsDiv.innerHTML = '';

        let subtotal = 0;
        cart.items.forEach(item => {
            const itemSubtotal = item.quantity * item.product_price;
            subtotal += itemSubtotal;
            const html = `
                <div class="review-item" style="display: flex; justify-content: space-between; padding: 0.8rem 0; border-bottom: 1px solid #e0e0e0;">
                    <span>${item.product_name} x ${item.quantity}</span>
                    <span style="font-weight: 600;">$${itemSubtotal.toFixed(2)}</span>
                </div>
            `;
            itemsDiv.innerHTML += html;
        });

        updateShippingCost(subtotal);

    } catch (error) {
        console.error('Error loading checkout:', error);
        showError('❌ Failed to load checkout');
    }
}

function selectAddress(type, addressId, element) {
    const radio = element.querySelector(`input[name="${type}_address"]`);
    if (radio) {
        radio.checked = true;
        document.querySelectorAll(`.checkout-address-options:has(input[name="${type}_address"]) .checkout-address-option`).forEach(opt => {
            opt.classList.remove('selected');
        });
        element.classList.add('selected');
    }
}

function updateShippingCost(subtotal = 0) {
    const shippingMethod = document.querySelector('input[name="shipping_method"]:checked')?.value || '100';
    const shipping = parseFloat(shippingMethod);
    const total = (subtotal || parseFloat(document.getElementById('checkout-subtotal')?.textContent || 0)) + shipping;

    // Get current subtotal if not provided
    if (subtotal === 0) {
        const subtotalText = document.getElementById('checkout-subtotal')?.textContent || '$0.00';
        subtotal = parseFloat(subtotalText.replace('$', ''));
    }

    document.getElementById('checkout-subtotal').textContent = `$${subtotal.toFixed(2)}`;
    document.getElementById('checkout-shipping').textContent = `$${shipping.toFixed(2)}`;
    document.getElementById('checkout-total').textContent = `$${(subtotal + shipping).toFixed(2)}`;
}

async function handleCheckout(event) {
    event.preventDefault();
    clearErrors();

    if (!isLoggedIn()) {
        showPage('login');
        return;
    }

    try {
        const shippingAddressId = document.querySelector('input[name="shipping_address"]:checked')?.value;
        const billingAddressId = document.querySelector('input[name="billing_address"]:checked')?.value;
        const shippingAmount = document.querySelector('input[name="shipping_method"]:checked')?.value || '100';

        if (!shippingAddressId || !billingAddressId) {
            showError('❌ Please select both shipping and billing addresses');
            return;
        }

        const order = await createOrder(shippingAddressId, billingAddressId, shippingAmount);
        currentOrder = order;

        // Show confirmation page
        document.getElementById('order-number').textContent = `Order #${order.order_number}`;
        document.getElementById('order-amount').textContent = `Total: $${parseFloat(order.total_amount).toFixed(2)}`;

        // Show payment section
        const paymentSection = document.getElementById('payment-section');
        paymentSection.style.display = 'block';

        // Update cart count
        await updateCartCount();

        showPage('confirmation');

        // Setup Khalti payment button
        const khaltiBtn = document.getElementById('khalti-btn');
        khaltiBtn.onclick = async () => {
            try {
                khaltiBtn.disabled = true;
                khaltiBtn.textContent = '⏳ Processing...';
                
                const response = await initiateKhaltiPayment(order.order_number);
                if (response.pidx) {
                    window.location.href = `https://dev.khalti.com/checkout/pay/${response.pidx}`;
                } else {
                    throw new Error('No pidx in response');
                }
            } catch (error) {
                console.error('Payment initiation error:', error);
                khaltiBtn.disabled = false;
                khaltiBtn.textContent = 'Pay Now with Khalti';
                showError('❌ Failed to initiate payment');
            }
        };

    } catch (error) {
        console.error('Checkout error:', error);
        let message = '❌ Checkout failed';
        if (error.data) {
            if (typeof error.data === 'string') {
                message = '❌ ' + error.data;
            } else {
                message = '❌ ' + (error.data.error || Object.values(error.data).flat().join(', '));
            }
        }
        document.getElementById('checkout-error').textContent = message;
        document.getElementById('checkout-error').style.display = 'block';
    }
}

// ====================== MESSAGE HANDLING ======================
function showError(message) {
    const errorDiv = document.getElementById('error-message');
    errorDiv.textContent = message;
    errorDiv.style.display = 'block';
    setTimeout(() => {
        errorDiv.style.display = 'none';
    }, 5000);
}

function showSuccess(message) {
    const successDiv = document.getElementById('success-message');
    successDiv.textContent = message;
    successDiv.style.display = 'block';
    setTimeout(() => {
        successDiv.style.display = 'none';
    }, 4000);
}

function clearErrors() {
    document.getElementById('error-message').style.display = 'none';
    document.getElementById('success-message').style.display = 'none';
    document.querySelectorAll('.error').forEach(el => {
        el.style.display = 'none';
    });
}

// ====================== INITIALIZATION ======================
document.addEventListener('DOMContentLoaded', () => {
    updateAuthLink();
    updateCartCount();
    showPage('shop');

    // Load Khalti script
    const script = document.createElement('script');
    script.src = 'https://khalti.s3.amazonaws.com/KhaltiCheckout.js';
    script.onerror = () => console.warn('Failed to load Khalti script');
    document.head.appendChild(script);
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + K to search
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        if (currentPage === 'shop') {
            document.getElementById('search-input').focus();
        }
    }
    // Escape to clear search
    if (e.key === 'Escape' && currentPage === 'shop') {
        document.getElementById('search-input').value = '';
        filterProducts();
    }
});

