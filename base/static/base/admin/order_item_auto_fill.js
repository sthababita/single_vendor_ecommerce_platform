(function () {
    function init($) {
        if (!$) {
            return;
        }

        function orderAdminBaseUrl() {
            var path = window.location.pathname;
            var match = path.match(/^(.*\/base\/order\/)(?:add\/|\d+\/change\/)?/);
            return match ? match[1] : null;
        }

        function relatedInput($productSelect, fieldName) {
            var productName = $productSelect.attr('name');
            var inputName = productName.replace(/-product$/, '-' + fieldName);
            return $('[name="' + inputName + '"]');
        }

        function selectedUserId() {
            return $('#id_user').val();
        }

        function fillOrderItem(productSelect) {
            var $productSelect = $(productSelect);
            var productId = $productSelect.val();
            var $unitPrice = relatedInput($productSelect, 'unit_price');
            var $quantity = relatedInput($productSelect, 'quantity');
            var baseUrl = orderAdminBaseUrl();
            var params = {};
            var userId = selectedUserId();

            if (!productId || !$unitPrice.length || !$quantity.length || !baseUrl) {
                $unitPrice.val('');
                $quantity.val('');
                return;
            }

            if (userId) {
                params.user_id = userId;
            }

            $.getJSON(baseUrl + 'product-price/' + productId + '/', params, function (data) {
                $unitPrice.val(data.price);
                $quantity.val(data.quantity);
            });
        }

        function fillAllOrderItems() {
            $('select[name$="-product"]').each(function () {
                if ($(this).val()) {
                    fillOrderItem(this);
                }
            });
        }

        function populateFromCartItems(items) {
            if (!items || !items.length) return;

            // Find existing product selects for order item inlines
            function getProductSelects() {
                return $('select[name$="-product"]').toArray();
            }

            var selects = getProductSelects();

            items.forEach(function (item, idx) {
                // ensure there's an available select to fill; if not, try to add one
                if (idx >= selects.length) {
                    clickAddInlineIfNeeded();
                    // refresh selects after adding
                    selects = getProductSelects();
                }

                var sel = selects[idx];
                if (!sel) {
                    // as a fallback find the first empty select
                    sel = selects.find(function (s) { return !s.value; });
                }

                if (sel) {
                    var $sel = $(sel);
                    $sel.val(item.product_id).trigger('change');

                    // set quantity and unit_price using relatedInput
                    var $qty = relatedInput($sel, 'quantity');
                    var $price = relatedInput($sel, 'unit_price');
                    if ($qty.length) $qty.val(item.quantity);
                    if ($price.length) $price.val(item.price);
                }
            });
        }

        function fetchCartForUser(userId) {
            var baseUrl = orderAdminBaseUrl();
            if (!baseUrl || !userId) return;
            $.getJSON(baseUrl + 'cart-items/' + userId + '/', function (data) {
                if (data && data.items) {
                    populateFromCartItems(data.items);
                }
                if (data && data.shipping_address_id) {
                    $('#id_shipping_address').val(data.shipping_address_id).trigger('change');
                }
                if (data && data.billing_address_id) {
                    $('#id_billing_address').val(data.billing_address_id).trigger('change');
                }
            });
        }

        $(document).on('change', 'select[name$="-product"]', function () {
            fillOrderItem(this);
        });

        $(document).on('change', '#id_user', function () {
            var userId = selectedUserId();
            fetchCartForUser(userId);
            fillAllOrderItems();
        });

        // Improve add-row selector to cover multiple admin themes
        function clickAddInlineIfNeeded(requiredIndex) {
            var selectors = ['.add-row a', '.add-row', '.grp-add-handler', '.inline-related .add-row a'];
            for (var i = 0; i < selectors.length; i++) {
                var $btn = $(selectors[i]).first();
                if ($btn && $btn.length) {
                    $btn.click();
                    return true;
                }
            }
            return false;
        }

        function setRowValuesWithRetry(idx, item, attempts) {
            attempts = attempts || 0;
            var prefix = 'orderitem_set';
            var prodSelector = '[name="' + prefix + '-' + idx + '-product"]';
            var qtySelector = '[name="' + prefix + '-' + idx + '-quantity"]';
            var priceSelector = '[name="' + prefix + '-' + idx + '-unit_price"]';

            var $prod = $(prodSelector);
            var $qty = $(qtySelector);
            var $price = $(priceSelector);

            if ($prod.length || $qty.length || $price.length) {
                if ($prod.length) {
                    $prod.val(item.product_id).trigger('change');
                }
                if ($qty.length) {
                    $qty.val(item.quantity);
                }
                if ($price.length) {
                    $price.val(item.price);
                }
                return true;
            }

            if (attempts < 10) {
                // try to click add button to create more inlines and retry
                clickAddInlineIfNeeded();
                setTimeout(function () {
                    setRowValuesWithRetry(idx, item, attempts + 1);
                }, 120);
            }
            return false;
        }

        // On load, attempt to auto-populate for the currently selected user (delay to allow inlines init)
        var initialUser = selectedUserId();
        if (initialUser) {
            setTimeout(function () {
                fetchCartForUser(initialUser);
            }, 250);
        }

        fillAllOrderItems();
    }

    if (window.django && django.jQuery) {
        init(django.jQuery);
    } else {
        document.addEventListener('DOMContentLoaded', function () {
            init(window.django && django.jQuery);
        });
    }
})();
