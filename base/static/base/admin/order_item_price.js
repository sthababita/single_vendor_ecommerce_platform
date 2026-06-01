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

    function unitPriceInput($productSelect) {
        var productName = $productSelect.attr('name');
        var unitPriceName = productName.replace(/-product$/, '-unit_price');
        return $('[name="' + unitPriceName + '"]');
    }

    function quantityInput($productSelect) {
        var productName = $productSelect.attr('name');
        var quantityName = productName.replace(/-product$/, '-quantity');
        return $('[name="' + quantityName + '"]');
    }

    function selectedUserId() {
        return $('#id_user').val();
    }

    function fillOrderItem(productSelect) {
        var $productSelect = $(productSelect);
        var productId = $productSelect.val();
        var $unitPrice = unitPriceInput($productSelect);
        var $quantity = quantityInput($productSelect);
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

    $(function () {
        $(document).on('change', 'select[name$="-product"]', function () {
            fillOrderItem(this);
        });

        $(document).on('change', '#id_user', function () {
            fillAllOrderItems();
        });

        fillAllOrderItems();
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
