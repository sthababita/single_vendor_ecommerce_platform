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

    function fillCartItem(productSelect) {
        var $productSelect = $(productSelect);
        var productId = $productSelect.val();
        var $unitPrice = relatedInput($productSelect, 'unit_price');
        var $subtotal = relatedInput($productSelect, 'subtotal');
        var baseUrl = cartAdminBaseUrl();
        var selectedPrice = $productSelect.find('option:selected').data('price');

        if (!productId || !$unitPrice.length || !$subtotal.length) {
            $unitPrice.val('');
            $subtotal.val('');
            return;
        }

        if (selectedPrice !== undefined) {
            $unitPrice.val(parseFloat(selectedPrice).toFixed(2));
            updateSubtotal($productSelect);
            return;
        }

        if (!baseUrl) {
            return;
        }

        $.getJSON(baseUrl + 'product-price/' + productId + '/', function (data) {
            $unitPrice.val(data.price);
            updateSubtotal($productSelect);
        });
    }

    $(function () {
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
