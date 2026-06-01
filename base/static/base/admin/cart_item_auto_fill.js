(function () {
    function init($) {
        if (!$) {
            return;
        }

        function cartAdminBaseUrl() {
            var path = window.location.pathname;
            var match = path.match(/^(.*\/base\/cart\/)(?:add\/|\d+\/change\/)?/);
            return match ? match[1] : null;
        }

        function relatedInput($productSelect, fieldName) {
            var productName = $productSelect.attr('name');
            var inputName = productName.replace(/-product$/, '-' + fieldName);
            return $('[name="' + inputName + '"]');
        }

        function updateSubtotal($productSelect) {
            var $unitPrice = relatedInput($productSelect, 'unit_price');
            var $quantity = relatedInput($productSelect, 'quantity');
            var $subtotal = relatedInput($productSelect, 'subtotal');
            var price = parseFloat($unitPrice.val()) || 0;
            var quantity = parseInt($quantity.val(), 10) || 0;

            $subtotal.val((price * quantity).toFixed(2));
        }

        function setPrice($productSelect, price) {
            relatedInput($productSelect, 'unit_price').val(parseFloat(price).toFixed(2));
            updateSubtotal($productSelect);
        }

        function fillCartItem(productSelect) {
            var $productSelect = $(productSelect);
            var productId = $productSelect.val();
            var $unitPrice = relatedInput($productSelect, 'unit_price');
            var $subtotal = relatedInput($productSelect, 'subtotal');
            var selectedPrice = $productSelect.find('option:selected').attr('data-price');
            var baseUrl = cartAdminBaseUrl();

            if (!productId || !$unitPrice.length || !$subtotal.length) {
                $unitPrice.val('');
                $subtotal.val('');
                return;
            }

            if (selectedPrice) {
                setPrice($productSelect, selectedPrice);
                return;
            }

            if (baseUrl) {
                $.getJSON(baseUrl + 'product-price/' + productId + '/', function (data) {
                    setPrice($productSelect, data.price);
                });
            }
        }

        $(document).on('change', 'select[name$="-product"]', function () {
            fillCartItem(this);
        });

        $(document).on('input change', 'input[name$="-quantity"]', function () {
            var productName = $(this).attr('name').replace(/-quantity$/, '-product');
            updateSubtotal($('[name="' + productName + '"]'));
        });

        $('select[name$="-product"]').each(function () {
            if ($(this).val()) {
                fillCartItem(this);
            }
        });
    }

    if (window.django && django.jQuery) {
        init(django.jQuery);
    } else {
        document.addEventListener('DOMContentLoaded', function () {
            init(window.django && django.jQuery);
        });
    }
})();
