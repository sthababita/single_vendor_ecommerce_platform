# E-Commerce Frontend

A simple, responsive frontend for the Django e-commerce platform built with vanilla HTML, CSS, and JavaScript.

## Features

✅ **User Authentication**
- Registration with shipping/billing addresses
- Login/Logout functionality
- Session persistence with localStorage

✅ **Product Browsing**
- Grid layout of all products
- Stock quantity display
- Quantity selector for cart items

✅ **Shopping Cart**
- Add/remove items
- Update quantities
- Real-time cart count in navbar
- Cart persistence

✅ **Checkout**
- Select shipping and billing addresses
- Order review before checkout
- Order creation

✅ **Payment Integration**
- Khalti payment gateway support
- Payment initiation and verification

✅ **Responsive Design**
- Mobile-friendly layout
- Works on all screen sizes

## Setup

### 1. Install Backend (if not already done)

```bash
cd single_vendor_ecommerce_platform
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### 2. Configure CORS (if needed)

If running frontend from a different port/origin, add to `SVEP/settings.py`:

```python
INSTALLED_APPS = [
    ...
    'corsheaders',
    ...
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    ...
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://127.0.0.1:3000",
]
```

### 3. Run the Frontend

#### Option A: Using Python's built-in server
```bash
cd frontend
python -m http.server 8080
```

#### Option B: Using Node.js (if installed)
```bash
cd frontend
npx http-server
```

#### Option C: Direct file access
Simply open `frontend/index.html` in your browser (some features may be limited)

## Usage

1. **Register** - Create a new account with shipping and billing addresses
2. **Login** - Sign in with your credentials
3. **Browse Products** - View all available products on the shop page
4. **Add to Cart** - Select quantity and add items to your cart
5. **Checkout** - Review items, select addresses, and place order
6. **Payment** - Complete payment using Khalti

## API Endpoints Used

- `POST /api/register/` - User registration
- `POST /api/login/` - User login
- `GET /api/products/` - List all products
- `GET /api/cart/` - Get current cart
- `POST /api/cart/add-to-cart/` - Add item to cart
- `PATCH /api/cart/{id}/` - Update cart item
- `DELETE /api/cart/{id}/` - Remove from cart
- `GET /api/addresses/` - List user addresses
- `POST /api/orders/` - Create order
- `GET /api/orders/` - List user orders
- `POST /api/khalti-payment/initiate/` - Initiate Khalti payment
- `POST /api/khalti-payment/verify/` - Verify Khalti payment

## File Structure

```
frontend/
├── index.html           # Main HTML with all pages
├── css/
│   └── style.css        # Styling for all pages
└── js/
    ├── api.js           # API call functions
    └── app.js           # Page logic and handlers
```

## Browser Compatibility

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)
- Mobile browsers

## Notes

- Authentication token is stored in localStorage
- Cart is stored on backend per user
- Khalti test mode is enabled by default
- Change API_BASE in `js/api.js` if backend runs on different URL

## Troubleshooting

### CORS Errors
Add the frontend URL to `CORS_ALLOWED_ORIGINS` in Django settings

### Payment Not Working
- Ensure Khalti script loads correctly
- Check browser console for errors
- Verify test public key is correct

### Cart Items Not Loading
- Ensure you're logged in
- Check that user has a cart in the database

## Future Enhancements

- [ ] Product search and filtering
- [ ] User profile page
- [ ] Order history and tracking
- [ ] Product reviews and ratings
- [ ] Wishlist functionality
- [ ] Advanced payment options
- [ ] Admin dashboard
